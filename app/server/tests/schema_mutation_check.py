"""Run named schema guard mutations in isolated source copies."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mutation_runner import check_multi_target

MATCH='actual==candidate and all(tuple(actual[t])==tuple(candidate[t]) for t in actual)'
MUTANTS=[
    ('startup-preflight','db.py','try:validate_schema(conn)','try:pass','test_v5_missing_table_is_refused_before_any_write'),
    ('missing-table','schema.py','actual==candidate','all(columns==candidate.get(table) for table,columns in actual.items())','test_v5_missing_table_is_refused_before_any_write'),
    ('missing-column','schema.py','actual==candidate','actual.keys()==candidate.keys() and all(all(candidate[t].get(k)==v for k,v in cols.items()) for t,cols in actual.items())','test_v5_missing_column_is_refused_before_any_write'),
    ('declared-type','schema.py','actual==candidate','actual.keys()==candidate.keys() and all(actual[t].keys()==candidate[t].keys() for t in actual)','test_wrong_declared_type_is_refused'),
    ('empty-v0','schema.py',"if tables:raise RuntimeError('Unsupported database schema layout: version 0 must be empty.')",'if False:raise RuntimeError("disabled")','test_nonempty_version_zero_is_refused'),
]
MUTANTS=[(name,target,MATCH if old=='actual==candidate' else old,new,test) for name,target,old,new,test in MUTANTS]
MUTANTS.append(('column-order','schema.py',MATCH,'actual==candidate','test_reordered_columns_are_refused'))
MUTANTS += [
    ('primary-key','schema.py','if primary!=PRIMARY[table]:','if False:','test_missing_primary_key_is_refused'),
    ('unique-token','schema.py','if unique!={PRIMARY[table]}|UNIQUE.get(table,set()):','if False:','test_missing_token_uniqueness_is_refused'),
    ('nullability','schema.py','if any(bool(r[3])!=(r[1] not in NULLABLE.get(table,set())) for r in columns):','if False:','test_missing_not_null_is_refused'),
    ('defaults','schema.py','if any(r[4]!=DEFAULTS.get((table,r[1])) for r in columns):','if False:','test_changed_default_is_refused'),
    ('foreign-key','schema.py','if foreign!=expected:','if False:','test_missing_session_foreign_key_is_refused'),
    ('partial-unique','schema.py',"if index[4] or any(r[1]<0 or r[4]!='BINARY' for r in parts):",'if False:','test_partial_unique_index_cannot_replace_token_uniqueness'),
]


def main():
    return check_multi_target(MUTANTS, 'test_schema_integrity.py', 60, 'schema', 'schema')


if __name__=='__main__':
    raise SystemExit(main())
