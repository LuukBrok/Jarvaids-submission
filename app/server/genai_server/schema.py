"""Recognise published database layouts before any migration writes.

Exact column names, declared types and integrity constraints reject partial migrations.
This is structural validation, not validation of application data or recovery
of a corrupt database. Extra tables/columns require an explicit migration.
"""

BASE = {
    'sessions': 'id:TEXT title:TEXT state:TEXT policy_version:INTEGER seq:INTEGER created:REAL expires:REAL lease:REAL deletion_hash:TEXT deleted_at:REAL',
    'actors': 'id:TEXT session_id:TEXT name:TEXT role:TEXT token_hash:TEXT consent_version:INTEGER',
    'records': 'id:TEXT session_id:TEXT kind:TEXT revision:INTEGER data:TEXT',
    'versions': 'session_id:TEXT record_id:TEXT revision:INTEGER data:TEXT',
    'events': 'session_id:TEXT seq:INTEGER type:TEXT actor_id:TEXT created:REAL data:TEXT',
    'requests': 'session_id:TEXT actor_id:TEXT request_id:TEXT fingerprint:TEXT result:TEXT',
}
POSITIONS = 'session_id:TEXT record_id:TEXT x:REAL y:REAL revision:INTEGER hand_placed:INTEGER placed_by:TEXT placed_at:REAL'
INVITATIONS = 'id:TEXT session_id:TEXT capability_hash:TEXT role:TEXT expires:REAL revoked:INTEGER actor_id:TEXT credential_hash:TEXT intent_hash:TEXT'
MEDIA = 'id:TEXT session_id:TEXT digest:TEXT payload:BLOB mime:TEXT width:INTEGER height:INTEGER'
# Schema 6: the size a shape, text or section needs. Nullable, see NULLABLE.
SIZE = ' w:REAL h:REAL'
CONTROLS = 'session_id:TEXT actor_id:TEXT request_id:TEXT sequence:INTEGER fingerprint:TEXT result:TEXT'
PRIMARY = {'sessions':('id',),'actors':('id',),'records':('id',),
           'versions':('record_id','revision'),'events':('session_id','seq'),
           'requests':('session_id','actor_id','request_id'),'positions':('session_id','record_id'),
           'invitations':('id',),'media':('session_id','id'),
           'control_requests':('session_id','actor_id','request_id')}
UNIQUE = {'actors':{('token_hash',)},'invitations':{('capability_hash',)},
          'media':{('session_id','digest')},'control_requests':{('session_id','actor_id','sequence')}}
NULLABLE = {'sessions':{'id','deletion_hash','deleted_at'},'actors':{'id','agreed_at','withdrawn_at'},
            'records':{'id'},'positions':{'w','h'},'invitations':{'id','actor_id','credential_hash','intent_hash'}}
DEFAULTS = {('sessions','seq'):'0',('sessions','revision'):'1',('sessions','roster_revision'):'1',
            ('actors','consent_version'):'0',('actors','control_seq'):'0',('invitations','revoked'):'0'}


def validate_constraints(conn, tables):
    for table in tables:
        quoted=table.replace('"','""')
        columns=list(conn.execute(f'PRAGMA table_info("{quoted}")'))
        primary=tuple(r[1] for r in sorted(columns,key=lambda r:r[5]) if r[5])
        if primary!=PRIMARY[table]:raise RuntimeError('Unsupported database schema primary key: '+table)
        if any(bool(r[3])!=(r[1] not in NULLABLE.get(table,set())) for r in columns):
            raise RuntimeError('Unsupported database schema nullability: '+table)
        if any(r[4]!=DEFAULTS.get((table,r[1])) for r in columns):
            raise RuntimeError('Unsupported database schema defaults: '+table)
        unique=set()
        for index in conn.execute(f'PRAGMA index_list("{quoted}")'):
            if not index[2]:continue
            name=index[1].replace('"','""')
            parts=[r for r in conn.execute(f'PRAGMA index_xinfo("{name}")') if r[5]]
            if index[4] or any(r[1]<0 or r[4]!='BINARY' for r in parts):
                raise RuntimeError('Unsupported database schema unique index: '+table)
            unique.add(tuple(r[2] for r in parts))
        if unique!={PRIMARY[table]}|UNIQUE.get(table,set()):
            raise RuntimeError('Unsupported database schema uniqueness: '+table)
        foreign={(r[2],r[3],r[4],r[5],r[6],r[7]) for r in conn.execute(f'PRAGMA foreign_key_list("{quoted}")')}
        expected=set() if table=='sessions' else {('sessions','session_id','id','NO ACTION','NO ACTION','NONE')}
        if foreign!=expected:raise RuntimeError('Unsupported database schema foreign key: '+table)


def layout(version, positions=False):
    expected=dict(BASE)
    if version>=2:
        expected['sessions']+=' revision:INTEGER roster_revision:INTEGER'
        expected['actors']+=' agreed_at:REAL withdrawn_at:REAL'
        expected['invitations']=INVITATIONS
    if version>=3:expected['media']=MEDIA
    if version>=4:
        expected['actors']+=' control_seq:INTEGER'
        expected['control_requests']=CONTROLS
    if positions:expected['positions']=POSITIONS+(SIZE if version>=6 else '')
    return {table:dict(column.split(':') for column in columns.split()) for table,columns in expected.items()}


def validate_schema(conn):
    version=conn.execute('PRAGMA user_version').fetchone()[0]
    if version not in (0,1,2,3,4,5,6):
        raise RuntimeError('Unsupported database schema version.')
    tables={row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    if version==0:
        if tables:raise RuntimeError('Unsupported database schema layout: version 0 must be empty.')
        return
    if version==1:candidates=[layout(1)]
    elif version==2:candidates=[layout(1,True),layout(2),layout(2,True)]
    elif version in (3,4):candidates=[layout(version),layout(version,True)]
    elif version==5:candidates=[layout(4,True)]
    else:candidates=[layout(6,True)]
    actual={}
    for table in tables:
        quoted=table.replace('"','""')
        actual[table]={row[1]:row[2].upper() for row in conn.execute(f'PRAGMA table_info("{quoted}")')}
    if not any(actual==candidate and all(tuple(actual[t])==tuple(candidate[t]) for t in actual) for candidate in candidates):
        raise RuntimeError('Unsupported database schema layout for version %d; no migration was applied.'%version)
    validate_constraints(conn,tables)
