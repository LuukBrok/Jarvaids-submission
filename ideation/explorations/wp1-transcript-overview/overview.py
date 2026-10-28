"""WP1 prototype: a transcript to a topic-tracked overview (F2.1, rolling minutes).

Reads an already-transcribed conversation (no transcriber model here: that is
F1.2/F1.3, already covered elsewhere in the repo) and produces an overview
organised by topic rather than by speaker turn. The transcript is walked in
order, in chunks, carrying a running state of topics:

  - A new subject becomes a new topic.
  - A topic is only written up as "closed" once the chunk itself shows the
    discussion reaching a conclusion or the group visibly moving on. Closing
    early flattens a discussion that has not concluded yet (flowchart.md F2.1).
  - If a later chunk returns to a topic that was already closed, that topic
    reopens and its summary is revised to the latest decision, then it can
    close again.
  - Who said which line is not kept in the summary: multiple speakers'
    fragments on one subject are folded into one description of the subject.

Every topic's summary carries verbatim quotes from the chunk that produced it,
checked against that chunk's text, so a person can trace a line in the
overview back to what was actually said (ignoring omissions or inventions is
the WP1 checklist item this exists for). A quote that does not verify is
dropped, never silently kept.

Usage:
    python3 overview.py --transcript meeting.txt --provider fixture
    python3 overview.py --transcript meeting.txt --provider claude --out overview.md

No key, no network and the `anthropic` package are needed for
--provider fixture; see README.md for what fixture mode is (and is not) good
for, and claude_overview.py for what --provider claude sends.
"""
import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path


def _normalise(text):
    return re.sub(r'\s+', ' ', text).strip().lower()


@dataclass
class Turn:
    text: str
    start: float = None
    end: float = None
    speaker: str = None


@dataclass
class Chunk:
    index: int
    text: str
    start: float = None
    end: float = None


@dataclass
class Topic:
    id: str
    title: str
    status: str  # "open" or "closed"
    summary: str
    first_chunk: int
    quotes: list = field(default_factory=list)  # [{"chunk": int, "quote": str}]
    reopened: int = 0  # how many times a closed topic was revisited


_TIMESTAMP_HEADER = re.compile(
    r'^(\d{1,2}:\d{2}(?::\d{2})?)\s*-->\s*(\d{1,2}:\d{2}(?::\d{2})?)\s*(?:(Speaker\s*\d+|[^\n]{1,40}?))?\s*$')


def _to_seconds(stamp):
    parts = [int(p) for p in stamp.split(':')]
    while len(parts) < 3:
        parts.insert(0, 0)
    h, m, s = parts
    return h * 3600 + m * 60 + s


def _parse_timestamped_blocks(raw):
    """"HH:MM --> HH:MM Speaker N" header line, then one or more wrapped
    lines of what was said, blocks separated by blank lines: the shape
    exported by several transcription tools (and what pandoc produces from
    a .docx with that layout). Returns None if the file does not look like
    this, so read_transcript can fall through to line-per-turn."""
    lines = raw.splitlines()
    if not any(_TIMESTAMP_HEADER.match(line.strip()) for line in lines):
        return None
    turns = []
    current = None
    for line in lines:
        stripped = line.strip()
        match = _TIMESTAMP_HEADER.match(stripped)
        if match:
            if current is not None and current['words']:
                turns.append(Turn(text=' '.join(current['words']), start=current['start'],
                                   end=current['end'], speaker=current['speaker']))
            current = {'start': _to_seconds(match.group(1)), 'end': _to_seconds(match.group(2)),
                       'speaker': match.group(3), 'words': []}
        elif stripped and current is not None:
            current['words'].append(stripped)
        # a non-blank line before any header (title, metadata) is dropped
    if current is not None and current['words']:
        turns.append(Turn(text=' '.join(current['words']), start=current['start'],
                           end=current['end'], speaker=current['speaker']))
    return turns


