"""Batch synthesis: wall photographs and a Whisper transcript to one provisional
canvas proposal.

Three phases, each a model call followed by a deterministic gate:

1. Extract. Each photograph is read into its sticky notes, and the transcript
   into claims. A claim is one point with the transcript segments it came from
   and a verbatim quote, not a prose summary: a summary cannot cite anything,
   and F6.3 says every claim points to session evidence.
2. Reconcile. Photo notes and spoken claims that say the same thing become one
   point that keeps every source. Agreement between the wall and the room is
   evidence, so nothing is thrown away, and conflicts are flagged rather than
   settled by the model.
3. Structure. Points become a form (cluster, timeline, matrix, flow,
   hierarchy) with labelled groups and relations. The model never emits
   coordinates: pipelines.md section 0 B, the model chooses meaning and code
   chooses geometry.

Every gate gets one repair attempt, then falls back loudly to an output that
invents nothing (pipelines.md 4.1 S5). Everything this produces is provisional
until a person accepts it; nothing here writes to a session.

The bundled model is a synthetic fixture. The Claude adapter lives in
claude_synthesis.py and is optional, so CI never needs a key or a network.
"""
import argparse
import hashlib
import json
import math
import re
import sys
import time
import unicodedata
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Protocol

from PIL import Image, ImageOps

SCHEMA = 'jarvaids.synthesis/1'
FORMS = ('cluster', 'timeline', 'matrix', 'flow', 'hierarchy')
CLAIM_KINDS = ('point', 'decision', 'action', 'question')
NOTE_COLOURS = ('yellow', 'pink', 'blue', 'green', 'orange', 'white', 'other')
READINGS = ('readable', 'partial', 'unreadable')

# A cluster holds at most 24 members on the server (API.md, Clusters), so a
# group larger than that could never be accepted as one.
MAX_GROUP = 24
MAX_GROUPS = 12
# pipelines.md 4.1 S1 caps one visualisation call at 60 items, and the server
# caps a proposal at 60 refs. Past that the honest move is to split the session.
MAX_STRUCTURE_POINTS = 60
# Bounds on input, so a wrong file fails here rather than as a large bill.
MAX_SEGMENTS = 5000
MAX_TRANSCRIPT_CHARS = 400_000
MAX_PHOTO_BYTES = 25 * 1024 * 1024
MAX_PHOTO_PIXELS = 20_000_000
# pipelines.md 2.1 S2 downscales to a 2048 px long edge before upload.
MODEL_LONG_EDGE = 2048
DEFAULT_BUDGET_TOKENS = 300_000

REPO_ROOT = Path(__file__).resolve().parents[3]


class SynthesisError(Exception):
    """Input refused or run aborted. Nothing partial is presented as complete."""


class BudgetExceeded(SynthesisError):
    pass


class ModelFailure(Exception):
    """One model call produced nothing usable. The caller falls back loudly."""


@dataclass(frozen=True)
class ModelResult:
    data: object
    provider: str
    model: str
    synthetic: bool
    usage: dict


class SynthesisModel(Protocol):
    name: str
    def read_photo(self, image: bytes, mime: str, repair: dict | None) -> ModelResult: ...
    def extract_claims(self, segments: list, repair: dict | None) -> ModelResult: ...
    def reconcile(self, claims: list, repair: dict | None) -> ModelResult: ...
    def structure(self, points: list, form: str | None, repair: dict | None) -> ModelResult: ...


# Inputs ---------------------------------------------------------------------

