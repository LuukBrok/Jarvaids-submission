#!/usr/bin/env python3
"""Standalone Notulator demo: paste a transcript, watch topic extraction run.

Not part of genai_server. Nothing here is persisted, session-scoped, or
called by the real backend. See README.md before running it.
"""
import json
import re
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from queue import Queue

OLLAMA_HOST = "http://localhost:11434"
MODEL = "gemma3:4b"
PORT = 8808

STATIC_DIR = Path(__file__).parent


def ollama_generate(prompt: str) -> dict:
    body = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "format": "json",
        "stream": False,
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/generate", data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        outer = json.loads(resp.read())
    raw = outer.get("response", "")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise ValueError(f"model did not return JSON: {raw[:300]!r}")
        return json.loads(match.group(0))


def ends_sentence(word: str) -> bool:
    return word.rstrip(")\"'").endswith((".", "?", "!"))


class TopicStore:
    """All state for one demo run. One run at a time, in memory only.

    Two levels: a small number of broad themes ("Pricing", "Mechanics"),
    each holding specific topics ("Student discount", "Payment methods"),
    each holding timestamped entries, one per visit.
    """

    def __init__(self):
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        with self.lock:
            self.topics = {}          # broad -> {"subtopics": {name -> {"description", "entries"}}}
            self.last_path = None     # (broad, specific) of the previous batch
            self.log = []             # activity feed for the UI
            self.status = "idle"      # idle | feeding | done | error
            self.words_fed = 0
            self.words_total = 0
            self.error = None

    def snapshot(self):
        with self.lock:
            return {
                "topics": self.topics,
                "log": self.log,
                "status": self.status,
                "words_fed": self.words_fed,
                "words_total": self.words_total,
                "error": self.error,
            }

    def append_log(self, entry: dict):
        with self.lock:
            self.log.append(entry)

    def topic_index(self) -> str:
        with self.lock:
            if not self.topics:
                return "(none yet)"
            lines = []
            for broad, data in self.topics.items():
                lines.append(f"- {broad}")
                for name, sub in data["subtopics"].items():
                    lines.append(f"    - {name}: {sub['description']}")
            return "\n".join(lines)

    def subtopic_history(self, broad: str, name: str) -> str:
        with self.lock:
            entries = self.topics[broad]["subtopics"][name]["entries"]
            lines = []
            for e in entries:
                lines.append(f"[{e['timestamp']}] {e['summary']}")
                for d in e["decisions"]:
                    lines.append(f"  decided: {d}")
                for a in e["action_items"]:
                    owner = a.get("owner") or "unassigned"
                    lines.append(f"  action ({owner}): {a['text']}")
                for q in e["open_questions"]:
                    lines.append(f"  open question: {q}")
            return "\n".join(lines)

    def apply_new_subtopic(self, broad: str, name: str, timestamp: str, extracted: dict):
        with self.lock:
            if broad not in self.topics:
                self.topics[broad] = {"subtopics": {}}
            self.topics[broad]["subtopics"][name] = {
                "description": extracted.get("description", name),
                "entries": [{
                    "timestamp": timestamp,
                    "summary": extracted.get("summary", ""),
                    "decisions": extracted.get("decisions", []),
                    "action_items": extracted.get("action_items", []),
                    "open_questions": extracted.get("open_questions", []),
                }],
            }
            self.last_path = (broad, name)

    def apply_existing_subtopic(self, broad: str, name: str, timestamp: str, extracted: dict, continuation: bool):
        with self.lock:
            entries = self.topics[broad]["subtopics"][name]["entries"]
            if continuation and entries:
                entry = entries[-1]
                new_summary = extracted.get("summary", "")
                if new_summary:
                    entry["summary"] = (entry["summary"] + " " + new_summary).strip()
                entry["decisions"] += extracted.get("decisions", [])
                entry["action_items"] += extracted.get("action_items", [])
                entry["open_questions"] += extracted.get("open_questions", [])
            else:
                entries.append({
                    "timestamp": timestamp,
                    "summary": extracted.get("summary", ""),
                    "decisions": extracted.get("decisions", []),
                    "action_items": extracted.get("action_items", []),
                    "open_questions": extracted.get("open_questions", []),
                })
            self.last_path = (broad, name)


store = TopicStore()
batch_queue: "Queue[tuple[str, str]]" = Queue()
feed_stop = threading.Event()


CLASSIFY_PROMPT = """You are organising a live meeting transcript into a two-level structure: a small number of BROAD THEMES, and within each, more SPECIFIC TOPICS discussed under it.

Existing structure so far (broad theme, then its specific topics indented):
{index}

New excerpt just said:
\"\"\"{batch}\"\"\"

Decide two things:

1. The BROAD THEME this belongs to. This is very general, covering a whole stretch of the meeting: examples are "Introduction", "Pricing", "Mechanics", "Protocol", "Logistics", "Wellbeing". One to three words. A whole meeting should only ever have a handful of these (roughly four to eight), so strongly prefer an existing broad theme over inventing a new one; only create a new one if this genuinely does not fit any listed above.

2. The SPECIFIC TOPIC, under that broad theme, this belongs to. More specific than the broad theme: within "Pricing" there might be "Student discount" and "Payment methods" as separate specific topics. Two to five words, a category name, never a full sentence. Prefer matching an existing specific topic (under the chosen broad theme) over creating a near-duplicate.

Respond with ONLY valid JSON, nothing else, in exactly this shape:
{{"broad_topic": "<existing or new broad theme, one to three words>", "specific_topic": "<existing or new specific topic under it, two to five words>"}}"""

