"""Rolling minutes: a transcript to a section-by-section provisional overview.

Pipeline 6 in pipelines.md, "notulation", runs live against a continuous
stream and never resummarises a topic that has not concluded (F2.1's named
risk). This module runs the same two deterministic/model split over a
complete transcript file, so a meeting can be evaluated offline before the
live loop exists:

1. Buffer and boundary (S1, S2). No model: split the transcript into
   candidate topic blocks on a long silence, a lexical shift between what was
   just said and what comes next, or a block simply growing too long.
2. Conclusion, summary, decisions, actions, open questions (S3 to S7). One
   model call per block. The model says whether the topic has concluded, and
   whether this block continues a topic already summarised rather than
   starting a new one, which is the "circling back" behaviour: a later block
   that resumes an earlier topic updates that topic's section instead of
   opening a second one, and a concluded block's summary is a full rewrite to
   the latest decision, not an append (F2.1 again: do not let a stale running
   note sit next to the answer that supersedes it).

A decision or action without a verbatim, segment-cited quote is discarded,
the same hallucination guard genai_server/synthesis.py uses for claims: a
free-text summary bullet cannot be checked, but a decision or action is a
strong enough claim that it must be (F6.3).

This package lives beside app/server/genai_server rather than inside it, and
reuses genai_server.synthesis's gate/ledger/output-path machinery by import
rather than copying it; nothing in genai_server itself is changed. The
bundled model is a synthetic fixture. The Claude adapter lives in
claude_adapter.py and is optional, so CI never needs a key or a network.
"""
import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Protocol

from genai_server.synthesis import (REPO_ROOT, DEFAULT_BUDGET_TOKENS, Ledger, ModelResult, SynthesisError,
                                    _gated, _normal, load_whisper, output_allowed)

SCHEMA = 'jarvaids.notulation/1'

# pipelines.md 6.3. Guesses, stated as guesses there; repeated here rather than
# imported because they are this module's own tuning, not a shared constant.
SILENCE_BOUNDARY_S = 8.0
MAX_BLOCK_WORDS = 2200
MIN_BLOCK_WORDS = 40
LEXICAL_WINDOW_WORDS = 40
LEXICAL_OVERLAP_THRESHOLD = 0.15


class NotulationModel(Protocol):
    name: str
    def summarize_block(self, block: list, context: dict, repair: dict | None) -> ModelResult: ...


# Boundary detection (S1, S2) -------------------------------------------------

def _words(text):
    return re.findall(r"[^\W\d_]+", text.lower())


def _jaccard(before, after):
    if not before or not after:
        return 0.0
    union = before | after
    return len(before & after) / len(union) if union else 0.0


def _window_words(segments, index, direction, limit=LEXICAL_WINDOW_WORDS):
    """The last (direction -1) or next (direction 1) `limit` words around a
    candidate cut, so a shift is judged on what was just said versus what is
    about to be, not on the whole meeting so far."""
    collected = []
    rng = range(index - 1, -1, -1) if direction < 0 else range(index, len(segments))
    for i in rng:
        collected.extend(_words(segments[i]['text']))
        if len(collected) >= limit:
            break
    return set(collected[-limit:] if direction < 0 else collected[:limit])


def detect_boundaries(segments):
    """Candidate topic boundaries between segments, each with its dominant
    reason and a confidence, mirroring pipelines.md 6.1 S2. Deterministic: no
    model runs here, which is why it costs 20 ms in the pipeline table and
    nothing here.

    A boundary can qualify on more than one signal at once (a long pause that
    also happens to land on a lexical shift); `reason` names only the most
    confident one for display, but `silence` records whether an 8-second-plus
    pause was among them regardless of which one "won", because that is the
    one signal strong enough on its own to stand even behind a very short
    block (see blocks_from_boundaries).
    """
    boundaries, word_count = [], 0
    for i in range(1, len(segments)):
        word_count += len(_words(segments[i - 1]['text']))
        reasons = []
        gap = segments[i]['start'] - segments[i - 1]['end']
        if gap >= SILENCE_BOUNDARY_S:
            reasons.append(('silence', min(1.0, gap / (2 * SILENCE_BOUNDARY_S))))
        overlap = _jaccard(_window_words(segments, i, -1), _window_words(segments, i, 1))
        if overlap <= LEXICAL_OVERLAP_THRESHOLD:
            reasons.append(('lexical_shift', round(1 - overlap, 2)))
        if word_count >= MAX_BLOCK_WORDS:
            reasons.append(('length_cap', 1.0))
        if reasons:
            reason, confidence = max(reasons, key=lambda r: r[1])
            boundaries.append({'index': i, 'reason': reason, 'confidence': round(confidence, 2),
                               'silence': any(r[0] == 'silence' for r in reasons)})
            word_count = 0
    return boundaries


