"""Real readiness boundaries and private, read-only operational diagnostics."""
import http.client
import json
from pathlib import Path
import secrets
import shutil
import sqlite3
import threading
import time
import unittest
import os
import queue
import re
import subprocess
import sys

from genai_server.http import LocalServer
from genai_server.service import Service
from genai_server.runtime import RuntimeMonitor, StoreProbe


class RuntimeStatusTests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).resolve().parents[1]/'.local'/'runtime-status';root.mkdir(parents=True,exist_ok=True)
        self.directory=root/secrets.token_hex(16);self.directory.mkdir()
        self.addCleanup(shutil.rmtree,self.directory)
        self.path=self.directory/'state.sqlite3';self.service=Service(self.path)
        self.server=LocalServer(('127.0.0.1',0),self.service,origins=['http://localhost:5173'])
        self.thread=threading.Thread(target=self.server.serve_forever,kwargs={'poll_interval':.02},daemon=True);self.thread.start()
        self.addCleanup(self.stop)
        self.sid=secrets.token_hex(16);self.token=secrets.token_urlsafe(32)
        self.service.create_session({'session_id':self.sid,'owner_token':self.token,'owner_name':'PRIVATE OWNER','title':'PRIVATE TITLE'})

    def stop(self):
        self.server.shutdown();self.server.server_close();self.thread.join(2)

    def request(self,path,token=None,headers=None):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        h=dict(headers or {})
        if token:h['Authorization']='Bearer '+token
        try:
            c.request('GET',path,headers=h);response=c.getresponse();raw=response.read()
            return response.status,json.loads(raw)
        finally:c.close()

    def loops_ready(self):
        for name in ('worker','maintenance'):
            self.service.runtime.begin(name);self.service.runtime.succeeded(name)

    def test_liveness_remains_up_while_readiness_requires_first_success(self):
        self.assertEqual(200,self.request('/health')[0])
        self.assertEqual(503,self.request('/ready')[0])
        for name in ('worker','maintenance'):self.service.runtime.begin(name)
        self.assertEqual(503,self.request('/ready')[0])
        self.loops_ready();self.assertEqual((200,'ready'),(lambda x:(x[0],x[1]['status']))(self.request('/ready')))

    def test_failed_and_stopped_loops_are_not_ready(self):
        self.loops_ready();self.service.runtime.failed('worker')
        self.assertEqual(503,self.request('/ready')[0])
        self.service.runtime.succeeded('worker');self.assertEqual(200,self.request('/ready')[0])
        self.service.runtime.stopped('maintenance');self.assertEqual(503,self.request('/ready')[0])

    def test_loop_clock_stalls_and_begin_cannot_erase_failure(self):
        now=[100.0];self.service.runtime=RuntimeMonitor(clock=lambda:now[0])
        self.loops_ready();now[0]+=16
        self.assertEqual('stalled',self.service.runtime.snapshot()['maintenance']['status'])
        self.assertEqual(503,self.request('/ready')[0])
        self.service.runtime.succeeded('maintenance');now[0]+=75
        self.assertEqual('stalled',self.service.runtime.snapshot()['worker']['status'])
        self.loops_ready();self.service.runtime.failed('worker');self.service.runtime.begin('worker')
        self.assertEqual('failed',self.service.runtime.snapshot()['worker']['status'])
        self.assertEqual(503,self.request('/ready')[0])
        self.service.runtime.succeeded('worker');self.assertEqual(200,self.request('/ready')[0])
        self.service.runtime.stopped('worker');self.service.runtime.begin('worker')
        self.assertEqual('starting',self.service.runtime.snapshot()['worker']['status'])

    def test_store_probe_cache_expires_and_concurrent_probe_does_not_wait(self):
        now=[100.0];probe=StoreProbe(self.path,clock=lambda:now[0]);before=self.path.read_bytes()
        self.assertEqual('available',probe.check()['status']);self.assertEqual(before,self.path.read_bytes())
        self.path.rename(self.directory/'retained.sqlite3')
        now[0]+=.9;self.assertEqual('available',probe.check()['status'])
        now[0]+=.2;self.assertEqual('unavailable',probe.check()['status']);self.assertFalse(self.path.exists())
        now[0]+=2;probe.lock.acquire()
        try:
            started=time.monotonic();self.assertEqual('checking',probe.check()['status'])
            self.assertLess(time.monotonic()-started,.1)
        finally:probe.lock.release()

    def test_readiness_checks_host_origin_and_query(self):
        self.assertEqual(403,self.request('/ready',headers={'Host':'foreign.example'})[0])
        self.assertEqual(403,self.request('/ready',headers={'Origin':'https://foreign.example'})[0])
        self.assertEqual(400,self.request('/ready?anything=1')[0])

    def test_store_write_contention_is_bounded_and_not_ready(self):
        self.loops_ready();c=sqlite3.connect(self.path,isolation_level=None)
        try:
            c.execute('BEGIN IMMEDIATE');started=time.monotonic()
            status,_=self.request('/ready')
            self.assertEqual(503,status)
            self.assertLess(time.monotonic()-started,1,'readiness must not wait for the normal ten-second store timeout')
        finally:c.rollback();c.close()

    def test_pending_completion_and_maintenance_faults_keep_readiness_false(self):
        self.loops_ready();self.assertEqual(200,self.request('/ready')[0])
        self.service.pending_completions['PRIVATE JOB ID']=()
        status,result=self.request('/ready');self.assertEqual(503,status)
        self.assertNotIn('PRIVATE JOB ID',json.dumps(result))
        self.service.pending_completions.clear();self.assertEqual(200,self.request('/ready')[0])
        self.service.maintenance_failures['PRIVATE SESSION ID']='maintenance_retry_pending'
        status,result=self.request('/ready');self.assertEqual(503,status)
        self.assertNotIn('PRIVATE SESSION ID',json.dumps(result))
        self.service.maintenance_failures.clear();self.assertEqual(200,self.request('/ready')[0])

    def test_readiness_does_not_recreate_a_missing_store(self):
        self.loops_ready();moved=self.directory/'retained.sqlite3';self.path.rename(moved)
        self.assertEqual(503,self.request('/ready')[0]);self.assertFalse(self.path.exists())

    def test_diagnostics_requires_facilitator_and_never_writes(self):
        route='/api/sessions/'+self.sid+'/diagnostics'
        self.assertEqual(401,self.request(route)[0])
        before=self.path.read_bytes()
        status,result=self.request(route,self.token)
        self.assertEqual(200,status);self.assertEqual(before,self.path.read_bytes())
        encoded=json.dumps(result)
        for private in ('PRIVATE OWNER','PRIVATE TITLE',self.token,str(self.directory)):
            self.assertNotIn(private,encoded)

    def test_diagnostics_bounds_and_redacts_attention_and_aggregates(self):
        now=time.time();secret='PRIVATE SOURCE AND PROVIDER ERROR'
        with self.service.db.transaction() as c:
            for _ in range(25):self.service._new(c,self.sid,'job',{'status':'failed','created_at':now-50,'error':secret,'execution_outcome':secret,'usage_status':secret})
            self.service._new(c,self.sid,'job',{'status':'queued','created_at':now+100})
            self.service._new(c,self.sid,secret,{'text':secret})
        before=self.path.read_bytes();status,result=self.request('/api/sessions/'+self.sid+'/diagnostics',self.token)
        self.assertEqual(200,status);self.assertEqual(before,self.path.read_bytes())
        self.assertEqual(26,result['record_counts']['job']);self.assertEqual(1,result['record_counts']['other'])
        jobs=result['jobs'];self.assertEqual(25,jobs['attention_total']);self.assertTrue(jobs['attention_truncated'])
        self.assertEqual(20,len(jobs['attention']));self.assertEqual(0,jobs['oldest_queued_age_seconds'])
        self.assertEqual({'unclassified_failure'},{j['reason'] for j in jobs['attention']})
        self.assertNotIn(secret,json.dumps(result))
        self.assertGreater(result['storage']['record_json_bytes'],0)

    def test_real_cli_reaches_ready_after_actual_loop_success(self):
        root=Path(__file__).resolve().parents[1];data=self.directory/'cli'
        env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
        options={'creationflags':subprocess.CREATE_NO_WINDOW} if sys.platform=='win32' else {}
        process=subprocess.Popen([sys.executable,'-m','genai_server','--port','0','--data-dir',str(data)],cwd=root,env=env,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,stdin=subprocess.DEVNULL,text=True,**options)
        def stop():
            if process.poll() is None:process.kill()
            process.communicate(timeout=5)
        self.addCleanup(stop);lines=queue.Queue()
        threading.Thread(target=lambda:lines.put(process.stdout.readline()),daemon=True).start()
        line=lines.get(timeout=10);match=re.search(r'bound to 127\.0\.0\.1:(\d+)',line)
        self.assertIsNotNone(match,'CLI did not announce its bound port')
        deadline=time.monotonic()+5;status=None;result={}
        while time.monotonic()<deadline:
            c=http.client.HTTPConnection('127.0.0.1',int(match.group(1)),timeout=1)
            try:
                c.request('GET','/ready');response=c.getresponse();status=response.status;result=json.loads(response.read())
            finally:c.close()
            if status==200:break
            time.sleep(.02)
        self.assertEqual(200,status,result)
        self.assertEqual('ready',result['status'])

    def test_removed_facilitator_cannot_read_diagnostics(self):
        invitation=secrets.token_urlsafe(32);other=secrets.token_urlsafe(32)
        self.service.command(self.sid,self.token,secrets.token_hex(16),'participant.invite',{'invitation':invitation,'expected_roster_revision':1})
        joined=self.service.join(self.sid,{'invitation':invitation,'token':other,'name':'Private Guest','policy_version':1})
        route='/api/sessions/'+self.sid+'/diagnostics'
        self.assertEqual(403,self.request(route,other)[0])
        self.service.command(self.sid,self.token,secrets.token_hex(16),'participant.role',{'actor_id':joined['actor_id'],'role':'facilitator','expected_roster_revision':3})
        self.assertEqual(200,self.request(route,other)[0])
        snap=self.service.snapshot(self.sid,self.token)
        self.service.command(self.sid,self.token,secrets.token_hex(16),'participant.remove',{'actor_id':joined['actor_id'],'expected_roster_revision':snap['session']['roster_revision']},snap['next_control_sequence'])
        self.assertEqual(401,self.request(route,other)[0])

    def test_busy_pending_lock_is_explicit_and_does_not_hold_up_diagnostics(self):
        held=threading.Event();release=threading.Event()
        def hold():
            with self.service.pending_lock:
                held.set();release.wait(3)
        thread=threading.Thread(target=hold);thread.start()
        try:
            self.assertTrue(held.wait(1));self.loops_ready();started=time.monotonic()
            status,result=self.request('/api/sessions/'+self.sid+'/diagnostics',self.token)
            self.assertEqual(200,status);self.assertIsNone(result['pending_completions'])
            self.assertLess(time.monotonic()-started,.75)
            status,result=self.request('/ready')
            self.assertEqual(503,status);self.assertEqual('checking',result['checks']['completion_store']['status'])
        finally:release.set();thread.join(4)