NEW_SUBTOPIC_PROMPT = """A new specific topic, "{specific}", has just come up under the broader theme "{broad}" in a live meeting. Here is what was said about it:

\"\"\"{batch}\"\"\"

Respond with ONLY valid JSON, nothing else, in exactly this shape:
{{
  "description": "<one-line description of this specific topic, used later to match further mentions of it>",
  "summary": "<2-4 sentence summary of what was said>",
  "decisions": ["<something the room actually settled on, if anything>"],
  "action_items": [{{"text": "<what needs doing>", "owner": "<name stated in the text, or null>"}}],
  "open_questions": ["<something raised and left unresolved>"]
}}

Only record a decision if the room genuinely settled on something, not merely discussed it. Only name an owner if the text actually states one; never invent one, use null instead. Leave a list empty ([]) if it does not apply. Never leave something out for being hard to categorise; put it in the field it fits best."""

UPDATE_SUBTOPIC_PROMPT = """The meeting has returned to, or continued on, the specific topic "{specific}" ({description}), under the broader theme "{broad}".

What has already been recorded for this specific topic:
{history}

New excerpt just said about it:
\"\"\"{batch}\"\"\"

Extract only the NEW information from this excerpt. Respond with ONLY valid JSON, nothing else, in exactly this shape:
{{
  "summary": "<2-4 sentence summary of what is new here>",
  "decisions": ["<something the room actually settled on just now, if anything>"],
  "action_items": [{{"text": "<what needs doing>", "owner": "<name stated in the text, or null>"}}],
  "open_questions": ["<something raised just now and left unresolved>"]
}}

Only record a decision if the room genuinely settled on something, not merely discussed it. Only name an owner if the text actually states one; never invent one, use null instead. Leave a list empty ([]) if it does not apply. Never leave something out for being hard to categorise; put it in the field it fits best."""


def normalise_label(label: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", label.lower()).strip()


def resolve_label(claimed: str, candidates) -> str | None:
    """Match a model-claimed label to an existing one, tolerating minor
    wording drift (case, punctuation, trailing whitespace) a small model
    will not reproduce byte-for-byte even when it means to match."""
    claimed_norm = normalise_label(claimed)
    for name in candidates:
        if normalise_label(name) == claimed_norm:
            return name
    return None


def process_batch(batch_text: str, timestamp: str):
    entry = {"timestamp": timestamp, "batch": batch_text}
    try:
        classify = ollama_generate(CLASSIFY_PROMPT.format(index=store.topic_index(), batch=batch_text))
        entry["classify"] = classify
        claimed_broad = classify["broad_topic"]
        claimed_specific = classify["specific_topic"]

        matched_broad = resolve_label(claimed_broad, store.topics)
        broad = matched_broad or claimed_broad
        existing_subtopics = store.topics[broad]["subtopics"] if matched_broad else {}
        matched_specific = resolve_label(claimed_specific, existing_subtopics)
        specific = matched_specific or claimed_specific
        # An exact (normalised) name match at either level overrides the
        # model's own phrasing: a real match is stronger evidence than
        # whatever label it happened to produce this time.

        if matched_specific is None:
            extracted = ollama_generate(NEW_SUBTOPIC_PROMPT.format(broad=broad, specific=specific, batch=batch_text))
            entry["extracted"] = extracted
            store.apply_new_subtopic(broad, specific, timestamp, extracted)
        else:
            continuation = ((broad, specific) == store.last_path)
            extracted = ollama_generate(UPDATE_SUBTOPIC_PROMPT.format(
                broad=broad, specific=specific,
                description=existing_subtopics[specific]["description"],
                history=store.subtopic_history(broad, specific), batch=batch_text,
            ))
            entry["extracted"] = extracted
            store.apply_existing_subtopic(broad, specific, timestamp, extracted, continuation)
    except Exception as exc:  # noqa: BLE001 - surfaced to the demo UI, not swallowed
        entry["error"] = str(exc)
    store.append_log(entry)


def worker_loop():
    while True:
        batch_text, timestamp = batch_queue.get()
        process_batch(batch_text, timestamp)


def feed_transcript(transcript: str, min_words: int, max_extra_words: int, words_per_second: float):
    words = transcript.split()
    store.words_total = len(words)
    buffer = []
    for i, word in enumerate(words):
        if feed_stop.is_set():
            store.status = "idle"
            return
        buffer.append(word)
        store.words_fed = i + 1
        ready = len(buffer) >= min_words and (
            ends_sentence(word) or len(buffer) >= min_words + max_extra_words
        )
        if ready:
            batch_queue.put((" ".join(buffer), seconds_to_clock(store.words_fed / words_per_second)))
            buffer = []
        time.sleep(1.0 / words_per_second)
    if buffer:
        batch_queue.put((" ".join(buffer), seconds_to_clock(store.words_fed / words_per_second)))
    store.status = "done"


def seconds_to_clock(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


class Handler(BaseHTTPRequestHandler):
    def _json(self, payload, status=200):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            data = (STATIC_DIR / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif self.path == "/state":
            self._json(store.snapshot())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        payload = json.loads(raw or b"{}")

        if self.path == "/start":
            store.reset()
            feed_stop.clear()
            threading.Thread(
                target=feed_transcript,
                args=(
                    payload["transcript"],
                    int(payload.get("min_words", 25)),
                    int(payload.get("max_extra_words", 15)),
                    float(payload.get("words_per_second", 8)),
                ),
                daemon=True,
            ).start()
            store.status = "feeding"
            self._json({"ok": True})
        elif self.path == "/stop":
            feed_stop.set()
            self._json({"ok": True})
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        pass


def main():
    threading.Thread(target=worker_loop, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Notulator demo on http://localhost:{PORT}")
    print(f"Expecting Ollama at {OLLAMA_HOST} serving model {MODEL!r}")
    server.serve_forever()


if __name__ == "__main__":
    main()
