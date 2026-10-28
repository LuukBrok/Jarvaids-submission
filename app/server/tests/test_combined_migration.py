"""Both published schema histories converge without losing their owned data."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from genai_server.db import Database, SCHEMA
import sqlite3
import secrets
import shutil


class CombinedMigrationTests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).resolve().parents[1]/'.local'/'tests';root.mkdir(parents=True,exist_ok=True)
        directory=root/secrets.token_hex(16);directory.mkdir();self.addCleanup(shutil.rmtree,directory)
        self.path=directory/'state.sqlite3'

    def test_bc_version_two_keeps_positions_and_adds_consent_media_controls(self):
        c=sqlite3.connect(self.path)
        try:
            c.executescript(SCHEMA)
            c.execute("INSERT INTO sessions VALUES('session1','Old','draft',1,0,1000,9000,1300,NULL,NULL)")
            c.execute('CREATE TABLE positions(session_id TEXT NOT NULL REFERENCES sessions(id),record_id TEXT NOT NULL,x REAL NOT NULL,y REAL NOT NULL,revision INTEGER NOT NULL,hand_placed INTEGER NOT NULL,placed_by TEXT NOT NULL,placed_at REAL NOT NULL,PRIMARY KEY(session_id,record_id))')
            c.execute("INSERT INTO positions VALUES('session1','record1',20,30,7,1,'actor1',1000)")
            c.execute('PRAGMA user_version=2');c.commit()
        finally:c.close()
        for _ in range(2):
            db=Database(self.path)
            with db.transaction() as c:
                self.assertEqual(6,c.execute('PRAGMA user_version').fetchone()[0])
                self.assertEqual((20,30,7),tuple(c.execute('SELECT x,y,revision FROM positions').fetchone()))
                for table in ('invitations','media','control_requests'):c.execute('SELECT * FROM '+table)

    def test_ade_version_four_keeps_invitation_and_recovers_failed_position_migration(self):
        db=Database(self.path)
        with db.transaction() as c:
            c.execute("INSERT INTO sessions(id,title,state,policy_version,created,expires,lease) VALUES('session1','Old','draft',1,1000,9000,1300)")
            c.execute("INSERT INTO invitations(id,session_id,capability_hash,role,expires) VALUES('invite1','session1','hash1','viewer',2000)")
            c.execute('DROP TABLE positions');c.execute('PRAGMA user_version=4')
        with patch('genai_server.db.fold_placements',side_effect=RuntimeError('interrupted')):
            with self.assertRaises(RuntimeError):Database(self.path)
        c=db.connect()
        try:
            self.assertEqual(4,c.execute('PRAGMA user_version').fetchone()[0])
            self.assertIsNone(c.execute("SELECT name FROM sqlite_master WHERE name='positions'").fetchone())
        finally:c.close()
        db=Database(self.path)
        with db.transaction() as c:
            self.assertEqual(6,c.execute('PRAGMA user_version').fetchone()[0])
            self.assertEqual('hash1',c.execute('SELECT capability_hash FROM invitations').fetchone()[0])
