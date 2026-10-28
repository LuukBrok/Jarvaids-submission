"""Typed requirement proposals and evidence checks, independent of persistence."""
import re
from .validation import fields, require, text

CRITERION_FIELDS = ('text', 'category', 'basis', 'conflict')
CATEGORIES = ('requirement', 'wish', 'clarification')
EVIDENCE = {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
    'properties': {'source_id': {'type': 'string'}, 'quote': {'type': 'string'}},
    'required': ['source_id', 'quote']}}
CRITERION_PATCH_FIELDS = {
    'op': {'type': 'string', 'enum': ['add', 'update', 'remove']},
    **{key: {'type': 'string'} for key in ('entry_id', 'text', 'stated_quote', 'conflict')},
    'category': {'type': 'string', 'enum': list(CATEGORIES)},
    'basis': {'type': 'string', 'enum': ['stated', 'inferred']},
    'evidence': EVIDENCE,
}


def criterion(value):
    fields(value, CRITERION_FIELDS)
    text(value['text'], 'text', 800)
    text(value['conflict'], 'conflict', 1000, empty=True)
    require(value['category'] in CATEGORIES and value['basis'] in ('stated', 'inferred'),
            'document_entry', 'Choose a criterion section and stated or inferred basis.')
    return {key: value[key].strip() for key in CRITERION_FIELDS}


def numerical_terms(value):
    # Preserve spoken values. Normalising dates or converting units is not extraction.
    return set(re.findall(r'\b\d+(?:[.,]\d+)?(?:\s*(?:%|kg\b|km\b|mm\b|cm\b|mb\b|gb\b))?'
        r'|\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|'
        r'thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|'
        r'fifty|sixty|seventy|eighty|ninety|hundred|thousand|million)\b', value.casefold()))


def validate_criteria(data, request):
    sources = {line['id']: line for line in request['lines']}
    entries = {entry['id']: entry for entry in request['entries']}
    changed = set()
    for patch in data['changes']:
        fields(patch, CRITERION_PATCH_FIELDS)
        value = criterion({key: patch[key] for key in CRITERION_FIELDS})
        text(patch['entry_id'], 'entry_id', 80, empty=True)
        text(patch['stated_quote'], 'stated_quote', 4000, empty=True)
        require(patch['op'] in ('add', 'update', 'remove'), 'criterion_operation', 'Unknown criterion operation.')
        require(patch['op'] == 'add' and not patch['entry_id'] or patch['op'] != 'add' and patch['entry_id'] in entries,
                'criterion_identity', 'AI referenced an unknown criterion.')
        require(not patch['entry_id'] or patch['entry_id'] not in changed, 'criterion_identity', 'AI changed a criterion twice.')
        changed.add(patch['entry_id'])
        require(type(patch['evidence']) is list and 1 <= len(patch['evidence']) <= 24,
                'criterion_evidence', 'Criteria need transcript evidence.')
        for ref in patch['evidence']:
            fields(ref, ('source_id', 'quote'))
            text(ref['quote'], 'quote', 4000)
            require(ref['source_id'] in sources and ref['quote'] in sources[ref['source_id']]['text'],
                    'criterion_evidence', 'AI cited unknown or invented criterion evidence.')
        quotes = ' '.join(ref['quote'] for ref in patch['evidence'])
        old = entries.get(patch['entry_id'], {})
        supported = quotes + (' ' + old.get('text', '') if patch['op'] != 'add' else '')
        require(numerical_terms(value['text']) <= numerical_terms(supported),
                'criterion_number', 'A numerical target was not stated in the evidence.')
        require(value['basis'] != 'stated' or bool(patch['stated_quote'].strip()) and
                any(patch['stated_quote'] in ref['quote'] for ref in patch['evidence']),
                'criterion_stated', 'A stated criterion needs an explicit quoted statement.')
        require(value['basis'] != 'inferred' or value['category'] == 'clarification',
                'criterion_inference', 'AI-inferred criteria must remain suggestions needing clarification.')
        require(not value['conflict'] or value['category'] == 'clarification',
                'criterion_conflict', 'Conflicting criteria must remain visible for review.')
        require(not old.get('conflict') or bool(value['conflict']),
                'criterion_conflict', 'Only a human can clear a flagged conflict.')