def load_whisper(raw):
    """Whisper JSON to segments with ids we assign.

    Accepts openai-whisper's `{"segments": [...]}` and a bare list of
    `{start, end, text}`, which is what most faster-whisper scripts write.
    Ids come from position, not from the file, so a model can never cite an id
    the file did not have.
    """
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise SynthesisError('Transcript is not valid JSON.') from exc
    items = data.get('segments') if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise SynthesisError('Transcript JSON has no segment list.')
    if len(items) > MAX_SEGMENTS:
        raise SynthesisError('Transcript has more than %d segments.' % MAX_SEGMENTS)
    segments, skipped, chars = [], 0, 0
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise SynthesisError('Segment %d is not an object.' % index)
        start, end, text = item.get('start'), item.get('end'), item.get('text')
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
                   for v in (start, end)):
            raise SynthesisError('Segment %d needs numeric start and end.' % index)
        if not 0 <= start <= end:
            raise SynthesisError('Segment %d ends before it starts.' % index)
        if not isinstance(text, str):
            raise SynthesisError('Segment %d has no text.' % index)
        text = ' '.join(text.split())
        if not text:
            skipped += 1
            continue
        chars += len(text)
        segment = {'id': 't%d' % (len(segments) + 1), 'start': float(start), 'end': float(end), 'text': text}
        if isinstance(item.get('speaker'), str):
            segment['speaker'] = item['speaker']
        segments.append(segment)
    if chars > MAX_TRANSCRIPT_CHARS:
        raise SynthesisError('Transcript exceeds %d characters.' % MAX_TRANSCRIPT_CHARS)
    return segments, skipped


def prepare_photo(raw):
    """Decode, orient, flatten and re-encode a photograph before any model sees it.

    Fresh JPEG pixels carry no EXIF, so GPS and device data never leave the
    machine. This does not use media.sanitise because that path caps input at
    4 MiB for the server's upload route, and a phone photograph is often larger.
    Re-encoding removes metadata, not visible names or faces.
    """
    if len(raw) > MAX_PHOTO_BYTES:
        raise SynthesisError('Photograph exceeds 25 MiB.')
    try:
        with Image.open(BytesIO(raw), formats=['PNG', 'JPEG']) as probe:
            width, height = probe.size
            # An iPhone JPEG is an MPO: the photo plus an embedded preview frame.
            # Open reads the photo itself; only an animation is refused.
            if width * height > MAX_PHOTO_PIXELS or (getattr(probe, 'n_frames', 1) != 1 and probe.format != 'MPO'):
                raise SynthesisError('Photograph is too large or has several frames.')
            probe.verify()
        with Image.open(BytesIO(raw), formats=['PNG', 'JPEG']) as decoded:
            decoded.load()
            oriented = ImageOps.exif_transpose(decoded)
            rgba = oriented.convert('RGBA')
            clean = Image.new('RGB', rgba.size, 'white')
            clean.paste(rgba, mask=rgba.getchannel('A'))
            clean.thumbnail((MODEL_LONG_EDGE, MODEL_LONG_EDGE))
            output = BytesIO()
            clean.save(output, format='JPEG', quality=85)
            return output.getvalue(), clean.width, clean.height
    except SynthesisError:
        raise
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as exc:
        raise SynthesisError('Photograph could not be decoded.') from exc


# Gates ----------------------------------------------------------------------
# Each gate returns (value, errors). Errors are plain sentences, because they
# go back to the model in the one repair attempt and into the output file.

def _normal(text):
    text = unicodedata.normalize('NFKC', text).casefold()
    return ' '.join(re.sub(r'[^\w\s]', ' ', text).split())


def _list(data, key):
    value = data.get(key) if isinstance(data, dict) else None
    return value if isinstance(value, list) else None


def check_photo_notes(data):
    notes = _list(data, 'notes')
    if notes is None:
        return [], ['Output has no notes list.']
    kept, errors = [], []
    for index, note in enumerate(notes):
        if not isinstance(note, dict):
            errors.append('Note %d is not an object.' % index)
            continue
        text, colour, reading = note.get('text'), note.get('colour'), note.get('reading')
        if colour not in NOTE_COLOURS or reading not in READINGS or not isinstance(text, str):
            errors.append('Note %d needs text, a colour from the list and a reading status.' % index)
            continue
        if reading != 'unreadable' and not text.strip():
            errors.append('Note %d is marked %s but has no text.' % (index, reading))
            continue
        kept.append({'text': text.strip(), 'colour': colour, 'reading': reading})
    return kept, errors