def blocks_from_boundaries(segments, boundaries):
    """Segments cut at each boundary index, each block paired with the
    boundary that opened it (None for the first). A block left under
    MIN_BLOCK_WORDS by a lexical-shift or length-cap boundary that fired on a
    stray interjection is folded into the block before it, carrying that
    block's own opening boundary forward rather than losing or misattributing
    it. A silence boundary is not folded this way: an 8-second pause the room
    actually took is evidence enough on its own, even for a topic settled in
    a few short sentences, and the whole point of this rule is not to repeat
    F2.1's mistake by erasing a real, if small, decision.

    Returns a list of (block, boundary) pairs, since after merging a block no
    longer corresponds one-to-one with a position in `boundaries`.
    """
    cuts = [0] + [b['index'] for b in boundaries] + [len(segments)]
    by_index = {b['index']: b for b in boundaries}
    raw = [(segments[start:end], by_index.get(start)) for start, end in zip(cuts, cuts[1:]) if end > start]
    merged = []
    for block, boundary in raw:
        spurious = boundary is not None and not boundary['silence']
        if merged and spurious and sum(len(_words(s['text'])) for s in block) < MIN_BLOCK_WORDS:
            prev_block, prev_boundary = merged[-1]
            merged[-1] = (prev_block + block, prev_boundary)
        else:
            merged.append((block, boundary))
    return merged


# Gate (S3 to S7) --------------------------------------------------------------
# One call's answer, checked the same way synthesis.py checks a claim: a
# decision, action or open question is kept only if its quote is really in
# the segments it cites. A summary bullet is free prose and is not checked
# this way, the same split synthesis.py draws between a claim's quote and a
# reconciled point's text.

def _list(data, key):
    value = data.get(key) if isinstance(data, dict) else None
    return value if isinstance(value, list) else None


def _check_cited(data, key, by_id, required_text_fields, optional_fields=()):
    items = _list(data, key) or []
    kept, errors = [], []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append('%s %d is not an object.' % (key, index))
            continue
        missing = [f for f in required_text_fields if not isinstance(item.get(f), str) or not item[f].strip()]
        if missing:
            errors.append('%s %d needs %s.' % (key, index, ' and '.join(required_text_fields)))
            continue
        cited, quote = item.get('segment_ids'), item.get('quote')
        if not isinstance(cited, list) or not cited or not all(isinstance(c, str) for c in cited):
            errors.append('%s %d cites no segments.' % (key, index))
            continue
        unknown = [c for c in cited if c not in by_id]
        if unknown:
            errors.append('%s %d cites segments that do not exist: %s.' % (key, index, ', '.join(unknown)))
            continue
        if not isinstance(quote, str) or not _normal(quote):
            errors.append('%s %d has no quote.' % (key, index))
            continue
        spoken = _normal(' '.join(by_id[c]['text'] for c in cited))
        if _normal(quote) not in spoken:
            errors.append('%s %d quote is not in the segments it cites.' % (key, index))
            continue
        clean = {f: item[f].strip() for f in required_text_fields}
        for f in optional_fields:
            value = item.get(f)
            clean[f] = value.strip() if isinstance(value, str) and value.strip() else None
        clean['segment_ids'] = sorted(set(cited), key=lambda c: int(c[1:]) if c[1:].isdigit() else c)
        clean['quote'] = quote.strip()
        kept.append(clean)
    return kept, errors


