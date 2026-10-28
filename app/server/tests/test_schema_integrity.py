"""Rejected schemas remain byte-identical; recognised migration stages restart."""
import secrets
import shutil
import sqlite3
import unittest
from pathlib import Path
from genai_server.db import Database, SCHEMA
from genai_server.schema import layout


class SchemaIntegrityTests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).resolve().parents[1]/'.local'/'schema-tests';root.mkdir(parents=True,exist_ok=True)
        self.directory=root/secrets.token_hex(16);self.directory.mkdir()
        self.addCleanup(shutil.rmtree,self.directory)
        self.path=self.directory/'state.sqlite3'

    def change(self,sql):
        c=sqlite3.connect(self.path)
        try:c.executescript(sql);c.commit()
        finally:c.close()

    def refused_unchanged(self):
        before=self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError,'schema'):
            Database(self.path)
        self.assertEqual(before,self.path.read_bytes(),'preflight must not change input bytes')

    def rebuild(self,table,transform):
        c=sqlite3.connect(self.path)
        try:
            sql=c.execute('SELECT sql FROM sqlite_master WHERE name=?',(table,)).fetchone()[0]
            c.execute('DROP TABLE '+table);c.execute(transform(sql));c.commit()
        finally:c.close()

    def test_v5_missing_table_is_refused_before_any_write(self):
        Database(self.path);self.change('DROP TABLE invitations;');self.refused_unchanged()

    def test_v5_missing_column_is_refused_before_any_write(self):
        Database(self.path);self.change('ALTER TABLE actors DROP COLUMN agreed_at;');self.refused_unchanged()

    def test_unknown_table_is_refused_before_any_write(self):
        Database(self.path);self.change('CREATE TABLE unexpected(value TEXT);');self.refused_unchanged()

    def test_wrong_declared_type_is_refused(self):
        Database(self.path)
        self.rebuild('positions',lambda sql:sql.replace('x REAL','x TEXT'))
        self.refused_unchanged()

    def test_unknown_version_is_refused(self):
        Database(self.path);self.change('PRAGMA user_version=91;');self.refused_unchanged()

    def test_reordered_columns_are_refused(self):
        Database(self.path)
        self.rebuild('positions',lambda sql:sql.replace('x REAL NOT NULL, y REAL NOT NULL','y REAL NOT NULL, x REAL NOT NULL'))
        self.refused_unchanged()

    def test_missing_primary_key_is_refused(self):
        Database(self.path);self.rebuild('actors',lambda sql:sql.replace('id TEXT PRIMARY KEY','id TEXT'))
        self.change('CREATE UNIQUE INDEX replacement ON actors(id);');self.refused_unchanged()

    def test_missing_token_uniqueness_is_refused(self):
        Database(self.path);self.rebuild('actors',lambda sql:sql.replace('token_hash TEXT NOT NULL UNIQUE','token_hash TEXT NOT NULL'));self.refused_unchanged()

    def test_partial_unique_index_cannot_replace_token_uniqueness(self):
        Database(self.path);self.rebuild('actors',lambda sql:sql.replace('token_hash TEXT NOT NULL UNIQUE','token_hash TEXT NOT NULL'))
        self.change("CREATE UNIQUE INDEX incomplete ON actors(token_hash) WHERE role='facilitator';");self.refused_unchanged()

    def test_missing_not_null_is_refused(self):
        Database(self.path);self.rebuild('actors',lambda sql:sql.replace('name TEXT NOT NULL','name TEXT'));self.refused_unchanged()

    def test_changed_default_is_refused(self):
        Database(self.path);self.rebuild('actors',lambda sql:sql.replace('DEFAULT 0','DEFAULT 1'));self.refused_unchanged()

    def test_missing_session_foreign_key_is_refused(self):
        Database(self.path);self.rebuild('actors',lambda sql:sql.replace(' REFERENCES sessions(id)',''));self.refused_unchanged()

    def test_harmless_index_names_and_diagnostic_triggers_are_allowed(self):
        Database(self.path)
        self.change('CREATE INDEX arbitrary_name ON actors(name); CREATE UNIQUE INDEX redundant_token_index ON actors(token_hash); CREATE TRIGGER diagnostic AFTER INSERT ON actors BEGIN SELECT 1; END;')
        Database(self.path)

    def test_nonempty_version_zero_is_refused(self):
        self.change('CREATE TABLE unexpected(value TEXT);');self.refused_unchanged()

    def test_partial_v2_is_refused_before_migrating_media(self):
        self.change(SCHEMA+'ALTER TABLE sessions ADD COLUMN revision INTEGER; PRAGMA user_version=2;')
        self.refused_unchanged()

    def test_invalid_wal_schema_is_not_reconfigured(self):
        Database(self.path)
        self.change('DROP TABLE invitations; PRAGMA journal_mode=WAL;')
        self.refused_unchanged()
        c=sqlite3.connect(self.path)
        try:self.assertEqual('wal',c.execute('PRAGMA journal_mode').fetchone()[0])
        finally:c.close()

    def test_all_published_and_interrupted_stages_restart(self):
        # These shapes include B/C v2, A/E/D v2-v4, interrupted combined
        # stages retaining B/C positions while consent/media/control migrate,
        # and a converged v5 whose positions have no size yet.
        stages=[(1,False,1),(1,True,2),(2,False,2),(2,True,2),
                (3,False,3),(3,True,3),(4,False,4),(4,True,4),(5,True,5)]
        for shape,positions,claimed in stages:
            with self.subTest(shape=shape,positions=positions):
                path=self.directory/('stage-%d-%d.sqlite3'%(shape,positions))
                Database(path)
                c=sqlite3.connect(path)
                try:
                    # Every published stage predates the version 6 size columns.
                    for name in ('w','h'):c.execute('ALTER TABLE positions DROP COLUMN '+name)
                    if not positions:c.execute('DROP TABLE positions')
                    if shape<4:
                        c.execute('DROP TABLE control_requests');c.execute('ALTER TABLE actors DROP COLUMN control_seq')
                    if shape<3:c.execute('DROP TABLE media')
                    if shape<2:
                        c.execute('DROP TABLE invitations')
                        for name in ('revision','roster_revision'):c.execute('ALTER TABLE sessions DROP COLUMN '+name)
                        for name in ('agreed_at','withdrawn_at'):c.execute('ALTER TABLE actors DROP COLUMN '+name)
                    c.execute("INSERT INTO sessions(id,title,state,policy_version,seq,created,expires,lease) VALUES('session1','Retained','draft',1,0,1,9999,100)")
                    if positions:c.execute("INSERT INTO positions VALUES('session1','record1',20,30,7,1,'actor1',1)")
                    c.execute('PRAGMA user_version=%d'%claimed);c.commit()
                finally:c.close()
                for _ in range(2):
                    db=Database(path)
                    with db.transaction() as c:
                        self.assertEqual(6,c.execute('PRAGMA user_version').fetchone()[0])
                        self.assertEqual('Retained',c.execute('SELECT title FROM sessions').fetchone()[0])
                        if positions:self.assertEqual(7,c.execute('SELECT revision FROM positions').fetchone()[0])