def check_claims(data, segments):
    """Keep each claim whose citations exist and whose quote is really there.

    The quote check is the hallucination guard: a claim is kept only if its
    quote appears, after normalising case, punctuation and spacing, in the text
    of the segments it cites. A claim that fails is reported, never silently
    dropped and never silently kept.
    """
    claims = _list(data, 'claims')
    if claims is None:
        return [], ['Output has no claims list.']
    by_id = {s['id']: s for s in segments}
    kept, errors = [], []
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            errors.append('Claim %d is not an object.' % index)
            continue
        text, kind = claim.get('text'), claim.get('kind')
        cited, quote = claim.get('segment_ids'), claim.get('quote')
        if not isinstance(text, str) or not text.strip() or kind not in CLAIM_KINDS:
            errors.append('Claim %d needs text and a kind from the list.' % index)
            continue
        if not isinstance(cited, list) or not cited or not all(isinstance(c, str) for c in cited):
            errors.append('Claim %d cites no segments.' % index)
            continue
        unknown = [c for c in cited if c not in by_id]
        if unknown:
            errors.append('Claim %d cites segments that do not exist: %s.' % (index, ', '.join(unknown)))
            continue
        if not isinstance(quote, str) or not _normal(quote):
            errors.append('Claim %d has no quote.' % index)
            continue
        spoken = _normal(' '.join(by_id[c]['text'] for c in by_id if c in cited))
        if _normal(quote) not in spoken:
            errors.append('Claim %d quote is not in the segments it cites.' % index)
            continue
        kept.append({'text': text.strip(), 'kind': kind, 'segment_ids': sorted(set(cited), key=lambda c: int(c[1:])),
                     'quote': quote.strip()})
    return kept, errors


def check_reconcile(data, claims):
    """Every claim in exactly one point, or the whole answer is refused.

    Partial acceptance is wrong here: a claim missing from every point is a
    source the canvas silently loses, and a claim in two points is counted twice.
    """
    points = _list(data, 'points')
    if points is None:
        return None, ['Output has no points list.']
    known = {c['id'] for c in claims}
    seen, errors, kept = {}, [], []
    for index, point in enumerate(points):
        if not isinstance(point, dict):
            errors.append('Point %d is not an object.' % index)
            continue
        text, ids, conflict = point.get('text'), point.get('claim_ids'), point.get('conflict', '')
        if not isinstance(text, str) or not text.strip() or not isinstance(conflict, str):
            errors.append('Point %d needs text.' % index)
            continue
        if not isinstance(ids, list) or not ids or not all(isinstance(i, str) for i in ids):
            errors.append('Point %d lists no claims.' % index)
            continue
        for claim_id in ids:
            if claim_id not in known:
                errors.append('Point %d lists a claim that does not exist: %s.' % (index, claim_id))
            seen[claim_id] = seen.get(claim_id, 0) + 1
        kept.append({'text': text.strip(), 'claim_ids': list(dict.fromkeys(ids)), 'conflict': conflict.strip()})
    twice = sorted(i for i, n in seen.items() if n > 1)
    missing = sorted(known - set(seen))
    if twice:
        errors.append('Claims appear in more than one point: %s.' % ', '.join(twice))
    if missing:
        errors.append('Claims appear in no point: %s.' % ', '.join(missing))
    return (None, errors) if errors else (kept, [])