def check_block(data, segments, known_topics, known_question_ids):
    """Gate for one block's model answer. Returns (value, errors); value is
    None, never partial, if anything fails, because a block with an unchecked
    decision or a dangling retirement is worse than one shown as a fallback."""
    if not isinstance(data, dict):
        return None, ['Output is not an object.']
    errors = []
    topic, concluded, continues = data.get('topic'), data.get('concluded'), data.get('continues_topic')
    if not isinstance(topic, str) or not topic.strip():
        errors.append('A non-empty topic label is required.')
    if not isinstance(concluded, bool):
        errors.append('Concluded must be true or false.')
    if continues is not None:
        if not isinstance(continues, str) or continues not in known_topics:
            errors.append('continues_topic must be null or one of the known topics: %s.'
                          % (', '.join(known_topics) if known_topics else '(none yet)'))
    summary = _list(data, 'summary')
    if not summary or not all(isinstance(b, str) and b.strip() for b in summary):
        errors.append('Summary needs at least one non-empty bullet.')
    by_id = {s['id']: s for s in segments}
    decisions, dec_errors = _check_cited(data, 'decisions', by_id, ('text',))
    actions, act_errors = _check_cited(data, 'actions', by_id, ('task',), optional_fields=('owner', 'due'))
    added, open_errors = _check_cited(data, 'open_questions_add', by_id, ('text',))
    retire = data.get('open_questions_retire', [])
    if retire is None:
        retire = []
    if not isinstance(retire, list) or not all(isinstance(r, str) for r in retire):
        errors.append('open_questions_retire must be a list of question ids.')
        retire = []
    else:
        unknown = sorted(r for r in retire if r not in known_question_ids)
        if unknown:
            errors.append('open_questions_retire names ids that do not exist: %s.' % ', '.join(unknown))
    errors += dec_errors + act_errors + open_errors
    if errors:
        return None, errors
    return {'topic': topic.strip(), 'concluded': concluded, 'continues_topic': continues,
            'summary': [b.strip() for b in summary], 'decisions': decisions, 'actions': actions,
            'open_questions_add': added, 'open_questions_retire': sorted(set(retire))}, []


def _merge_running(old, new):
    """Tier A: append what is not already there, rather than replace. Tier B,
    the full rewrite on conclusion, is the caller's job, not this one's."""
    seen = {_normal(b) for b in old}
    return old + [b for b in new if _normal(b) not in seen and not seen.add(_normal(b))]


def _dedupe(existing, added, keys):
    seen = {tuple(item.get(k) for k in keys) for item in existing}
    return existing + [item for item in added if tuple(item.get(k) for k in keys) not in seen]


# Running ----------------------------------------------------------------------