def parse_transcript_text(raw):
    """The actual format-sniffing, split out from read_transcript so webui.py
    can hand it pasted or uploaded text directly, without writing a file
    first: the segment JSON already used by
    app/server/genai_server/synthesis.py
    ({"segments": [{"start", "end", "text"}, ...]} or a bare list of those,
    so a real transcript from that pipeline needs no conversion to try this);
    a "HH:MM --> HH:MM Speaker N" block-per-turn export (see
    _parse_timestamped_blocks); or plain text, one turn per non-blank line
    (an optional "Speaker: " prefix is kept in the chunk text so a quote can
    still cite it, just never relied on for the summary)."""
    stripped = raw.strip()
    if stripped.startswith('{') or stripped.startswith('['):
        try:
            data = json.loads(stripped)
        except ValueError:
            data = None
        if data is not None:
            segments = data['segments'] if isinstance(data, dict) and 'segments' in data else data
            if isinstance(segments, list):
                return [Turn(text=s['text'].strip(), start=s.get('start'), end=s.get('end'),
                             speaker=s.get('speaker')) for s in segments if s.get('text', '').strip()]
    blocks = _parse_timestamped_blocks(raw)
    if blocks:
        return blocks
    return [Turn(text=line.strip()) for line in raw.splitlines() if line.strip()]


def read_transcript(path):
    """See parse_transcript_text for the format rules; this just reads the file."""
    return parse_transcript_text(Path(path).read_text(encoding='utf-8'))


def chunk_turns(turns, target_chars=3000, hard_cap_chars=6000):
    """Groups consecutive turns into chunks around target_chars, never
    splitting a turn, so a chunk is always a clean slice of what was said.
    A single turn longer than hard_cap_chars is chunked alone rather than
    merged, since merging would blow the target on every chunk after it."""
    chunks = []
    current, length = [], 0
    for turn in turns:
        turn_len = len(turn.text)
        if current and length + turn_len > target_chars:
            chunks.append(current)
            current, length = [], 0
        current.append(turn)
        length += turn_len
        if length >= hard_cap_chars:
            chunks.append(current)
            current, length = [], 0
    if current:
        chunks.append(current)

    result = []
    for i, group in enumerate(chunks):
        starts = [t.start for t in group if t.start is not None]
        ends = [t.end for t in group if t.end is not None]
        result.append(Chunk(index=i, text='\n'.join(t.text for t in group),
                             start=min(starts) if starts else None, end=max(ends) if ends else None))
    return result


def verify_quotes(quotes, chunk_text):
    """Keeps only quotes that actually occur in the chunk (ignoring case and
    spacing), the same check SYNTHESIS.md applies to claim quotes: a model
    stating it quoted the transcript is not the same as it having done so."""
    haystack = _normalise(chunk_text)
    return [q for q in quotes if q.strip() and _normalise(q) in haystack]


def apply_touched(topics, touched, chunk):
    """Merges one chunk's touched-topic updates into the running state.
    touched is the provider's output: a list of {id, is_new, title, status,
    summary, quotes}. An id already in `topics` is updated in place (a
    previously closed topic being touched again is how a reopen happens);
    an unknown id is created. Nothing not mentioned in `touched` changes,
    which is what lets a topic stay closed, unrevised, for chunks that never
    come back to it."""
    notes = []
    for item in touched:
        topic_id = item['id']
        quotes = verify_quotes(item.get('quotes', []), chunk.text)
        dropped = len(item.get('quotes', [])) - len(quotes)
        if dropped:
            notes.append('chunk %d, topic %r: dropped %d quote(s) not found in the chunk text'
                          % (chunk.index, item.get('title', topic_id), dropped))
        quote_records = [{'chunk': chunk.index, 'quote': q} for q in quotes]
        existing = topics.get(topic_id)
        if existing is None:
            topics[topic_id] = Topic(id=topic_id, title=item['title'], status=item['status'],
                                      summary=item['summary'], first_chunk=chunk.index, quotes=quote_records)
        else:
            if existing.status == 'closed' and item['status'] == 'open':
                existing.reopened += 1
            existing.title = item['title'] or existing.title
            existing.status = item['status']
            existing.summary = item['summary']
            existing.quotes.extend(quote_records)
    return notes


