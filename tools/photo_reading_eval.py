"""Measure the live photo reader against hand-typed baselines (WP4).

Put photographs and a baseline.json in one folder, ideally under evidence/raw/
(gitignored), and run:

    python tools/photo_reading_eval.py evidence/raw/photo-reading --effort low

baseline.json maps each photo to what is really written on it. A string means
the photo shows one note and the whole photo is its region; a list gives
several notes with normalised [x, y, width, height] boxes:

    {"note-01.jpg": "Test de handschrift eerst",
     "wall.jpg": [{"box": [0, 0, 0.5, 1], "text": "..."}, ...]}

Type the baseline before looking at the model's output, so the model cannot
influence it. A text of null reads the region without scoring it; a person then
judges the reading, and their correction becomes the baseline. Each photo goes through the same path as the live server:
media.sanitise, the marked regions, one ClaudeExtractor call. Results are
written next to the photos as JSON and Markdown; nothing is written to tracked
files unless the folder is tracked.
"""
import argparse
import json
import sys
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app' / 'server'))

from PIL import Image, ImageOps  # noqa: E402

from genai_server.adapters import ExtractionInput  # noqa: E402
from genai_server.claude_extractor import ClaudeExtractor  # noqa: E402
from genai_server.claude_synthesis import load_env_key  # noqa: E402
from genai_server.media import sanitise  # noqa: E402

# The browser redraws anything but a small PNG as a PNG that fits the server's
# 4 MiB stored-photo limit (app.mjs, uploadable); do the same here.
UPLOAD_LIMIT, UPLOAD_EDGE = int(3.5 * 1024 * 1024), 3200


def upload_bytes(path):
    raw = path.read_bytes()
    with Image.open(BytesIO(raw)) as image:
        if image.format == 'PNG' and len(raw) <= UPLOAD_LIMIT:
            return raw, 'image/png'
        image = ImageOps.exif_transpose(image).convert('RGB')
    scale = min(1, UPLOAD_EDGE / max(image.size))
    while True:
        size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
        output = BytesIO()
        image.resize(size, Image.LANCZOS).save(output, format='PNG')
        if output.tell() <= UPLOAD_LIMIT or size[0] < 64:
            return output.getvalue(), 'image/png'
        scale *= (UPLOAD_LIMIT / output.tell()) ** .5 * .95


def normal(text):
    return ' '.join(text.lower().split())


def distance(a, b):
    """Levenshtein distance in characters."""
    previous = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        current = [i]
        for j, y in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (x != y)))
        previous = current
    return previous[-1]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('folder', type=Path)
    parser.add_argument('--effort', choices=['low', 'medium', 'high'], default='low')
    args = parser.parse_args()
    load_env_key(ROOT / '.env')
    baseline = json.loads((args.folder / 'baseline.json').read_text(encoding='utf-8'))
    extractor = ClaudeExtractor(effort=args.effort)
    rows, calls = [], []
    for name, expected in baseline.items():
        raw, mime = upload_bytes(args.folder / name)
        stored, _, _, _ = sanitise(raw, mime)
        notes = [{'box': [0, 0, 1, 1], 'text': expected}] if isinstance(expected, str) else expected
        regions = tuple({'id': 'region_%03d' % (i + 1), 'box': n['box']} for i, n in enumerate(notes))
        started = time.monotonic()
        try:
            output = extractor.extract(ExtractionInput('eval', 1, 'image/png', stored, regions))
        except Exception as exc:  # one failed photo is a result, not the end of the run
            calls.append({'photo': name, 'error': '%s: %s' % (type(exc).__name__, exc)})
            print('%s: failed, %s' % (name, calls[-1]['error']))
            continue
        seconds = round(time.monotonic() - started, 1)
        calls.append({'photo': name, 'regions': len(regions), 'seconds': seconds, 'model': output.model,
                      'usage': output.usage})
        for note, read in zip(notes, output.notes):
            truth = normal(note['text']) if note['text'] is not None else None
            errors = distance(truth, normal(read['text'])) if truth is not None else None
            rows.append({'photo': name, 'region': read['region_id'], 'baseline': note['text'], 'read': read['text'],
                         'status': read['status'], 'confidence': read['confidence'],
                         'colour': read['colour']['hex'], 'char_errors': errors, 'chars': len(truth) if truth is not None else None,
                         'exact': errors == 0 if truth is not None else None})
        print('%s: %d note(s) in %.1f s' % (name, len(regions), seconds))
    scored = [r for r in rows if r['chars'] is not None]
    chars = sum(r['chars'] for r in scored)
    summary = {
        'date': datetime.now().isoformat(timespec='seconds'), 'effort': args.effort, 'notes': len(rows),
        'scored': len(scored), 'exact': sum(r['exact'] for r in scored), 'unreadable': sum(r['status'] == 'unreadable' for r in rows),
        'character_error_rate': round(sum(r['char_errors'] for r in scored) / chars, 4) if chars else None,
        'failed_photos': sum('error' in c for c in calls),
        'seconds': round(sum(c.get('seconds', 0) for c in calls), 1),
        'cost_usd': round(sum((c.get('usage') or {}).get('cost') or 0 for c in calls), 4),
        'normalisation': 'case and whitespace ignored; punctuation and [?] count as errors'}
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    out = args.folder / ('results-%s-%s' % (args.effort, stamp))
    out.with_suffix('.json').write_text(json.dumps({'summary': summary, 'calls': calls, 'notes': rows},
                                                   ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# Photo reading, effort %s, %s' % (args.effort, summary['date']), '',
             '%(exact)d of %(scored)d scored notes exact (%(notes)d read), character error rate %(character_error_rate)s, '
             '%(unreadable)d unreadable, %(failed_photos)d failed photos, %(seconds)s s, $%(cost_usd)s.' % summary,
             '', '| Photo | Baseline | Read | Status | Confidence | Errors |', '|---|---|---|---|---|---|']
    lines += ['| %s | %s | %s | %s | %s | %s |' % (r['photo'], r['baseline'], r['read'], r['status'], r['confidence'],
                                                   '%s/%s' % (r['char_errors'], r['chars']) if r['chars'] is not None else 'not scored') for r in rows]
    out.with_suffix('.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))
    print('Written to %s.json and .md' % out)


if __name__ == '__main__':
    main()