def run(transcript, model, budget_tokens=DEFAULT_BUDGET_TOKENS):
    """transcript: (name, raw bytes), Whisper JSON as synthesis.load_whisper reads."""
    name, raw = transcript
    segments, skipped = load_whisper(raw)
    if not segments:
        raise SynthesisError('Transcript has no usable segments.')
    boundaries = detect_boundaries(segments)
    blocks = blocks_from_boundaries(segments, boundaries)

    ledger, gates, warnings = Ledger(budget_tokens), [], []
    sections, by_topic, open_questions = [], {}, {}
    next_question = 1

    for block_number, (block, boundary) in enumerate(blocks, 1):
        known_topics = [s['topic'] for s in sections]
        context = {'known_topics': known_topics,
                   'open_questions': [{'id': qid, 'text': q['text']}
                                      for qid, q in open_questions.items() if q['status'] == 'open']}
        value, record = _gated(
            ledger, 'block:%d' % block_number,
            lambda repair: model.summarize_block(block, context, repair),
            lambda data: check_block(data, block, known_topics, set(open_questions)))
        gates.append(record)
        if value is None:
            warnings.append('Block %d (%s to %s) could not be summarised; shown as a gap, nothing invented.'
                            % (block_number, block[0]['id'], block[-1]['id']))
            value = {'topic': 'Untitled block %d' % block_number, 'concluded': False, 'continues_topic': None,
                     'summary': [], 'decisions': [], 'actions': [], 'open_questions_add': [],
                     'open_questions_retire': []}

        topic_key = _normal(value['topic'])
        target = by_topic.get(topic_key)
        if target is None and value['continues_topic']:
            target = by_topic.get(_normal(value['continues_topic']))

        block_record = {'block': block_number, 'segment_ids': [s['id'] for s in block], 'boundary': boundary}

        if target is None:
            sections.append({'id': 's%d' % (len(sections) + 1), 'topic': value['topic'],
                             'concluded': value['concluded'], 'summary': list(value['summary']),
                             'decisions': [], 'actions': [], 'blocks': [block_record]})
            target = len(sections) - 1
        else:
            section = sections[target]
            # Circling back: the latest word on a topic replaces the running
            # note once it concludes, rather than sitting beside it.
            section['summary'] = (list(value['summary']) if value['concluded']
                                  else _merge_running(section['summary'], value['summary']))
            section['topic'] = value['topic'] or section['topic']
            section['concluded'] = section['concluded'] or value['concluded']
            section['blocks'].append(block_record)
        by_topic[topic_key] = target

        section = sections[target]
        if value['concluded']:
            section['decisions'] = _dedupe(section['decisions'], value['decisions'], ('text', 'quote'))
            section['actions'] = _dedupe(section['actions'], value['actions'], ('task', 'quote'))

        for item in value['open_questions_add']:
            open_questions['q%d' % next_question] = dict(item, status='open', opened_in_block=block_number,
                                                          section=section['id'])
            next_question += 1
        for qid in value['open_questions_retire']:
            if qid in open_questions:
                open_questions[qid]['status'] = 'retired'
                open_questions[qid]['retired_in_block'] = block_number

    providers = sorted({(c['provider'], c['model']) for c in ledger.calls})
    return {
        'schema': SCHEMA,
        'provisional': True,
        'review': 'Nothing here is accepted. Every section, decision and action needs a person to accept, edit or reject it.',
        'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'synthetic': any(c['synthetic'] for c in ledger.calls) or not ledger.calls,
        'producers': [{'provider': p, 'model': m} for p, m in providers],
        'input': {'file': name, 'sha256': hashlib.sha256(raw).hexdigest(), 'segments': len(segments),
                  'empty_segments_skipped': skipped, 'blocks': len(blocks)},
        'sections': sections,
        'open_questions': [{'id': qid, **q} for qid, q in sorted(open_questions.items(), key=lambda kv: kv[0])],
        'gates': gates,
        'warnings': warnings,
        'usage': {'calls': len(ledger.calls), 'budget_tokens': ledger.budget,
                  'input_tokens': sum(c['input_tokens'] for c in ledger.calls),
                  'output_tokens': sum(c['output_tokens'] for c in ledger.calls), 'by_call': ledger.calls},
    }


# Reading the result -----------------------------------------------------------

def to_markdown(document):
    producers = ', '.join('%s %s' % (p['provider'], p['model']) for p in document['producers']) or 'none'
    lines = ['# Rolling minutes', '',
             '**Provisional.** Made by %s%s. %s' % (producers, ', SYNTHETIC' if document['synthetic'] else '',
                                                     document['review']), '']
    if document['warnings']:
        lines += ['## Warnings', ''] + ['- ' + w for w in document['warnings']] + ['']
    for section in document['sections']:
        status = 'concluded' if section['concluded'] else 'still running, nothing extracted yet'
        lines += ['## %s _(%s)_' % (section['topic'], status), '']
        lines += ['- ' + b for b in section['summary']] + ['']
        if section['decisions']:
            lines += ['**Decisions**', ''] + ['- %s ("%s")' % (d['text'], d['quote']) for d in section['decisions']] + ['']
        if section['actions']:
            lines += ['**Actions**', ''] + ['- %s%s%s ("%s")' % (
                a['task'], ' - %s' % a['owner'] if a['owner'] else ' - unassigned',
                ', due %s' % a['due'] if a['due'] else '', a['quote']) for a in section['actions']] + ['']
    if document['open_questions']:
        lines += ['## Open questions', '']
        for q in document['open_questions']:
            lines.append('- [%s] %s%s' % (q['status'], q['text'], ' (retired)' if q['status'] == 'retired' else ''))
        lines.append('')
    usage = document['usage']
    lines += ['## Usage', '', '%d calls, %d input and %d output tokens, budget %d.' % (
        usage['calls'], usage['input_tokens'], usage['output_tokens'], usage['budget_tokens']), '']
    return '\n'.join(lines)