def generate_overview(turns, provider, chunk_chars=3000, on_progress=None):
    """Runs the whole transcript through `provider` chunk by chunk and
    returns (topics: dict[id, Topic], chunks: list[Chunk], notes: list[str],
    usage: dict). `provider` is a callable
    (chunk, open_topics, closed_topics) -> (touched_topics, usage_or_None)
    so a fixture and a real model adapter can share this loop; see
    claude_overview.py for the real one and fixture_provider() below for the
    offline one.

    `on_progress`, if given, is called as on_progress(event: dict) before and
    after every chunk ({'type': 'chunk_start'|'chunk_done', 'index', 'total',
    ...}). A single local-model call can take minutes with nothing else to
    show for it; without this, a long run looks identical to a hung one."""
    topics = {}
    chunks = chunk_turns(turns, target_chars=chunk_chars)
    all_notes = []
    total_usage = {'input_tokens': 0, 'output_tokens': 0}
    for chunk in chunks:
        if on_progress:
            on_progress({'type': 'chunk_start', 'index': chunk.index, 'total': len(chunks)})
        started = time.monotonic()
        open_topics = [{'id': t.id, 'title': t.title, 'summary': t.summary}
                       for t in topics.values() if t.status == 'open']
        closed_topics = [{'id': t.id, 'title': t.title, 'summary': t.summary}
                         for t in topics.values() if t.status == 'closed']
        touched, usage = provider(chunk, open_topics, closed_topics)
        chunk_notes = apply_touched(topics, touched, chunk)
        all_notes.extend(chunk_notes)
        if usage:
            total_usage['input_tokens'] += usage.get('input_tokens', 0)
            total_usage['output_tokens'] += usage.get('output_tokens', 0)
        if on_progress:
            on_progress({'type': 'chunk_done', 'index': chunk.index, 'total': len(chunks),
                         'elapsed': time.monotonic() - started, 'topics_touched': len(touched),
                         'notes': chunk_notes})
    return topics, chunks, all_notes, total_usage


def fixture_provider(chunk, open_topics, closed_topics):
    """Deterministic, offline, no key: proves the chunking and state machine
    work on a transcript without calling a model. It is not a summariser: it
    titles a chunk from its first few words and closes it only on a crude
    keyword match. Never read its output as a real overview (README.md)."""
    closing_words = ('decided', 'agreed', "let's go with", 'we will', "we'll", 'final answer', 'conclusion',
                      'moving on', 'next topic')
    words = chunk.text.split()
    title = ' '.join(words[:6]) + ('...' if len(words) > 6 else '')
    status = 'closed' if any(w in chunk.text.lower() for w in closing_words) else 'open'
    first_line = chunk.text.splitlines()[0] if chunk.text else ''
    quote = ' '.join(first_line.split()[:12])
    topic_id = 'fixture-chunk-%d' % chunk.index
    return [{'id': topic_id, 'is_new': True, 'title': title or '(untitled)', 'status': status,
             'summary': '[fixture] ' + chunk.text[:280], 'quotes': [quote] if quote else []}], None


def render_markdown(topics, chunks, notes, usage, source, turn_count):
    ordered = sorted(topics.values(), key=lambda t: t.first_chunk)
    lines = [
        '# Transcript overview (WP1 prototype, F2.1)',
        '',
        '**Model-made content. Provisional until a person accepts it** (CLAUDE.md); nothing here has been reviewed yet.',
        '',
        'Source transcript: `%s`. %d turn(s) grouped into %d chunk(s).' % (source, turn_count, len(chunks)),
        '',
    ]
    for topic in ordered:
        badge = 'Closed' if topic.status == 'closed' else 'Still open when the transcript ended'
        lines.append('## %s' % topic.title)
        lines.append('*%s*%s' % (badge, ', revisited %d time(s) after an earlier close' % topic.reopened
                                  if topic.reopened else ''))
        lines.append('')
        lines.append(topic.summary)
        lines.append('')
        if topic.quotes:
            lines.append('**Evidence**')
            for q in topic.quotes:
                lines.append('- chunk %d: "%s"' % (q['chunk'], q['quote']))
            lines.append('')
    if notes:
        lines.append('## Processing notes')
        for n in notes:
            lines.append('- %s' % n)
        lines.append('')
    if usage.get('input_tokens') or usage.get('output_tokens'):
        lines.append('## Usage')
        lines.append('- input tokens: %d' % usage['input_tokens'])
        lines.append('- output tokens: %d' % usage['output_tokens'])
        lines.append('')
    return '\n'.join(lines)


