"""One durable database for all prototype-owned content, including export payloads."""
from contextlib import contextmanager
from pathlib import Path
import sqlite3
import base64
import hashlib
import json
import secrets
from io import BytesIO
from PIL import Image

from .media import sanitise
from .validation import Problem
from .schema import validate_schema


# One line per schema version, and the number is claimed here before it is used.
#
# This exists because two branches both numbered their migration version 2, one
# for positions and one for invitations, and nothing noticed: a database written
# by either side reported "2" and the other side believed it. Both branches were
# green alone. A registry does not prevent the mistake, it relocates it: two
# branches claiming the same number now collide on the same line of this dict and
# git refuses to merge them, which is a thirty-second conversation instead of a
# corrupted database.
#
# Adding a migration means adding a line here first. check_schema_versions.py
# fails the build if this and the chain below disagree.
SCHEMA_VERSIONS = {
    1: 'sessions, actors, records, versions, events, requests',
    2: 'invitations, session and roster revisions, actor consent timestamps',
    3: 'media, holding sanitised image bytes outside the record',
    4: 'control_requests and actor control sequences',
    5: 'positions, and folding the old placement items into them',
    6: 'positions gain nullable w and h, a size for canvas objects',
}
CURRENT_VERSION = max(SCHEMA_VERSIONS)


SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, state TEXT NOT NULL,
 policy_version INTEGER NOT NULL, seq INTEGER NOT NULL DEFAULT 0,
 created REAL NOT NULL, expires REAL NOT NULL, lease REAL NOT NULL,
 deletion_hash TEXT, deleted_at REAL
);
CREATE TABLE IF NOT EXISTS actors (
 id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id),
 name TEXT NOT NULL, role TEXT NOT NULL, token_hash TEXT NOT NULL UNIQUE,
 consent_version INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS records (
 id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id),
 kind TEXT NOT NULL, revision INTEGER NOT NULL, data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS records_session_kind ON records(session_id,kind);