def check_structure(data, points, form=None):
    if not isinstance(data, dict):
        return None, ['Output is not an object.']
    errors = []
    chosen, reason = data.get('form'), data.get('reason')
    if chosen not in FORMS:
        errors.append('Form must be one of %s.' % ', '.join(FORMS))
    elif form and chosen != form:
        errors.append('The form was named as %s and must not be changed.' % form)
    if not isinstance(reason, str) or not reason.strip():
        errors.append('A one-line reason for the form is required.')
    known = {p['id'] for p in points}
    groups, relations = _list(data, 'groups'), _list(data, 'relations')
    if groups is None or relations is None:
        return None, errors + ['Output needs groups and relations lists.']
    if not 1 <= len(groups) <= MAX_GROUPS:
        errors.append('Use between 1 and %d groups.' % MAX_GROUPS)
    seen = {}
    for index, group in enumerate(groups):
        ids = group.get('point_ids') if isinstance(group, dict) else None
        label = group.get('label') if isinstance(group, dict) else None
        if (not isinstance(label, str) or not label.strip() or not isinstance(ids, list) or not ids
                or not all(isinstance(i, str) for i in ids)):
            errors.append('Group %d needs a label and points.' % index)
            continue
        if len(ids) > MAX_GROUP:
            errors.append('Group %d has more than %d points.' % (index, MAX_GROUP))
        for point_id in ids:
            if point_id not in known:
                errors.append('Group %d lists a point that does not exist: %s.' % (index, point_id))
            seen[point_id] = seen.get(point_id, 0) + 1
    twice = sorted(i for i, n in seen.items() if n > 1)
    missing = sorted(known - set(seen))
    if twice:
        errors.append('Points appear in more than one group: %s.' % ', '.join(twice))
    if missing:
        errors.append('Points appear in no group: %s.' % ', '.join(missing))
    for index, relation in enumerate(relations):
        ends = (relation.get('from'), relation.get('to')) if isinstance(relation, dict) else (None, None)
        if not all(isinstance(end, str) and end in known for end in ends) or ends[0] == ends[1]:
            errors.append('Relation %d must join two different existing points.' % index)
    if errors:
        return None, errors
    return {'form': chosen, 'reason': reason.strip(), 'fallback': False,
            'groups': [{'label': g['label'].strip(), 'point_ids': list(g['point_ids'])} for g in groups],
            'relations': [{'from': r['from'], 'to': r['to'], 'label': str(r.get('label', '')).strip()}
                          for r in relations]}, []


def support_of(sources):
    """Derived from the sources, never taken from the model: whether the wall
    and the room agree is a fact about provenance, not a judgement."""
    kinds = {s['kind'] for s in sources}
    return 'photo+speech' if kinds == {'photo', 'speech'} else kinds.pop()


# Running --------------------------------------------------------------------

class Ledger:
    """Counts every call and stops before one that would start over budget.

    The check is before the call, so a run can overshoot by at most one call.
    Stating that is cheaper than estimating a request's size in advance.
    """
    def __init__(self, budget_tokens):
        self.budget, self.calls = budget_tokens, []

    @property
    def spent(self):
        return sum(c['input_tokens'] + c['output_tokens'] for c in self.calls)

    def call(self, step, thunk):
        if self.spent >= self.budget:
            raise BudgetExceeded('Token budget of %d spent before %s.' % (self.budget, step))
        result = thunk()
        self.calls.append({'step': step, 'provider': result.provider, 'model': result.model,
                           'synthetic': result.synthetic,
                           'input_tokens': int(result.usage.get('input_tokens') or 0),
                           'output_tokens': int(result.usage.get('output_tokens') or 0)})
        return result


def _gated(ledger, step, ask, check):
    """One call, one repair if the gate refuses it, then give up.

    Returns (value, record). value is None when the step has to fall back.
    """
    record = {'step': step, 'attempts': 0, 'errors': [], 'fallback': False}
    repair = None
    for attempt in (1, 2):
        record['attempts'] = attempt
        try:
            result = ledger.call(step, lambda: ask(repair))
        except ModelFailure as exc:
            record['errors'] = ['Model call failed: %s.' % exc]
            break
        value, errors = check(result.data)
        record['errors'] = errors
        if not errors:
            return value, record
        repair = {'previous': result.data, 'errors': errors}
    record['fallback'] = True
    return None, record


