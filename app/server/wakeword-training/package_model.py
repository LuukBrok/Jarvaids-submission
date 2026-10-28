"""Package trained, reviewed local assets; never download or rename a reference phrase."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('keyword', 'melspectrogram', 'embedding', 'training_record', 'output'):
        parser.add_argument('--' + name.replace('_', '-'), type=Path, required=True)
    args = parser.parse_args()
    record = json.loads(args.training_record.read_text(encoding='utf-8'))
    if (record.get('phrase') != 'Hey Jarvaids' or
            record.get('pronunciation') != 'Hey Jar-vaydz' or
            record.get('pronunciation_reviewed') is not True or
            record.get('status') != 'trained'):
        parser.error('A completed custom training record with pronunciation review is required.')
    # Fail before copying anything if provenance or an input is missing.
    assets = {}
    for name in ('keyword', 'melspectrogram', 'embedding'):
        path = getattr(args, name)
        provenance = record['assets'][name]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != provenance['sha256'] or not provenance['licence'] or not provenance['source']:
            parser.error('Checksum or provenance mismatch for ' + name)
        assets[name] = dict(provenance, file=name + '.onnx')
    args.output.mkdir(parents=True, exist_ok=False)
    for name in assets:
        shutil.copyfile(getattr(args, name), args.output / assets[name]['file'])
    shutil.copyfile(args.training_record, args.output / 'training-record.json')
    manifest = {'phrase':'Hey Jarvaids', 'pronunciation':'Hey Jar-vaydz',
                'engine_version':'0.6.0', 'assets':assets}
    path = args.output / 'manifest.json'
    path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(path)


if __name__ == '__main__':
    main()
