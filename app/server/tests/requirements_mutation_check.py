"""Named criterion guard removals in disposable source copies."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mutation_runner import check_multi_target

MUTANTS = [
    ('criterion-identity', 'criteria.py',
     "patch['op'] == 'add' and not patch['entry_id'] or patch['op'] != 'add' and patch['entry_id'] in entries", 'True',
     'test_unknown_entry_cannot_be_updated'),
    ('synthetic-criterion', 'documents.py',
     "require(not output.synthetic, 'document_synthetic', 'Synthetic interpretations cannot become live criteria.')", 'pass',
     'test_synthetic_criteria_cannot_become_live_entries'),
    ('inferred-section', 'criteria.py',
     "value['basis'] != 'inferred' or value['category'] == 'clarification'", 'True',
     'test_inference_cannot_become_a_requirement'),
    ('numeric-evidence', 'criteria.py',
     "numerical_terms(value['text']) <= numerical_terms(supported)", 'True',
     'test_invented_numeric_targets_are_rejected'),
    ('stated-evidence', 'criteria.py',
     "value['basis'] != 'stated' or bool(patch['stated_quote'].strip()) and\n                any(patch['stated_quote'] in ref['quote'] for ref in patch['evidence'])", 'True',
     'test_stated_criterion_requires_explicit_quote'),
    ('quoted-evidence', 'criteria.py',
     "ref['source_id'] in sources and ref['quote'] in sources[ref['source_id']]['text']", 'True',
     'test_invented_evidence_is_rejected'),
    ('conflict-section', 'criteria.py',
     "not value['conflict'] or value['category'] == 'clarification'", 'True',
     'test_conflict_cannot_be_hidden_in_requirement_section'),
    ('human-conflict-resolution', 'criteria.py',
     "not old.get('conflict') or bool(value['conflict'])", 'True',
     'test_ai_cannot_hide_or_clear_a_conflict'),
    ('conflict-acceptance', 'documents.py',
     "not any(e['data'].get('conflict') for e in entries if not e['data'].get('removed'))", 'True',
     'test_conflicts_are_retained_and_block_acceptance_until_reviewed'),
    ('targeted-lifecycle', 'documents.py',
     "if not action or r['data']['document_type'] == intent", 'if True',
     'test_independent_collectors_and_targeted_voice_lifecycle'),
    ('requirements-provider-schema', 'document_model.py',
     "requirements = request.get('document_type') == 'requirements'", 'requirements = False',
     'test_requirements_use_their_own_prompt_and_schema'),
]

if __name__ == '__main__':
    check_multi_target(MUTANTS, 'test_requirements.py', 60, 'requirements')
