"""Small runtime signals, with no source content or provider exception text."""
from contextlib import contextmanager
import sqlite3
import threading
import time
from pathlib import Path


class RuntimeMonitor:
    """Progress of the two actual loops; HTTP requests cannot manufacture it."""
    def __init__(self, clock=time.monotonic):
        self.clock=clock
        self.lock=threading.Lock()
        self.limits={'worker':90.0,'maintenance':15.0}
        self.loops={name:{'started':None,'finished':None,'successful':False,
                         'busy':False,'failed':False,'stopped':False} for name in self.limits}

    def begin(self,name):
        with self.lock:
            if self.loops[name]['stopped']:self.loops[name]['successful']=False
            self.loops[name].update(started=self.clock(),busy=True,stopped=False)

    def succeeded(self,name):
        with self.lock:self.loops[name].update(finished=self.clock(),successful=True,busy=False,failed=False)

    def failed(self,name):
        with self.lock:self.loops[name].update(finished=self.clock(),busy=False,failed=True)

    def stopped(self,name):
        with self.lock:self.loops[name].update(stopped=True,busy=False)

    def snapshot(self):
        with self.lock:
            now=self.clock();result={}
            for name,state in self.loops.items():
                reference=state['started'] if state['busy'] else state['finished']
                age=None if reference is None else max(0.0,now-reference)
                if state['stopped']:status='stopped'
                elif state['failed']:status='failed'
                elif reference is None:status='not_started'
                elif age>self.limits[name]:status='stalled'
                elif not state['successful']:status='starting'
                else:status='busy' if state['busy'] else 'idle'
                result[name]={'status':status,'age_seconds':None if age is None else round(age,3),
                              'stall_after_seconds':self.limits[name]}
            return result


def _open_existing(path,mode,timeout=.1):
    # mode=rw/ro never creates a replacement for a deleted or unavailable store.
    return sqlite3.connect(Path(path).resolve().as_uri()+'?mode='+mode,
                           uri=True,timeout=timeout,isolation_level=None)


class StoreProbe:
    """A cached write-transaction probe, not a physical disk durability test."""
    def __init__(self,path,clock=time.monotonic):
        self.path=path;self.clock=clock;self.lock=threading.Lock()
        self.checked=None;self.cached=None

    def check(self):
        now=self.clock()
        if self.cached is not None and self.checked is not None and 0<=now-self.checked<1.0:
            return dict(self.cached)
        if not self.lock.acquire(blocking=False):return {'status':'checking'}
        try:
            # Recheck after acquiring the lock; concurrent probes need no extra work.
            now=self.clock()
            if self.cached is not None and self.checked is not None and 0<=now-self.checked<1.0:
                return dict(self.cached)
            connection=None
            try:
                connection=_open_existing(self.path,'rw')
                deadline=time.monotonic()+.25
                connection.set_progress_handler(lambda:time.monotonic()>deadline,1000)
                connection.execute('BEGIN IMMEDIATE')
                connection.execute('SELECT 1 FROM sessions LIMIT 1').fetchone()
                result={'status':'available'}
            except sqlite3.Error as error:
                code=getattr(error,'sqlite_errorcode',0)
                result={'status':'busy' if code&255 in (sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED) else 'unavailable'}
            except OSError:
                result={'status':'unavailable'}
            finally:
                if connection is not None:
                    try:connection.rollback()
                    except sqlite3.Error:result={'status':'unavailable'}
                    finally:
                        try:connection.close()
                        except sqlite3.Error:result={'status':'unavailable'}
            self.cached=result;self.checked=self.clock()
            return dict(result)
        finally:self.lock.release()


@contextmanager
def diagnostic_read(path):
    """One read-only snapshot with short SQLite lock and query budgets."""
    connection=_open_existing(path,'ro')
    try:
        connection.row_factory=sqlite3.Row
        connection.execute('PRAGMA query_only=ON')
        deadline=time.monotonic()+.25
        connection.set_progress_handler(lambda:time.monotonic()>deadline,1000)
        connection.execute('BEGIN')
        yield connection
    finally:
        try:connection.rollback()
        finally:connection.close()


SAFE_JOB_REASONS=frozenset(('interrupted_unknown_outcome','deadline_exceeded','capture_stopped',
    'user_cancelled','policy_changed','source_changed','permission_changed','adapter_changed',
    'adapter_failed','adapter_timeout','adapter_cancelled','record_capacity','storage_capacity'))


def session_metrics(connection,sid,now):
    """Only explicit numeric fields and generated job IDs leave this function."""
    counts={kind:0 for kind in ('source','proposal','item','job','export','other')}
    for row in connection.execute('SELECT kind,count(*) AS n FROM records WHERE session_id=? GROUP BY kind',(sid,)):
        counts[row['kind'] if row['kind'] in counts else 'other']+=row['n']
    states={state:0 for state in ('queued','running','succeeded','failed','cancelled','other')}
    for row in connection.execute("SELECT json_extract(data,'$.status') AS status,count(*) AS n FROM records WHERE session_id=? AND kind='job' GROUP BY status",(sid,)):
        states[row['status'] if row['status'] in states else 'other']+=row['n']
    oldest=connection.execute("SELECT min(json_extract(data,'$.created_at')) FROM records WHERE session_id=? AND kind='job' AND json_extract(data,'$.status')='queued'",(sid,)).fetchone()[0]
    predicate="session_id=? AND kind='job' AND json_extract(data,'$.status') IN ('failed','cancelled')"
    total=connection.execute('SELECT count(*) FROM records WHERE '+predicate,(sid,)).fetchone()[0]
    rows=connection.execute("SELECT id,json_extract(data,'$.status') AS status,json_extract(data,'$.error') AS reason,json_extract(data,'$.execution_outcome') AS outcome,json_extract(data,'$.usage_status') AS usage FROM records WHERE "+predicate+' ORDER BY rowid DESC LIMIT 20',(sid,)).fetchall()
    attention=[{'job_id':row['id'],'status':row['status'],
                'reason':row['reason'] if row['reason'] in SAFE_JOB_REASONS else 'unclassified_failure',
                'execution_outcome':row['outcome'] if row['outcome'] in ('completed','unknown') else 'unrecorded',
                'usage_status':row['usage'] if row['usage'] in ('reported','unknown') else 'unrecorded'} for row in rows]
    uncertain=connection.execute("SELECT count(*) FROM records WHERE "+predicate+" AND (json_extract(data,'$.execution_outcome')='unknown' OR json_extract(data,'$.error')='interrupted_unknown_outcome')",(sid,)).fetchone()[0]
    storage={}
    for table,column,label in (('records','data','record_json_bytes'),('versions','data','history_json_bytes'),
                                ('events','data','event_json_bytes'),('requests','result','request_json_bytes'),
                                ('control_requests','result','control_reply_json_bytes'),('media','payload','media_bytes')):
        storage[label]=connection.execute(f'SELECT coalesce(sum(length(CAST({column} AS BLOB))),0) FROM {table} WHERE session_id=?',(sid,)).fetchone()[0]
    return {'record_counts':counts,'jobs':{'counts':states,'oldest_queued_age_seconds':None if oldest is None else round(max(0.0,now-oldest),3),
            'uncertain_count':uncertain,'attention':attention,'attention_total':total,'attention_truncated':total>20},
            'storage':storage}