def _escape(text):
    return (text or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def render_html_fragment(topics, chunks, notes, usage, source, turn_count):
    """The same content as render_markdown, as an HTML fragment of topic
    cards for webui.py (or anywhere else that wants it rendered rather than
    handed raw Markdown). Not a full page: webui.py wraps this in its own
    <html>/<head> with the shared stylesheet."""
    ordered = sorted(topics.values(), key=lambda t: t.first_chunk)
    parts = ['<p class="source">Source: <code>%s</code>. %d turn(s) grouped into %d chunk(s).</p>'
             % (_escape(source), turn_count, len(chunks))]
    for topic in ordered:
        closed = topic.status == 'closed'
        badge_class = 'closed' if closed else 'open'
        badge_text = 'Closed' if closed else 'Still open when the transcript ended'
        reopened = ('<span class="badge reopened">revisited %d&times; after an earlier close</span>'
                    % topic.reopened) if topic.reopened else ''
        quotes_html = ''
        if topic.quotes:
            items = ''.join('<li>chunk %d: &ldquo;%s&rdquo;</li>' % (q['chunk'], _escape(q['quote']))
                            for q in topic.quotes)
            quotes_html = '<details><summary>Evidence (%d quote(s))</summary><ul>%s</ul></details>' % (
                len(topic.quotes), items)
        parts.append(
            '<article class="topic">'
            '<header><h2>%s</h2><span class="badge %s">%s</span>%s</header>'
            '<p class="summary">%s</p>%s'
            '</article>' % (_escape(topic.title), badge_class, badge_text, reopened,
                            _escape(topic.summary), quotes_html))
    if notes:
        items = ''.join('<li>%s</li>' % _escape(n) for n in notes)
        parts.append('<details class="notes"><summary>Processing notes (%d)</summary><ul>%s</ul></details>'
                     % (len(notes), items))
    if usage.get('input_tokens') or usage.get('output_tokens'):
        parts.append('<p class="usage">Usage: %d input token(s), %d output token(s).</p>'
                     % (usage['input_tokens'], usage['output_tokens']))
    return '\n'.join(parts)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--transcript', required=True, help='path to a .txt transcript or synthesis.py-style segment JSON')
    parser.add_argument('--provider', choices=['fixture', 'claude', 'ollama'], default='fixture')
    parser.add_argument('--model', default=None, help='overrides the default model for --provider claude/ollama')
    parser.add_argument('--effort', default='medium', help='reasoning effort for --provider claude')
    parser.add_argument('--ollama-host', default=None, help='default http://localhost:11434, for --provider ollama')
    parser.add_argument('--chunk-chars', type=int, default=3000)
    parser.add_argument('--out', default=None, help='defaults to <transcript>.overview.md next to the input')
    parser.add_argument('--json-out', default=None, help='also write the raw topic state as JSON, for WP2/WP3 to consume')
    args = parser.parse_args(argv)

    turns = read_transcript(args.transcript)
    if not turns:
        print('No turns found in %s' % args.transcript, file=sys.stderr)
        return 1

    if args.provider == 'fixture':
        provider = fixture_provider
    elif args.provider == 'ollama':
        from ollama_overview import make_ollama_provider
        provider = make_ollama_provider(model=args.model, host=args.ollama_host)
    else:
        from claude_overview import make_claude_provider
        provider = make_claude_provider(model=args.model, effort=args.effort)

    def report(event):
        if event['type'] == 'chunk_start':
            print('Chunk %d/%d: calling %s...' % (event['index'] + 1, event['total'], args.provider),
                  flush=True)
        else:
            print('Chunk %d/%d: done in %.1fs, touched %d topic(s)'
                  % (event['index'] + 1, event['total'], event['elapsed'], event['topics_touched']), flush=True)

    topics, chunks, notes, usage = generate_overview(turns, provider, chunk_chars=args.chunk_chars,
                                                      on_progress=report)

    out_path = Path(args.out) if args.out else Path(args.transcript).with_suffix('.overview.md')
    out_path.write_text(render_markdown(topics, chunks, notes, usage, args.transcript, len(turns)), encoding='utf-8')
    print('Wrote %s (%d topic(s) from %d chunk(s))' % (out_path, len(topics), len(chunks)))

    if args.json_out:
        payload = {'topics': [{'id': t.id, 'title': t.title, 'status': t.status, 'summary': t.summary,
                                'first_chunk': t.first_chunk, 'reopened': t.reopened, 'quotes': t.quotes}
                               for t in sorted(topics.values(), key=lambda t: t.first_chunk)],
                   'usage': usage}
        Path(args.json_out).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
        print('Wrote %s' % args.json_out)

    if notes:
        print('%d processing note(s), see the output file.' % len(notes), file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