CREATE TABLE IF NOT EXISTS versions (
 session_id TEXT NOT NULL REFERENCES sessions(id), record_id TEXT NOT NULL,
 revision INTEGER NOT NULL, data TEXT NOT NULL,
 PRIMARY KEY(record_id,revision)
);
CREATE TABLE IF NOT EXISTS events (
 session_id TEXT NOT NULL REFERENCES sessions(id), seq INTEGER NOT NULL,
 type TEXT NOT NULL, actor_id TEXT NOT NULL, created REAL NOT NULL, data TEXT NOT NULL,
 PRIMARY KEY(session_id,seq)
);
CREATE TABLE IF NOT EXISTS requests (
 session_id TEXT NOT NULL REFERENCES sessions(id), actor_id TEXT NOT NULL,
 request_id TEXT NOT NULL, fingerprint TEXT NOT NULL, result TEXT NOT NULL,
 PRIMARY KEY(session_id,actor_id,request_id)
);
PRAGMA user_version=1;
"""


class Connection(sqlite3.Connection):
    changed=None


class Database:
    def __init__(self,path):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        conn=self.connect(validate=True)
        try:
            version=conn.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0,1,2,3,4,5,6):raise RuntimeError('Unsupported database schema version.')
            tables={row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            had_positions='positions' in tables
            # Both published histories used v2. Inspect the actual schema before advancing.
            if version==2 and 'invitations' not in tables:
                if not had_positions:raise RuntimeError('Unrecognised version 2 schema.')
                version=1
            if version==0:
                conn.executescript(SCHEMA)
                version=1
            if version==1:
                conn.executescript('''BEGIN IMMEDIATE;
                    ALTER TABLE sessions ADD COLUMN revision INTEGER NOT NULL DEFAULT 1;
                    ALTER TABLE sessions ADD COLUMN roster_revision INTEGER NOT NULL DEFAULT 1;
                    ALTER TABLE actors ADD COLUMN agreed_at REAL;
                    ALTER TABLE actors ADD COLUMN withdrawn_at REAL;
                    CREATE TABLE invitations (
                        id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id),
                        capability_hash TEXT NOT NULL UNIQUE, role TEXT NOT NULL,
                        expires REAL NOT NULL, revoked INTEGER NOT NULL DEFAULT 0,
                        actor_id TEXT, credential_hash TEXT, intent_hash TEXT
                    );
                    PRAGMA user_version=2;
                    COMMIT;''')
                version=2
            if version==2:
                self._migrate_media(conn);version=3
            if version==3:
                conn.executescript('''BEGIN IMMEDIATE;
                    ALTER TABLE actors ADD COLUMN control_seq INTEGER NOT NULL DEFAULT 0;
                    CREATE TABLE control_requests (
                        session_id TEXT NOT NULL REFERENCES sessions(id), actor_id TEXT NOT NULL,
                        request_id TEXT NOT NULL, sequence INTEGER NOT NULL,
                        fingerprint TEXT NOT NULL, result TEXT NOT NULL,
                        PRIMARY KEY(session_id,actor_id,request_id), UNIQUE(session_id,actor_id,sequence)
                    );
                    PRAGMA user_version=4;
                    COMMIT;''')
                version=4
            if version<5:
                conn.execute('BEGIN IMMEDIATE')
                try:
                    conn.execute('''CREATE TABLE IF NOT EXISTS positions (
                        session_id TEXT NOT NULL REFERENCES sessions(id), record_id TEXT NOT NULL,
                        x REAL NOT NULL, y REAL NOT NULL, revision INTEGER NOT NULL,
                        hand_placed INTEGER NOT NULL, placed_by TEXT NOT NULL, placed_at REAL NOT NULL,
                        PRIMARY KEY(session_id,record_id))''')
                    if not had_positions:fold_placements(conn)
                    conn.execute('PRAGMA user_version=5')
                    conn.commit()
                except BaseException:
                    conn.rollback();raise
                version=5
            if version==5:
                # A size for the canvas objects that need one (shape, text,
                # section). Nullable and left null on every existing row,
                # because a note's width follows its text and a guessed size
                # written here would be a second answer to that question.
                # One transaction, so an interrupted run stays at 5 and the
                # next start repeats the whole step rather than half of it.
                conn.executescript('''BEGIN IMMEDIATE;
                    ALTER TABLE positions ADD COLUMN w REAL;
                    ALTER TABLE positions ADD COLUMN h REAL;
                    PRAGMA user_version=6;
                    COMMIT;''')
        finally:
            conn.close()

    @staticmethod
    def _migrate_media(conn):
        conn.execute('BEGIN IMMEDIATE')
        try:
            conn.execute('''CREATE TABLE media (
                id TEXT NOT NULL, session_id TEXT NOT NULL REFERENCES sessions(id),
                digest TEXT NOT NULL, payload BLOB NOT NULL, mime TEXT NOT NULL,
                width INTEGER NOT NULL, height INTEGER NOT NULL,
                PRIMARY KEY(session_id,id), UNIQUE(session_id,digest))''')
            def rewrite(value,sid):
                if isinstance(value,list):return [rewrite(v,sid) for v in value]
                if not isinstance(value,dict):return value
                value={k:rewrite(v,sid) for k,v in value.items()}
                if value.get('type')=='image' and 'base64' in value:
                    encoded=value.pop('base64')
                    try:
                        raw=base64.b64decode(encoded,validate=True)
                        clean,mime,w,h=sanitise(raw,value.get('mime'))
                        with Image.open(BytesIO(raw)) as legacy_image:orientation=legacy_image.getexif().get(274,1)
                    except (Problem,ValueError,TypeError):
                        value.update(media_unavailable=True,byte_count=0,sanitisation_error='invalid_legacy_image')
                    else:
                        checksum=hashlib.sha256(clean).hexdigest()
                        old=conn.execute('SELECT id FROM media WHERE session_id=? AND digest=?',(sid,checksum)).fetchone()
                        mid=old['id'] if old else secrets.token_hex(16)
                        if not old:conn.execute('INSERT INTO media VALUES(?,?,?,?,?,?,?)',(mid,sid,checksum,clean,mime,w,h))
                        transforms={2:lambda x,y:(1-x,y),3:lambda x,y:(1-x,1-y),4:lambda x,y:(x,1-y),
                                    5:lambda x,y:(y,x),6:lambda x,y:(1-y,x),7:lambda x,y:(1-y,1-x),8:lambda x,y:(y,1-x)}
                        if orientation in transforms:
                            for region in value.get('regions',[]):
                                x,y,rw,rh=region['box'];transform=transforms[orientation]
                                corners=[transform(x,y),transform(x+rw,y),transform(x,y+rh),transform(x+rw,y+rh)]
                                xs,ys=zip(*corners);region['box']=[min(xs),min(ys),max(xs)-min(xs),max(ys)-min(ys)]
                        value.update(media_id=mid,mime=mime,width=w,height=h,byte_count=len(clean),sanitised=True)
                return value
            for table,column in (('records','data'),('versions','data'),('requests','result')):
                for row in conn.execute(f'SELECT rowid,session_id,{column} FROM {table}').fetchall():
                    updated=rewrite(json.loads(row[column]),row['session_id'])
                    conn.execute(f'UPDATE {table} SET {column}=? WHERE rowid=?',
                                 (json.dumps(updated,ensure_ascii=False,separators=(',',':')),row['rowid']))
            conn.execute('PRAGMA user_version=3')
            conn.commit()
        except BaseException:
            conn.rollback();raise

    def connect(self,validate=False):
        conn=sqlite3.connect(self.path,timeout=10,isolation_level=None,factory=Connection)
        conn.row_factory=sqlite3.Row
        if validate:
            try:validate_schema(conn)
            except BaseException:
                conn.close();raise
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA secure_delete=ON')
        conn.execute('PRAGMA journal_mode=DELETE')
        conn.execute('PRAGMA synchronous=FULL')
        return conn

    @contextmanager
    def transaction(self):
        conn=self.connect()
        try:
            conn.execute('BEGIN IMMEDIATE')
            conn.changed={}
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()


def fold_placements(conn):
    """Fold legacy accepted placements inside the caller migration transaction."""
    for row in conn.execute("SELECT id,session_id,revision,data FROM records WHERE kind='item' ORDER BY rowid").fetchall():
        data=json.loads(row['data'])
        if data.get('item_kind')!='placement' or data.get('status')!='accepted':continue
        for p in data.get('positions',[]):
            conn.execute('INSERT OR REPLACE INTO positions VALUES(?,?,?,?,?,?,?,?)',
                         (row['session_id'],p['id'],float(p['x']),float(p['y']),1,1,
                          data.get('accepted_by',''),data.get('created_at',0.0)))
        data['status']='superseded';data['superseded_reason']='position_model'
        revision=row['revision']+1;encoded=json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
        conn.execute('UPDATE records SET revision=?,data=? WHERE id=?',(revision,encoded,row['id']))
        conn.execute('INSERT INTO versions VALUES(?,?,?,?)',(row['session_id'],row['id'],revision,encoded))