# Fixture -----------------------------------------------------------------------

class FixtureNotulationModel:
    """Deterministic and offline: it proves the segmentation, the gate and the
    circling-back merge, and claims nothing about real summary quality."""
    name = 'fixture'
    usage = {'input_tokens': 0, 'output_tokens': 0}

    def _topic(self, block):
        counts = {}
        for segment in block:
            for word in _words(segment['text']):
                if len(word) > 4:
                    counts[word] = counts.get(word, 0) + 1
        if not counts:
            return 'untitled'
        best = max(counts.items(), key=lambda kv: (kv[1], -list(counts).index(kv[0])))
        return 'topic: %s' % best[0]

    def summarize_block(self, block, context, repair):
        topic = self._topic(block)
        continues = topic if topic in context['known_topics'] else None
        text = ' '.join(s['text'] for s in block)
        return ModelResult({'topic': topic, 'concluded': True, 'continues_topic': continues,
                            'summary': ['FIXTURE ONLY: ' + text[:200]], 'decisions': [], 'actions': [],
                            'open_questions_add': [], 'open_questions_retire': []},
                           'fixture', 'synthetic-v1', True, dict(self.usage))


# Command line ------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description='A transcript to a section-by-section rolling-minutes overview.')
    parser.add_argument('--transcript', required=True, help='Whisper JSON with segment timestamps')
    parser.add_argument('--out', help='JSON output path; a .md twin is written beside it')
    parser.add_argument('--provider', choices=('fixture', 'claude', 'ollama'), default='fixture')
    parser.add_argument('--budget-tokens', type=int, default=DEFAULT_BUDGET_TOKENS)
    parser.add_argument('--effort', choices=('low', 'medium', 'high', 'xhigh', 'max'), default='medium')
    parser.add_argument('--model', help='Model name for --provider ollama, e.g. llama3.1 (already pulled)')
    parser.add_argument('--ollama-host', default='http://127.0.0.1:11434',
                        help='Ollama server address for --provider ollama')
    args = parser.parse_args(argv)

    out = Path(args.out) if args.out else (
        REPO_ROOT / 'evidence' / 'raw' / 'notulation' / time.strftime('notulation-%Y%m%d-%H%M%S.json'))
    if not output_allowed(out):
        parser.error('Output quotes the transcript; write it under evidence/raw/ or outside the repository.')
    try:
        if args.provider == 'claude':
            from .claude_adapter import ClaudeNotulationModel
            from genai_server.claude_synthesis import load_env_key
            load_env_key(REPO_ROOT / '.env')
            model = ClaudeNotulationModel(effort=args.effort)
        elif args.provider == 'ollama':
            from .ollama_adapter import OllamaNotulationModel
            model = OllamaNotulationModel(args.model, host=args.ollama_host)
        else:
            model = FixtureNotulationModel()
        transcript = (Path(args.transcript).name, Path(args.transcript).read_bytes())
        document = run(transcript, model, args.budget_tokens)
    except (SynthesisError, OSError) as exc:
        print('notulation: ' + str(exc), file=sys.stderr)
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    out.with_suffix('.md').write_text(to_markdown(document), encoding='utf-8')
    for warning in document['warnings']:
        print('warning: ' + warning, file=sys.stderr)
    print('%s (%d sections, %d calls, %d tokens)' % (
        out, len(document['sections']), document['usage']['calls'],
        document['usage']['input_tokens'] + document['usage']['output_tokens']))
    return 0


if __name__ == '__main__':
    # See genai_server/synthesis.py's own note: run the package's copy of this
    # module, not __main__'s, so a raised SynthesisError or ModelFailure is the
    # class this file's except clauses recognise.
    from notulation.pipeline import main as package_main
    raise SystemExit(package_main())