def _clock(seconds):
    seconds = int(seconds)
    return '%d:%02d' % (seconds // 60, seconds % 60)


def run(photos, transcript, model, form=None, budget_tokens=DEFAULT_BUDGET_TOKENS):
    """photos: [(name, raw bytes)]. transcript: (name, raw bytes) or None."""
    if form is not None and form not in FORMS:
        raise SynthesisError('Form must be one of %s.' % ', '.join(FORMS))
    if not photos and transcript is None:
        raise SynthesisError('Give at least one photograph or a transcript.')
    ledger, gates, warnings, rejected = Ledger(budget_tokens), [], [], []
    inputs = {'photos': [], 'transcript': None}

    # Phase 1a: photographs to notes.
    photo_notes, claims = [], []
    for number, (name, raw) in enumerate(photos, 1):
        image, width, height = prepare_photo(raw)
        notes, record = _gated(ledger, 'photo:%s' % name,
                               lambda repair: model.read_photo(image, 'image/jpeg', repair), check_photo_notes)
        gates.append(record)
        inputs['photos'].append({'file': name, 'sha256': hashlib.sha256(raw).hexdigest(),
                                 'sent_pixels': [width, height], 'notes': len(notes or [])})
        if notes is None:
            warnings.append('Photograph %s could not be read; none of its notes are included.' % name)
            continue
        for index, note in enumerate(notes, 1):
            note_id = 'p%d.%d' % (number, index)
            photo_notes.append(dict(note, id=note_id, file=name))
            if note['reading'] == 'unreadable':
                warnings.append('Note %s in %s is unreadable and needs typing by hand.' % (index, name))
                continue
            claims.append({'id': note_id, 'text': note['text'], 'kind': 'point',
                           'sources': [{'kind': 'photo', 'file': name, 'note': index,
                                        'colour': note['colour'], 'reading': note['reading']}]})

    # Phase 1b: transcript to claims. Partial acceptance is right here: a claim
    # that fails its quote check is reported and the rest still stand.
    if transcript is not None:
        name, raw = transcript
        segments, skipped = load_whisper(raw)
        inputs['transcript'] = {'file': name, 'sha256': hashlib.sha256(raw).hexdigest(),
                                'segments': len(segments), 'empty_segments_skipped': skipped,
                                'duration_s': segments[-1]['end'] if segments else 0}
        by_id = {s['id']: s for s in segments}
        record = {'step': 'transcript', 'attempts': 0, 'errors': [], 'fallback': False}
        kept, claim_errors, repair = [], [], None
        for attempt in (1, 2):
            record['attempts'] = attempt
            try:
                result = ledger.call('transcript', lambda: model.extract_claims(segments, repair))
            except ModelFailure as exc:
                # A failed repair keeps what the first answer got right.
                record['errors'].append('Model call failed: %s.' % exc)
                record['fallback'] = attempt == 1
                break
            kept, claim_errors = check_claims(result.data, segments)
            record['errors'] = list(claim_errors)
            if not claim_errors:
                break
            repair = {'previous': result.data, 'errors': claim_errors}
        if record['fallback']:
            warnings.append('No claims were taken from the transcript.')
        elif claim_errors:
            rejected.extend({'step': 'transcript', 'reason': e} for e in claim_errors)
            warnings.append('%d transcript claims failed their checks and were left out.' % len(claim_errors))
        gates.append(record)
        for index, claim in enumerate(kept, 1):
            cited = [by_id[i] for i in claim['segment_ids']]
            speakers = sorted({s['speaker'] for s in cited if 'speaker' in s})
            claims.append({'id': 'c%d' % index, 'text': claim['text'], 'kind': claim['kind'],
                           'sources': [{'kind': 'speech', 'segment_ids': claim['segment_ids'],
                                        'start': cited[0]['start'], 'end': cited[-1]['end'],
                                        'speakers': speakers, 'quote': claim['quote']}]})

    # Phase 2: reconcile.
    by_claim = {c['id']: c for c in claims}
    merged = None
    if claims:
        public = [{'id': c['id'], 'text': c['text'], 'kind': c['kind'], 'from': c['sources'][0]['kind']}
                  for c in claims]
        merged, record = _gated(ledger, 'reconcile', lambda repair: model.reconcile(public, repair),
                                lambda data: check_reconcile(data, claims))
        gates.append(record)
    if merged is None:
        if claims:
            warnings.append('Reconciliation failed its checks; every claim is shown separately, nothing merged.')
        merged = [{'text': c['text'], 'claim_ids': [c['id']], 'conflict': ''} for c in claims]
    points = []
    for index, point in enumerate(merged, 1):
        members = [by_claim[i] for i in point['claim_ids']]
        sources = [s for c in members for s in c['sources']]
        kinds = {c['kind'] for c in members}
        points.append({'id': 'n%d' % index, 'text': point['text'], 'kind': kinds.pop() if len(kinds) == 1 else 'point',
                       'support': support_of(sources), 'conflict': point['conflict'] or None,
                       'claim_ids': point['claim_ids'], 'source_texts': [c['text'] for c in members],
                       'sources': sources})

    # Phase 3: structure.
    structure = None
    if 0 < len(points) <= MAX_STRUCTURE_POINTS:
        public = [{'id': p['id'], 'text': p['text'], 'kind': p['kind'], 'support': p['support']} for p in points]
        structure, record = _gated(ledger, 'structure', lambda repair: model.structure(public, form, repair),
                                   lambda data: check_structure(data, points, form))
        gates.append(record)
        if structure is None:
            warnings.append('Structure failed its checks; points are listed in source order, unorganised.')
    elif points:
        warnings.append('%d points is over the %d a single structure call takes; split the session.'
                        % (len(points), MAX_STRUCTURE_POINTS))
    if structure is None:
        structure = {'form': 'ordered', 'reason': 'Fallback: no organisation was proposed.', 'fallback': True,
                     'groups': [{'label': 'Not organised', 'point_ids': [p['id'] for p in points]}] if points else [],
                     'relations': []}

    providers = sorted({(c['provider'], c['model']) for c in ledger.calls})
    return {
        'schema': SCHEMA,
        'provisional': True,
        'review': 'Nothing here is accepted. Every point needs a person to accept, edit or reject it.',
        'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'synthetic': any(c['synthetic'] for c in ledger.calls) or not ledger.calls,
        'producers': [{'provider': p, 'model': m} for p, m in providers],
        'inputs': inputs,
        'photo_notes': photo_notes,
        'claims': claims,
        'points': points,
        'structure': structure,
        'gates': gates,
        'rejected': rejected,
        'warnings': warnings,
        'usage': {'calls': len(ledger.calls), 'budget_tokens': ledger.budget,
                  'input_tokens': sum(c['input_tokens'] for c in ledger.calls),
                  'output_tokens': sum(c['output_tokens'] for c in ledger.calls),
                  'by_call': ledger.calls},
    }


# Reading the result ---------------------------------------------------------

def to_markdown(document):
    by_id = {p['id']: p for p in document['points']}
    producers = ', '.join('%s %s' % (p['provider'], p['model']) for p in document['producers']) or 'none'
    lines = ['# Synthesis proposal', '',
             '**Provisional.** Made by %s%s. %s' % (producers, ', SYNTHETIC' if document['synthetic'] else '',
                                                     document['review']), '']
    if document['warnings']:
        lines += ['## Warnings', ''] + ['- ' + w for w in document['warnings']] + ['']
    structure = document['structure']
    lines += ['## %s' % structure['form'].capitalize(), '', '_%s_' % structure['reason'], '']
    for group in structure['groups']:
        lines += ['### ' + group['label'], '']
        for point_id in group['point_ids']:
            point = by_id[point_id]
            lines.append('- **%s** [%s, %s] %s' % (point_id, point['kind'], point['support'], point['text']))
            if point['conflict']:
                lines.append('  - Conflict: ' + point['conflict'])
            for source in point['sources']:
                if source['kind'] == 'photo':
                    lines.append('  - Photo %s, note %d (%s)' % (source['file'], source['note'], source['colour']))
                else:
                    lines.append('  - Speech %s to %s: "%s"' % (_clock(source['start']), _clock(source['end']),
                                                               source['quote']))
        lines.append('')
    if structure['relations']:
        lines += ['### Relations', ''] + ['- %s to %s: %s' % (r['from'], r['to'], r['label'])
                                          for r in structure['relations']] + ['']
    usage = document['usage']
    lines += ['## Usage', '', '%d calls, %d input and %d output tokens, budget %d.' % (
        usage['calls'], usage['input_tokens'], usage['output_tokens'], usage['budget_tokens']), '']
    return '\n'.join(lines)


# Fixture --------------------------------------------------------------------

class FixtureSynthesisModel:
    """Deterministic and offline, like FixtureExtractor: it proves the gates and
    the plumbing, and claims nothing about reading, merging or organising."""
    name = 'fixture'
    usage = {'input_tokens': 0, 'output_tokens': 0}

    def _result(self, data):
        return ModelResult(data, 'fixture', 'synthetic-v1', True, dict(self.usage))

    def read_photo(self, image, mime, repair):
        return self._result({'notes': [{'text': 'FIXTURE ONLY, note %d; no OCR performed.' % i,
                                        'colour': 'yellow', 'reading': 'readable'} for i in (1, 2)]})

    def extract_claims(self, segments, repair):
        return self._result({'claims': [{'text': 'FIXTURE ONLY: ' + s['text'], 'kind': 'point',
                                         'segment_ids': [s['id']], 'quote': s['text'][:60]} for s in segments]})

    def reconcile(self, claims, repair):
        return self._result({'points': [{'text': c['text'], 'claim_ids': [c['id']], 'conflict': ''} for c in claims]})

    def structure(self, points, form, repair):
        ids = [p['id'] for p in points]
        groups = [{'label': 'Fixture group %d' % (i // MAX_GROUP + 1), 'point_ids': ids[i:i + MAX_GROUP]}
                  for i in range(0, len(ids), MAX_GROUP)]
        return self._result({'form': form or 'cluster', 'reason': 'FIXTURE ONLY, no form selection performed.',
                             'groups': groups, 'relations': []})


# Command line ---------------------------------------------------------------

def output_allowed(path, repo_root=REPO_ROOT):
    """Results quote the transcript, so they belong in evidence/raw/, which is
    gitignored, or outside the repository. AGENTS.md: transcripts carrying
    identifiers never enter the repository."""
    path, repo_root = Path(path).resolve(), Path(repo_root).resolve()
    return not path.is_relative_to(repo_root) or path.is_relative_to(repo_root / 'evidence' / 'raw')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Photographs and a Whisper transcript to a provisional canvas proposal.')
    parser.add_argument('--photo', action='append', default=[], help='PNG or JPEG of the wall; repeat for several')
    parser.add_argument('--transcript', help='Whisper JSON with segment timestamps')
    parser.add_argument('--out', help='JSON output path; a .md twin is written beside it')
    parser.add_argument('--provider', choices=('fixture', 'claude'), default='fixture')
    parser.add_argument('--form', choices=FORMS, help='Name the form instead of letting the model choose')
    parser.add_argument('--budget-tokens', type=int, default=DEFAULT_BUDGET_TOKENS)
    parser.add_argument('--effort', choices=('low', 'medium', 'high', 'xhigh', 'max'), default='medium')
    args = parser.parse_args(argv)

    out = Path(args.out) if args.out else (
        REPO_ROOT / 'evidence' / 'raw' / 'synthesis' / time.strftime('synthesis-%Y%m%d-%H%M%S.json'))
    if not output_allowed(out):
        parser.error('Output quotes the transcript; write it under evidence/raw/ or outside the repository.')
    try:
        if args.provider == 'claude':
            from .claude_synthesis import ClaudeSynthesisModel, load_env_key
            load_env_key(REPO_ROOT / '.env')
            model = ClaudeSynthesisModel(effort=args.effort)
        else:
            model = FixtureSynthesisModel()
        photos = [(Path(p).name, Path(p).read_bytes()) for p in args.photo]
        transcript = (Path(args.transcript).name, Path(args.transcript).read_bytes()) if args.transcript else None
        document = run(photos, transcript, model, args.form, args.budget_tokens)
    except (SynthesisError, OSError) as exc:
        print('synthesis: ' + str(exc), file=sys.stderr)
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    out.with_suffix('.md').write_text(to_markdown(document), encoding='utf-8')
    for warning in document['warnings']:
        print('warning: ' + warning, file=sys.stderr)
    print('%s (%d points, %d calls, %d tokens)' % (out, len(document['points']), document['usage']['calls'],
                                                     document['usage']['input_tokens'] + document['usage']['output_tokens']))
    return 0


if __name__ == '__main__':
    # Run the package's copy of this module, not __main__'s. Under `python -m`
    # this file is loaded twice, and claude_synthesis raises the package's
    # SynthesisError and ModelFailure, which __main__'s except clauses would
    # not recognise: a single refusal would crash the run instead of falling back.
    from genai_server.synthesis import main as package_main
    raise SystemExit(package_main())
