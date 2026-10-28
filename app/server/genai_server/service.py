"""Transactional domain logic. HTTP and model providers do not own state transitions."""
import base64
import hashlib
import json
import math
import re
import secrets
import sqlite3
import time
import threading
from copy import deepcopy
from .voice_commands import recognise_command, recognise_continuation, normalise_activation_phrase
from .polls import PollMixin
from .documents import DocumentMixin
from .calendar_dates import zone_name
from .summary_stickies import ideas_from_summary
from .summaries import SummaryMixin

from .adapters import ExtractionInput, FixtureExtractor, TranscriptionInput, FixtureTranscriber, TranscriptionFailure
from .adapters import FixtureSpeakerIdentifier, SpeakerIdentificationFailure, match_speaker, SPEAKER_MATCH_THRESHOLD
from .db import Database
from .media import sanitise, crop as crop_pixels
from .isolated import IsolatedFailure, IsolatedExtractor
from .wakeword import WakewordStreams
from .runtime import RuntimeMonitor, StoreProbe, diagnostic_read, session_metrics
from .validation import Problem, audio_payload, credential, fields, ident, image_payload, integer, regions, require, text


def encode(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def new_id():
    return secrets.token_hex(16)


class Service(SummaryMixin, DocumentMixin, PollMixin):
    MAX_JOBS=5
    MAX_INSTANCE_JOBS=32
    MAX_COORDINATE=100000
    # spec/canvas-layout.md: above 24 items in one form, "24 items in one hull is
    # a list that has been drawn badly". Past that it is not a form, so it is
    # refused. The 9-item threshold in the same section is where a hull stops
    # reading as a group and the model should sub-divide: that is guidance for
    # the layout engine, which is in the client, and the server does not enforce
    # it. Refusing a person's grouping of twelve would be the server arguing
    # with the person holding the pen, which the same spec rejects.
    MAX_CLUSTER_MEMBERS=24
    MAX_PLACEMENTS=60
    # The canvas object model, docs/specs/2026-10-18-canvas-object-model.md.
    # Five kinds a person can draw by hand or a model can propose. Each closed
    # set below is closed because the client draws exactly these and nothing
    # else: an unknown value would be stored and then silently not drawn.
    CANVAS_KINDS=('shape','text','arrow','section','stroke')
    # Kinds whose drawn box is a stored fact. A note's width follows its text,
    # so storing one for it would be a second answer; a rectangle has no text
    # to follow, so without a size there is nothing to draw.
    SIZED_KINDS=('shape','text','section')
    CANVAS_FIELDS={'shape':(('shape','tone'),('text',)),'text':(('text','size'),()),
                   'arrow':(('from','to','tone'),('label',)),'section':(('title','form','member_ids'),()),
                   'stroke':(('points','weight','tone'),())}
    # Tones are the ink, the one accent and the design system's three labelled
    # categories, never a status colour: a red shape must not read as an error.
    TONES=('ink','accent','category-1','category-2','category-3')
    SHAPES=('rect','ellipse','diamond','line')
    TEXT_SIZES=('body','title','heading')
    SECTION_FORMS=('free','cluster','timeline','matrix','flow')
    STROKE_WEIGHTS=('fine','regular','bold')
    # A section bigger than the largest move is one nobody can drag as a whole,
    # so it shares item.place's limit of 60.
    MAX_SECTION_MEMBERS=60
    # 256 points is a hand-drawn line of a few seconds after the client thins
    # it; more is a recording, and every point is stored in every revision.
    MAX_STROKE_POINTS=256
    # Points are relative to the stroke's position. A pen line wider than
    # 10000 either way is not a gesture anyone made, and the bound keeps every
    # absolute point inside the board's own coordinate limit plus this margin.
    MAX_STROKE_OFFSET=10000
    # Smaller than 8 cannot be grabbed; larger than 4000 is several screens,
    # which is a section that should have been two.
    MIN_SIZE=8
    MAX_SIZE=4000
    MAX_RECORDS=1000
    MAX_REQUESTS=10000
    MAX_IMAGE_BYTES=20*1024*1024
    MAX_SESSION_BYTES=64*1024*1024
    # One chunk is <=12s of 16kHz mono PCM16 (~384000 bytes); 400 chunks is
    # roughly 45 minutes of continuous speech, comfortably over a working
    # meeting, bounded so one session cannot grow the transcript unboundedly.
    MAX_AUDIO_CHUNKS=400
    CONTROL_COMMANDS={'session.pause','session.close','session.heartbeat','participant.remove','consent.withdraw','invitation.revoke'}
    CONTROL_REPLAY_WINDOW=128

    def __init__(self,path,extractor=None,clock=time.time,transcriber=None,speaker_identifier=None,
                 speaker_match_threshold=SPEAKER_MATCH_THRESHOLD,wakeword_factory=None,
                 wakeword_clock=time.monotonic,wakeword_threshold=0.5,poll_model=None,poll_notice='',
                 document_model=None,document_notice='',automatic_workspace=False,summary_model=None):
        self.db=Database(path)
        self.automatic_workspace=automatic_workspace
        self.extractor=extractor or FixtureExtractor()
        self.transcriber=transcriber or FixtureTranscriber()
        # F1.3 opt-in voice-ID path. Default is the fixture (same role as
        # FixtureTranscriber): no profile ever matches it, so a session with
        # no real identifier configured behaves exactly as it did before
        # this feature existed, whether or not someone enrols. See
        # decisions/decision-log.md.
        self.speaker_identifier=speaker_identifier or FixtureSpeakerIdentifier()
        self.speaker_match_threshold=speaker_match_threshold
        self.wakewords=WakewordStreams(wakeword_factory,wakeword_clock,wakeword_threshold)
        self.clock=clock
        self.runtime=RuntimeMonitor()
        self.store_probe=StoreProbe(self.db.path)
        self.pending_completions={}
        self.pending_lock=threading.RLock()
        # Moving transcription outside db.transaction() (see
        # _transcribe_before_lock) let concurrent chunks run in parallel,
        # which sounds like the fix but is not: a real ASR model is
        # CPU-bound, and several concurrent transcribe() calls on one
        # machine fight each other for the same cores, which is slower
        # overall than one at a time and, on a model that is not documented
        # thread-safe for concurrent calls on one instance, showed up as
        # sporadic transcription failures and timed-out HTTP requests on a
        # real user's laptop. This lock serialises transcription only, so
        # it never holds up an unrelated command the way the write-lock did.
        self.transcription_lock=threading.Lock()
        # Carry the groupmate's latest laptop fix into this combined build:
        # ASR and speaker embedding share the CPU model lock. Neither model
        # holds the database transaction or blocks unrelated UI commands.
        self.speaker_lock=self.transcription_lock
        self.executions={}
        self.maintenance_failures={}
        self.last_claim_session=None
        self.handlers={
            'participant.invite':self._invite,'participant.role':self._role,'participant.remove':self._remove,
            'invitation.revoke':self._invitation_revoke,'consent.withdraw':self._withdraw,
            'consent.acknowledge':self._consent,'session.activate':self._activate,
            'session.pause':self._pause,'session.close':self._close,'session.heartbeat':self._heartbeat,
            'source.text':self._source_text,'source.image':self._source_image,'source.audio':self._source_audio,
            'summary.to_stickies':self._summary_to_stickies,
            'source.correct':self._source_correct,'source.regions':self._source_regions,
            'speaker.enroll':self._speaker_enroll,
            'extraction.queue':self._queue,'job.cancel':self._cancel,
            'item.place':self._place,'cluster.membership':self._cluster_membership,
            'canvas.create':self._canvas_create,'canvas.update':self._canvas_update,'canvas.remove':self._canvas_remove,
            'proposal.create':self._proposal_create,'proposal.edit':self._proposal_edit,
            'proposal.review':self._review,'item.edit':self._item_edit,'item.undo':self._undo,
            'export.create':self._export,
        }
        self._init_summaries(summary_model)
        self._init_polls(poll_model,poll_notice)
        self._init_documents(document_model,document_notice)
        if self.automatic_workspace:self._apply_waiting_inputs()

    def _wakeword_authority(self,sid,token):
        with self.db.transaction() as c:
            s,a=self._auth(c,sid,token)
            self._facilitator(a)
            self._active(s)
            require(a['consent_version']==s['policy_version'],'agreement_incomplete','Acknowledge current policy before detection.',409)
            return (a['id'],s['policy_version'],s['revision'])

    def wakeword(self,sid,token,action,body):
        if action=='stop':
            fields(body,('stream_id',))
            with self.db.transaction() as c:
                _,actor=self._auth(c,sid,token)
            return self.wakewords.stop(sid,actor['id'],body['stream_id'])
        authority=self._wakeword_authority(sid,token)
        authorize=lambda:self._wakeword_authority(sid,token)
        if action=='start':
            fields(body)
            return self.wakewords.start(sid,authority,authorize)
        return self.wakewords.batch(sid,authority,body,authorize)

    def readiness(self):
        loops=self.runtime.snapshot();store=self.store_probe.check()
        completion='checking'
        if self.pending_lock.acquire(timeout=.05):
            try:completion='pending' if self.pending_completions else 'clear'
            finally:self.pending_lock.release()
        cleanup='pending' if self.maintenance_failures else 'clear'
        ready=(store['status']=='available' and all(loop['status'] in ('idle','busy') for loop in loops.values())
               and completion=='clear' and cleanup=='clear')
        return {'status':'ready' if ready else 'not_ready','checks':{'store':store,**loops,
                'completion_store':{'status':completion},'maintenance_cleanup':{'status':cleanup}}}

    def diagnostics(self,sid,token):
        try:
            with diagnostic_read(self.db.path) as c:
                session,actor=self._auth(c,sid,token)
                self._facilitator(actor)
                result=session_metrics(c,sid,self.clock())
                result['session']={'state':session['state'],'snapshot_seq':session['seq'],
                    'expires_in_seconds':round(max(0.0,session['expires']-self.clock()),3)}
        except sqlite3.Error:
            raise Problem(503,'diagnostics_unavailable','Session diagnostics are temporarily unavailable.') from None
        # Do not invert the worker's pending-lock/database acquisition order.
        result['pending_completions']=None
        if self.pending_lock.acquire(timeout=.05):
            try:result['pending_completions']=sum(args[0]['id']==sid for args in self.pending_completions.values())
            finally:self.pending_lock.release()
        result['runtime']=self.runtime.snapshot()
        return result

    def create_session(self,body):
        fields(body,('session_id','owner_token','owner_name','title'),('retention_seconds','timezone'))
        sid=ident(body['session_id']);token=credential(body['owner_token'])
        title=text(body['title'],'title',200);name=text(body['owner_name'],'owner_name',100)
        retention=integer(body.get('retention_seconds',86400),'retention_seconds',60,7*86400)
        zone=zone_name(body.get('timezone','UTC'))
        self.sweep()
        with self.db.transaction() as c:
            old=c.execute('SELECT * FROM sessions WHERE id=?',(sid,)).fetchone()
            if old:
                actor=c.execute('SELECT * FROM actors WHERE session_id=? AND token_hash=?',(sid,digest(token))).fetchone()
                require(actor is not None and old['state']!='deleted','session_exists','Session ID is already in use.',409)
                require(old['title']==title and actor['name']==name and old['expires']-old['created']==retention and self._session_timezone(c,sid)==zone,
                        'idempotency_conflict','Session ID was reused with different creation fields.',409)
                return {'session_id':sid,'actor_id':actor['id'],'state':old['state'],'replayed':True}
            require(c.execute("SELECT count(*) FROM sessions WHERE state!='deleted'").fetchone()[0]<100,
                    'session_capacity','Local instance has reached its active-session limit.',429)
            now=self.clock();aid=new_id()
            require(c.execute('SELECT 1 FROM actors WHERE token_hash=?',(digest(token),)).fetchone() is None,
                    'credential_reused','Use a new credential for each actor.',409)
            c.execute('INSERT INTO sessions(id,title,state,policy_version,seq,created,expires,lease) VALUES(?,?,?,?,?,?,?,?)',(sid,title,'draft',1,0,now,now+retention,now+300))
            c.execute('INSERT INTO actors(id,session_id,name,role,token_hash,consent_version) VALUES(?,?,?,?,?,0)',(aid,sid,name,'facilitator',digest(token)))
            if 'timezone' in body:
                self._new(c,sid,'session_clock',{'timezone':zone})
            if self.poll_model is not None:
                self._new(c,sid,'poll_policy',{'cloud_text':True})
            if self.document_model is not None:
                self._new(c,sid,'command_policy',{'whole_meeting_text':True,'types':['todo','requirements','calendar']})
            if self.summary_model is not None:self._new(c,sid,'summary_policy',{'cloud_text':not getattr(self.summary_model,'local',True)})
            self._event(c,sid,aid,'session.created',{})
            return {'session_id':sid,'actor_id':aid,'state':'draft','replayed':False}

    def _auth(self,c,sid,token,deleted=False):
        ident(sid)
        require(type(token) is str and token,'unauthorized','A bearer credential is required.',401)
        s=c.execute('SELECT * FROM sessions WHERE id=?',(sid,)).fetchone()
        a=c.execute('SELECT * FROM actors WHERE session_id=? AND token_hash=?',(sid,digest(token))).fetchone()
        if s and s['state']=='deleted' and deleted and secrets.compare_digest(s['deletion_hash'] or '',digest(token)):
            return dict(s),{'id':'deleted','role':'facilitator'}
        require(s is not None and a is not None,'unauthorized','Invalid credential or session.',401)
        require(s['state']!='deleted','session_deleted','Session content is unavailable.',410)
        require(s['expires']>self.clock(),'session_expired','Session retention has expired.',410)
        return dict(s),dict(a)

    @staticmethod
    def _facilitator(a):
        require(a['role']=='facilitator','forbidden','A facilitator must perform this action.',403)

    @staticmethod
    def _editor(a):
        require(a['role'] in ('facilitator','participant'),'forbidden','Viewer access is read-only.',403)

    def _active(self,s):
        require(s['state']=='active','capture_inactive','Activate the session with current agreement before adding or processing sources.',409)
        require(s['lease']>self.clock(),'lease_expired','Capture lease expired; renew and explicitly activate.',409)

    def _event(self,c,sid,actor,kind,data):
        c.execute('UPDATE sessions SET seq=seq+1 WHERE id=?',(sid,))
        row=c.execute('SELECT seq,state,policy_version FROM sessions WHERE id=?',(sid,)).fetchone()
        seq=row['seq']
        # Everything written since the previous event on this transaction, so a
        # client can refetch exactly those records instead of the whole session.
        # Consumed here: a second event in the same transaction reports its own
        # writes, not the first one's again.
        changed=getattr(c,'changed',None) or {}
        # State and policy version ride along on every event so the stream is
        # self-sufficient: a client that missed a pause must not need a snapshot
        # to find out it has to re-acknowledge. Costs about 38 bytes an event,
        # which is the most compressible thing in the payload.
        payload={**data,'state':row['state'],'policy_version':row['policy_version'],
                 'records':sorted(changed.values(),key=lambda r:(r['id'],r['kind']))}
        if getattr(c,'changed',None) is not None:c.changed={}
        c.execute('INSERT INTO events VALUES(?,?,?,?,?,?)',(sid,seq,kind,actor,self.clock(),encode(payload)))
        return seq

    def _get(self,c,sid,rid,kind=None):
        ident(rid)
        row=c.execute('SELECT * FROM records WHERE session_id=? AND id=?',(sid,rid)).fetchone()
        require(row is not None and (kind is None or row['kind']==kind),'not_found','Record not found in this session.',404)
        return {'id':row['id'],'kind':row['kind'],'revision':row['revision'],'data':json.loads(row['data'])}

    def _list(self,c,sid,kind=None):
        rows=c.execute('SELECT * FROM records WHERE session_id=?'+(' AND kind=?' if kind else '')+' ORDER BY rowid',
                       (sid,kind) if kind else (sid,)).fetchall()
        return [{'id':r['id'],'kind':r['kind'],'revision':r['revision'],'data':json.loads(r['data'])} for r in rows]

    def _new(self,c,sid,kind,data):
        require(c.execute('SELECT count(*) FROM records WHERE session_id=?',(sid,)).fetchone()[0]<self.MAX_RECORDS,
                'record_capacity','Session record limit reached.',429)
        record={'id':new_id(),'kind':kind,'revision':1,'data':data}
        c.execute('INSERT INTO records VALUES(?,?,?,?,?)',(record['id'],sid,kind,1,encode(data)))
        c.execute('INSERT INTO versions VALUES(?,?,?,?)',(sid,record['id'],1,encode(data)))
        return self._track(c,record)

    def _save(self,c,sid,r,data):
        rev=r['revision']+1
        c.execute('UPDATE records SET revision=?,data=? WHERE id=? AND session_id=?',(rev,encode(data),r['id'],sid))
        c.execute('INSERT INTO versions VALUES(?,?,?,?)',(sid,r['id'],rev,encode(data)))
        return self._track(c,{'id':r['id'],'kind':r['kind'],'revision':rev,'data':data})

    @staticmethod
    def _track(c,record,kind=None):
        """Note a write so the command's event can name it.

        Every write passes through here, so no handler can forget to declare
        what it changed. That was the whole failure: the event was built from
        the handler's return value, and a cascade or a roster change returns
        nothing that names the records it touched.
        """
        if getattr(c,'changed',None) is not None:
            what=kind or record['kind']
            c.changed[(record['id'],what)]={'id':record['id'],'kind':what,'revision':record['revision']}
        return record

    @staticmethod
    def _expected(record,expected):
        integer(expected,'expected_revision')
        require(record['revision']==expected,'stale_revision','The record changed. Fetch the current revision and review again.',409,
                record_id=record['id'],current_revision=record['revision'])

    def _refs(self,c,sid,refs):
        require(type(refs) is list and 1<=len(refs)<=60,'invalid_references','Supply 1–60 source/item references.')
        seen=set()
        for ref in refs:
            fields(ref,('id','revision'))
            record=self._get(c,sid,ref['id'])
            require(record['kind'] in ('source','item'),'invalid_reference','Only sources and accepted items can be referenced.')
            self._expected(record,ref['revision'])
            require(record['id'] not in seen,'duplicate_reference','Reference IDs must be unique.')
            seen.add(record['id'])
            require(record['data'].get('status') not in ('stale','undone','superseded'),'stale_reference','Referenced item requires review or was undone.',409)
        return refs

    def command(self,sid,token,request_id,operation,body,control_sequence=None):
        ident(request_id)
        require(type(operation) is str and operation in self.handlers,'unknown_operation','Unknown operation.',404)
        fields(body,(),tuple(body.keys()) if type(body) is dict else ())
        control=operation in self.CONTROL_COMMANDS
        if control:integer(control_sequence,'control_sequence',1,2**53-1)
        else:require(control_sequence is None,'invalid_control_sequence','This command does not use a control sequence.')
        fingerprint=digest(encode({'operation':operation,'body':body,**({'control_sequence':control_sequence} if control else {})}))
        precomputed_audio=self._transcribe_before_lock(sid,token,request_id,body) if operation=='source.audio' else None
        precomputed_enrollment=self._enroll_before_lock(sid,token,request_id,body) if operation=='speaker.enroll' else None
        self.sweep()
        with self.db.transaction() as c:
            s,a=self._auth(c,sid,token)
            if operation in ('participant.invite','participant.role','participant.remove','invitation.revoke','session.activate','session.close','session.heartbeat',
                             'proposal.review','item.edit','item.undo','export.create'):
                self._facilitator(a)
            elif operation not in ('session.pause','consent.acknowledge','consent.withdraw'):
                self._editor(a)
            table='control_requests' if control else 'requests'
            old=c.execute(f'SELECT * FROM {table} WHERE session_id=? AND actor_id=? AND request_id=?',(sid,a['id'],request_id)).fetchone()
            if old:
                require(old['fingerprint']==fingerprint,'idempotency_conflict','Request ID was reused with different operation or payload.',409)
                return {**json.loads(old['result']),'replayed':True}
            if control:
                require(control_sequence>a['control_seq']-self.CONTROL_REPLAY_WINDOW,'control_replay_expired',
                        'This control result is no longer retained. Refresh; its earlier outcome may have committed.',409,
                        next_control_sequence=a['control_seq']+1)
                require(control_sequence==a['control_seq']+1,'control_sequence_conflict','Refresh before allocating another control intent.',409,
                        next_control_sequence=a['control_seq']+1)
            if operation!='export.create':
                require(s['state']!='closed','session_closed','Closed sessions are read-only; export or delete remains available.',409)
            if operation not in self.CONTROL_COMMANDS:
                require(c.execute('SELECT count(*) FROM requests WHERE session_id=?',(sid,)).fetchone()[0]<self.MAX_REQUESTS,
                        'request_capacity','Session command limit reached.',429)
            if operation=='source.audio':result=self._source_audio(c,s,a,body,precomputed_audio)
            elif operation=='speaker.enroll':result=self._speaker_enroll(c,s,a,body,precomputed_enrollment)
            else:result=self.handlers[operation](c,s,a,body)
            noop=result.pop('_noop',False)
            seq=s['seq'] if noop or operation=='session.heartbeat' else self._event(c,sid,a['id'],operation,{})
            result={'result':result,'seq':seq,'replayed':False}
            if control:
                result['next_control_sequence']=control_sequence+1
                require(len(encode(result).encode())<=2048,'control_result_too_large','Control response exceeded its reserved size.',500)
                c.execute('UPDATE actors SET control_seq=? WHERE id=?',(control_sequence,a['id']))
                c.execute('INSERT INTO control_requests VALUES(?,?,?,?,?,?)',(sid,a['id'],request_id,control_sequence,fingerprint,encode(result)))
                c.execute('DELETE FROM control_requests WHERE session_id=? AND actor_id=? AND sequence<=?',
                          (sid,a['id'],control_sequence-self.CONTROL_REPLAY_WINDOW))
            else:c.execute('INSERT INTO requests VALUES(?,?,?,?,?)',(sid,a['id'],request_id,fingerprint,encode(result)))
            if operation not in self.CONTROL_COMMANDS:self._budget(c,sid)
        if operation in ('session.pause','session.close','consent.withdraw'):
            self._cancel_executions(sid)
        elif operation=='participant.remove' or (operation=='participant.role' and body['role']=='viewer'):
            self._cancel_executions(sid,author=body['actor_id'])
        elif operation=='job.cancel':self._cancel_executions(sid,jid=body['job_id'])
        return result

    def _cancel_executions(self,sid,author=None,jid=None):
        with self.pending_lock:
            for job_id,ticket in self.executions.items():
                if ticket['sid']==sid and (author is None or ticket['author_id']==author) and (jid is None or job_id==jid):
                    ticket['cancel_event'].set()

    def _budget(self,c,sid):
        total=c.execute('SELECT coalesce(sum(length(payload)),0) FROM media WHERE session_id=?',(sid,)).fetchone()[0]
        for table,column in (('records','data'),('versions','data'),('events','data'),('requests','result'),('positions','record_id')):
            total+=c.execute(f'SELECT coalesce(sum(length(CAST({column} AS BLOB))),0) FROM {table} WHERE session_id=?',(sid,)).fetchone()[0]
        require(total<=self.MAX_SESSION_BYTES,'storage_capacity','Session content/history budget reached. Export or delete; no partial change was saved.',429)

    @staticmethod
    def _result_ids(value):
        return [value['id']] if isinstance(value,dict) and 'id' in value else []

    def _invalidate(self,c,sid,changed):
        queue=[changed];seen={changed};affected=[]
        while queue:
            current=queue.pop(0)
            for record in self._list(c,sid):
                if record['id'] in seen or record['kind'] not in ('proposal','item','job'):continue
                d=record['data']
                if not any(ref['id']==current for ref in d.get('refs',[])):continue
                seen.add(record['id'])
                if record['kind']=='job':
                    if d['status'] not in ('queued','running'):continue
                    d['status']='cancelled';d['error']='source_changed'
                elif record['kind']=='proposal':
                    if d['status'] in ('accepted','rejected'):continue
                    d['status']='stale'
                else:
                    if d['status']=='undone':continue
                    d['status']='stale'
                self._save(c,sid,record,d);affected.append(record['id']);queue.append(record['id'])
        return affected

    def _invite(self,c,s,a,b):
        fields(b,('invitation','expected_roster_revision'),('role','expires_seconds'));self._facilitator(a)
        self._roster_expected(s,b['expected_roster_revision'])
        capability=credential(b['invitation']);role=b.get('role','participant')
        require(role in ('participant','viewer'),'invalid_role','Invite a participant or viewer.')
        duration=integer(b.get('expires_seconds',600),'expires_seconds',60,3600)
        require(c.execute('SELECT count(*) FROM invitations WHERE session_id=?',(s['id'],)).fetchone()[0]<128,
                'invitation_capacity','Invitation limit reached.',429)
        require(c.execute('SELECT 1 FROM invitations WHERE capability_hash=?',(digest(capability),)).fetchone() is None,
                'invitation_reused','Generate a new invitation capability.',409)
        iid=new_id();expires=min(s['expires'],self.clock()+duration)
        c.execute('INSERT INTO invitations(id,session_id,capability_hash,role,expires) VALUES(?,?,?,?,?)',
                  (iid,s['id'],digest(capability),role,expires))
        c.execute('UPDATE sessions SET roster_revision=roster_revision+1 WHERE id=?',(s['id'],))
        return {'invitation_id':iid,'role':role,'expires':expires,'policy_version':s['policy_version'],
                'roster_revision':s['roster_revision']+1}

    @staticmethod
    def _roster_expected(s,revision):
        integer(revision,'expected_roster_revision')
        require(revision==s['roster_revision'],'stale_roster','Refresh the roster before changing membership.',409,
                current_roster_revision=s['roster_revision'])

    def join(self,sid,body):
        fields(body,('invitation','token','name','policy_version'))
        ident(sid);capability=credential(body['invitation']);token=credential(body['token'])
        name=text(body['name'],'name',100);integer(body['policy_version'],'policy_version')
        intent=digest(encode(body));self.sweep()
        with self.db.transaction() as c:
            row=c.execute('SELECT * FROM sessions WHERE id=?',(sid,)).fetchone()
            invite=c.execute('SELECT * FROM invitations WHERE session_id=? AND capability_hash=?',(sid,digest(capability))).fetchone()
            require(row is not None and invite is not None,'invalid_invitation','Invitation is unavailable.',401)
            s=dict(row)
            require(s['state'] not in ('closed','deleted') and s['expires']>self.clock(),'session_closed','Session is not accepting members.',409)
            if invite['actor_id']:
                require(secrets.compare_digest(invite['credential_hash'],digest(token)),
                        'invitation_consumed','Invitation was already consumed.',409)
                require(secrets.compare_digest(invite['intent_hash'],intent),'idempotency_conflict','Join payload changed.',409)
                require(c.execute('SELECT 1 FROM actors WHERE id=? AND session_id=?',(invite['actor_id'],sid)).fetchone() is not None,
                        'membership_removed','This membership was removed.',401)
                return {'actor_id':invite['actor_id'],'session_id':sid,'replayed':True}
            require(not invite['revoked'],'invitation_revoked','Invitation was revoked.',409)
            require(invite['expires']>self.clock(),'invitation_expired','Invitation expired.',409)
            require(body['policy_version']==s['policy_version'],'policy_changed','Read the current policy before joining.',409)
            require(c.execute('SELECT count(*) FROM actors WHERE session_id=?',(sid,)).fetchone()[0]<8,'participant_capacity','Prototype supports at most eight members.',429)
            require(c.execute('SELECT 1 FROM actors WHERE token_hash=?',(digest(token),)).fetchone() is None,'credential_reused','Use a new credential.',409)
            aid=new_id()
            c.execute('INSERT INTO actors(id,session_id,name,role,token_hash,consent_version,agreed_at) VALUES(?,?,?,?,?,?,?)',
                      (aid,sid,name,invite['role'],digest(token),s['policy_version'],self.clock()))
            c.execute('UPDATE invitations SET actor_id=?,credential_hash=?,intent_hash=? WHERE id=?',
                      (aid,digest(token),intent,invite['id']))
            c.execute('UPDATE sessions SET roster_revision=roster_revision+1 WHERE id=?',(sid,))
            self._event(c,sid,aid,'participant.joined',{'actor_id':aid,'roster_revision':s['roster_revision']+1})
            self._budget(c,sid)
            return {'actor_id':aid,'session_id':sid,'replayed':False}

    def _invitation_revoke(self,c,s,a,b):
        fields(b,('invitation_id','expected_roster_revision'));self._roster_expected(s,b['expected_roster_revision'])
        iid=ident(b['invitation_id'])
        invite=c.execute('SELECT * FROM invitations WHERE session_id=? AND id=?',(s['id'],iid)).fetchone()
        require(invite is not None,'not_found','Invitation not found.',404)
        require(invite['actor_id'] is None,'invitation_consumed','Remove the admitted member instead.',409)
        if invite['revoked']:return {'invitation_id':iid,'revoked':True,'_noop':True}
        c.execute('UPDATE invitations SET revoked=1 WHERE id=?',(iid,))
        c.execute('UPDATE sessions SET roster_revision=roster_revision+1 WHERE id=?',(s['id'],))
        return {'invitation_id':iid,'revoked':True,'roster_revision':s['roster_revision']+1}

    def _remove(self,c,s,a,b):
        fields(b,('actor_id','expected_roster_revision'));self._roster_expected(s,b['expected_roster_revision'])
        aid=ident(b['actor_id'])
        other=c.execute('SELECT * FROM actors WHERE session_id=? AND id=?',(s['id'],aid)).fetchone()
        require(other is not None,'not_found','Participant not found.',404)
        if other['role']=='facilitator':
            require(c.execute("SELECT count(*) FROM actors WHERE session_id=? AND role='facilitator'",(s['id'],)).fetchone()[0]>1,
                    'last_facilitator','Promote a replacement before removing the last facilitator.',409)
        c.execute('DELETE FROM actors WHERE id=?',(aid,))
        c.execute('DELETE FROM control_requests WHERE session_id=? AND actor_id=?',(s['id'],aid))
        c.execute('UPDATE sessions SET roster_revision=roster_revision+1 WHERE id=?',(s['id'],))
        self._cancel_capture(c,s,author=aid)
        return {'actor_id':aid,'removed':True,'roster_revision':s['roster_revision']+1}

    def _cancel_capture(self,c,s,author=None):
        self.wakewords.invalidate(s['id'],author)
        for r in self._list(c,s['id'],'job'):
            if r['data']['status'] in ('queued','running') and (author is None or r['data']['author_id']==author):
                d=r['data'];d.update(status='cancelled',error='capture_stopped');self._save(c,s['id'],r,d)

    def _stop_capture(self,c,s,state='paused'):
        if s['state']==state:return {'state':state,'policy_version':s['policy_version'],'revision':s['revision'],'_noop':True}
        c.execute('UPDATE sessions SET state=?,revision=revision+1 WHERE id=?',(state,s['id']))
        self._cancel_capture(c,s)
        return {'state':state,'policy_version':s['policy_version'],'revision':s['revision']+1}

    def _withdraw(self,c,s,a,b):
        fields(b)
        if a['consent_version']==0 and a['withdrawn_at'] is not None:
            return {'actor_id':a['id'],'withdrawn_at':a['withdrawn_at'],'_noop':True}
        c.execute('UPDATE actors SET consent_version=0,withdrawn_at=? WHERE id=?',(self.clock(),a['id']))
        result=self._stop_capture(c,s)
        result.pop('_noop',None)
        return {'actor_id':a['id'],'withdrawn_at':self.clock(),**result}

    def _role(self,c,s,a,b):
        fields(b,('actor_id','role','expected_roster_revision'));self._facilitator(a);ident(b['actor_id'])
        self._roster_expected(s,b['expected_roster_revision'])
        require(b['role'] in ('participant','viewer','facilitator'),'invalid_role','Unknown role.')
        other=c.execute('SELECT * FROM actors WHERE session_id=? AND id=?',(s['id'],b['actor_id'])).fetchone()
        require(other is not None,'not_found','Participant not found.',404)
        if other['role']=='facilitator' and b['role']!='facilitator':
            require(c.execute("SELECT count(*) FROM actors WHERE session_id=? AND role='facilitator'",(s['id'],)).fetchone()[0]>1,
                    'last_facilitator','Promote a replacement before demoting the last facilitator.',409)
        if other['role']==b['role']:return {'actor_id':other['id'],'role':b['role'],'_noop':True}
        self.wakewords.invalidate(s['id'],other['id'])
        c.execute('UPDATE actors SET role=? WHERE id=?',(b['role'],other['id']))
        c.execute('UPDATE sessions SET roster_revision=roster_revision+1 WHERE id=?',(s['id'],))
        if b['role']=='viewer':self._cancel_capture(c,s,author=other['id'])
        return {'actor_id':other['id'],'role':b['role'],'roster_revision':s['roster_revision']+1}

    def _consent(self,c,s,a,b):
        fields(b,('policy_version',));integer(b['policy_version'],'policy_version')
        require(b['policy_version']==s['policy_version'],'policy_changed','Read and acknowledge the current policy version.',409,current_policy_version=s['policy_version'])
        if a['consent_version']==s['policy_version'] and a['agreed_at'] is not None:
            return {'actor_id':a['id'],'policy_version':s['policy_version'],'acknowledged':True,'agreed_at':a['agreed_at'],'_noop':True}
        c.execute('UPDATE actors SET consent_version=?,agreed_at=? WHERE id=?',(s['policy_version'],self.clock(),a['id']))
        return {'actor_id':a['id'],'policy_version':s['policy_version'],'acknowledged':True,'agreed_at':self.clock()}

    def _activate(self,c,s,a,b):
        fields(b,('policy_version','expected_session_revision'));self._facilitator(a)
        integer(b['expected_session_revision'],'expected_session_revision')
        require(b['expected_session_revision']==s['revision'],'stale_activation','Refresh the capture state before activation.',409)
        require(type(b['policy_version']) is int and b['policy_version']==s['policy_version'],'policy_changed','Current policy version is required.',409)
        missing=c.execute('SELECT id FROM actors WHERE session_id=? AND consent_version!=?',(s['id'],s['policy_version'])).fetchall()
        require(not missing,'agreement_incomplete','Every current member must acknowledge before activation.',409,actor_ids=[r['id'] for r in missing])
        if s['state']=='active':
            self._active(s)
            return {'state':'active','policy_version':s['policy_version'],'revision':s['revision'],'_noop':True}
        c.execute("UPDATE sessions SET state='active',lease=?,revision=revision+1 WHERE id=?",(self.clock()+300,s['id']))
        return {'state':'active','policy_version':s['policy_version'],'revision':s['revision']+1}

    def _pause(self,c,s,a,b):
        fields(b);return self._stop_capture(c,s)

    def _close(self,c,s,a,b):
        fields(b,('expected_session_revision',));self._facilitator(a)
        integer(b['expected_session_revision'],'expected_session_revision')
        require(b['expected_session_revision']==s['revision'],'stale_session','Refresh before closing this session.',409)
        return self._stop_capture(c,s,'closed')

    def _heartbeat(self,c,s,a,b):
        fields(b);self._facilitator(a)
        require(s['state']!='active' or s['lease']>self.clock(),'lease_expired','Wait for capture to pause before renewing an expired lease.',409)
        if self.clock()+300-s['lease']>=10:
            c.execute('UPDATE sessions SET lease=? WHERE id=?',(self.clock()+300,s['id']))
        return {'lease_seconds':300}

    def _proposal(self,c,s,a,kind,body,refs,origin='human',extra=None):
        data={'proposal_kind':kind,'text':body,'refs':deepcopy(refs),'origin':origin,'author_id':a['id'],
              'status':'needs_review','policy_version':s['policy_version'],'created_at':self.clock(),**(extra or {})}
        proposal=self._new(c,s['id'],'proposal',data)
        if self.automatic_workspace and kind in ('content','relationship'):
            proposal=self._apply_input(c,s,a,proposal)
        return proposal

    def _apply_input(self,c,s,a,proposal):
        d=proposal['data']
        item_data={'item_kind':d['proposal_kind'],'text':d['text'] or 'Unreadable note',
            'refs':deepcopy(d['refs']),'origin':d['origin'],'status':'accepted','proposal_id':proposal['id'],
            'automatic':True,'applied_by':'system','author_id':a['id'],'created_at':self.clock()}
        for key in ('form','region_id','reading_status','provider','model','synthetic','confidence','colour',
                    'summary_title','summary_detail','summary_category','summary_importance','summary_batch_id','summary_order','summary_topic_id'):
            if key in d:item_data[key]=deepcopy(d[key])
        item=self._new(c,s['id'],'item',item_data)
        self._carry_position(c,s,a,proposal,item)
        return self._save(c,s['id'],proposal,{**d,'status':'accepted','automatic':True,'item_id':item['id']})

    def _apply_waiting_inputs(self):
        """Existing valid readings join automatic mode once, without re-running AI."""
        with self.db.transaction() as c:
            for row in c.execute("SELECT * FROM sessions WHERE state NOT IN ('deleted','closed')").fetchall():
                s=dict(row)
                for proposal in self._list(c,s['id'],'proposal'):
                    d=proposal['data']
                    if d['status']!='needs_review' or d['proposal_kind']!='content' or d['policy_version']!=s['policy_version']:continue
                    author=c.execute('SELECT * FROM actors WHERE session_id=? AND id=?',(s['id'],d['author_id'])).fetchone()
                    if author is None or author['role'] not in ('participant','facilitator'):continue
                    c.execute('SAVEPOINT automatic_input')
                    previous=deepcopy(c.changed)
                    try:
                        self._refs(c,s['id'],d['refs'])
                        self._apply_input(c,s,dict(author),proposal)
                        self._event(c,s['id'],'system','workspace.input_applied',{'proposal_id':proposal['id']})
                        self._budget(c,s['id'])
                    except Problem:
                        c.execute('ROLLBACK TO automatic_input');c.changed=previous
                    c.execute('RELEASE automatic_input')

    def _source_text(self,c,s,a,b):
        fields(b,('text',));self._editor(a);self._active(s);value=text(b['text'],'text')
        source=self._new(c,s['id'],'source',{'type':'text','text':value,'author_id':a['id'],'origin':'human','created_at':self.clock()})
        if self.automatic_workspace:
            heard=recognise_command(value)
            segment=self._new(c,s['id'],'transcript_segment',{'text':value,'status':'final','input_method':'typed',
                'voice_command':heard,'author_id':a['id'],'speaker_actor_id':a['id'],'speaker_name':a['name'],
                'attribution':'per_connection','capture_id':'typed_inputs','capture_revision':s['revision'],
                'created_at':self.clock(),'source_id':source['id'],
                'provenance':{'producer':'typed-input','model_version':None,'synthetic':False}})
            self._poll_heard(c,s,a,segment);self._document_heard(c,s,a,segment)
            if heard and heard['status']=='recognised': return {'source':source,'command':segment}
        proposal=self._proposal(c,s,a,'content',value,[{'id':source['id'],'revision':1}])
        return {'source':source,'proposal':proposal}

    def _summary_to_stickies(self,c,s,a,b):
        """Publish an existing summary as proposed notes, never as accepted facts.

        Transcript-to-summary is intentionally outside this handler. Its caller
        may attach transcript refs later; the summary source keeps those refs so
        the boundary does not need another API change when that work lands.
        """
        fields(b,('summary',),('refs',));self._editor(a);self._active(s)
        value=text(b['summary'],'summary')
        supplied=b.get('refs',[])
        require(type(supplied) is list and len(supplied)<=60,'invalid_references','Supply at most 60 transcript, source or accepted-item references.')
        seen=set()
        for ref in supplied:
            fields(ref,('id','revision'))
            record=self._get(c,s['id'],ref['id']);self._expected(record,ref['revision'])
            require(record['kind'] in ('transcript_segment','source','item'),'invalid_reference',
                    'Summary evidence must be transcript, source or accepted-item records.')
            require(record['id'] not in seen,'duplicate_reference','Reference IDs must be unique.')
            seen.add(record['id'])
        ideas=ideas_from_summary(value)
        require(ideas,'empty_summary','The summary did not contain any sticky-note ideas.')
        batch_id=new_id()
        source=self._new(c,s['id'],'source',{'type':'summary','text':value,'refs':deepcopy(supplied),
            'author_id':a['id'],'origin':'model','created_at':self.clock(),
            'provenance':{'producer':'summary-to-sticky bridge','model_version':'deterministic-v1','synthetic':False}})

        # Put the batch to the right of everything already positioned. A
        # conservative 320 by 200 footprint protects human and machine notes
        # whose natural CSS size is not stored in the database.
        positions=self._positions(c,s['id'])
        right=max((p['x']+(p['w'] or 320) for p in positions.values()),default=-344)+24
        top=min((p['y'] for p in positions.values()),default=0)
        proposals=[]
        for index,idea in enumerate(ideas):
            extra={'summary_title':idea['title'],'summary_detail':idea['body'],
                'summary_category':idea['category'],'summary_importance':idea['importance'],
                'summary_batch_id':batch_id,'summary_order':index,
                'provider':'summary-to-sticky bridge','model':'deterministic-v1','synthetic':False}
            proposal=self._proposal(c,s,a,'content',idea['title'],[{'id':source['id'],'revision':1}],origin='model',extra=extra)
            x=right+(index%2)*344;y=top+(index//2)*224
            target=proposal['data'].get('item_id',proposal['id'])
            self._write_position(c,s['id'],target,x,y,False,a['id'])
            proposals.append(proposal)
        return {'source':source,'proposals':proposals,'batch_id':batch_id,'count':len(proposals)}

    def _source_image(self,c,s,a,b):
        fields(b,('mime','base64'),('regions',));self._editor(a);self._active(s)
        rs=regions(b['regions']) if 'regions' in b else []
        raw,_,_=image_payload(b['base64'],b['mime'])
        raw,mime,w,h=sanitise(raw,b['mime']);checksum=hashlib.sha256(raw).hexdigest()
        old=c.execute('SELECT id FROM media WHERE session_id=? AND digest=?',(s['id'],checksum)).fetchone()
        used=c.execute('SELECT coalesce(sum(length(payload)),0) FROM media WHERE session_id=?',(s['id'],)).fetchone()[0]
        require(used+(0 if old else len(raw))<=self.MAX_IMAGE_BYTES,'image_capacity','Session image storage limit reached.',429)
        mid=old['id'] if old else new_id()
        if not old:c.execute('INSERT INTO media VALUES(?,?,?,?,?,?,?)',(mid,s['id'],checksum,raw,mime,w,h))
        source=self._new(c,s['id'],'source',{'type':'image','mime':mime,'media_id':mid,'width':w,'height':h,'sanitised':True,
            'byte_count':len(raw),'regions':deepcopy(rs),**({'detect_notes':True} if not rs else {}),
            'author_id':a['id'],'origin':'human','created_at':self.clock()})
        return self._public(source)

    def _validate_audio(self,b,required_extra=()):
        # required_extra: speaker.enroll's body carries a 'name' field
        # alongside the same mime/base64/ended_reason audio fields
        # source.audio uses; passing it here keeps there being one audio
        # validator, not two that could drift on the duration/mime checks.
        optional=() if required_extra else ('capture_id','captured_at_ms','captured_at_utc_ms')
        fields(b,('mime','base64','ended_reason',*required_extra),optional)
        if 'capture_id' in b or 'captured_at_ms' in b:
            require('capture_id' in b and 'captured_at_ms' in b,'missing_fields',
                    'capture_id and captured_at_ms must be supplied together.')
            ident(b['capture_id'])
            integer(b['captured_at_ms'],'captured_at_ms',low=0,high=9007199254740991)
        if 'captured_at_utc_ms' in b:
            integer(b['captured_at_utc_ms'],'captured_at_utc_ms',low=0,high=9007199254740991)
        require(b['ended_reason'] in ('silence','hard_cut'),'invalid_ended_reason',
                'ended_reason must be silence or hard_cut.')
        raw,sample_rate,duration_ms=audio_payload(b['base64'],b['mime'])
        return raw,sample_rate,duration_ms

    def _transcribe_before_lock(self,sid,token,request_id,b):
        """Runs the (possibly multi-second) ASR call before command() opens
        its write transaction, so real local ASR does not hold SQLite's
        write lock, which db.transaction()'s BEGIN IMMEDIATE takes for the
        whole block, for that long. Held that long it serialises every other
        command on the server, in every session, for as long as one chunk
        takes to transcribe: with a real model that is seconds, not the
        milliseconds every other command needs, so chunks arriving faster
        than they can be transcribed pile up an ever-growing delay instead
        of the 2.7s pipelines.md budgets. This function only reads (no
        BEGIN IMMEDIATE), so it cannot itself block another command.

        Returns None when there is nothing to precompute: an existing
        request row means this is a replay, and command()'s normal
        idempotency check inside the transaction will return the original
        result without transcribing again; a validation failure here is
        re-raised, matching what _source_audio would have raised inline.
        """
        conn=self.db.connect()
        try:
            s,a=self._auth(conn,sid,token)
            old=conn.execute('SELECT 1 FROM requests WHERE session_id=? AND actor_id=? AND request_id=?',
                (sid,a['id'],request_id)).fetchone()
            if old:return None
            # Same order _source_audio enforces inside the lock: F6.1 says no
            # model call before consent/activation, so that gate must run
            # before transcribing here too, not only on the write path.
            self._editor(a);self._active(s)
            raw,sample_rate,duration_ms=self._validate_audio(b)
            self._calendar_capture_time(s, b)
            # Read while the connection is still open and read-only, same
            # reasoning as everything else in this function: a session with
            # no enrolled profiles must cost nothing extra, and this is one
            # cheap SELECT, not a model call.
            profiles=[(row['id'],json.loads(row['data'])['name'],tuple(json.loads(row['data'])['embedding']))
                for row in conn.execute("SELECT id,data FROM records WHERE session_id=? AND kind='speaker_profile'",(sid,)).fetchall()]
        finally:
            conn.close()
        request=TranscriptionInput(chunk_bytes=raw,sample_rate=sample_rate,duration_ms=duration_ms,
            ended_reason=b['ended_reason'],speaker_actor_id=a['id'])
        checksum=hashlib.sha256(raw).hexdigest()
        # F1.3: run voice-ID on the same chunk regardless of whether
        # transcription itself succeeds below; a gap in the transcript is no
        # reason to also skip looking at who it came from, and conversely a
        # failed/absent voice match must never block the transcript (F6.4).
        speaker_match=self._identify_speaker(raw,sample_rate,profiles) if profiles else None
        try:
            with self.transcription_lock:
                result=self.transcriber.transcribe(request)
            complete={'status':'final','text':result.text,'confidence':result.confidence,
                'provider':result.provider,'model':result.model,'synthetic':result.synthetic,
                'duration_ms':duration_ms,'checksum':checksum,'speaker_match':speaker_match}
            words=result.usage.get('words',[]) if isinstance(result.usage,dict) else []
            if len(profiles)>1 and words and hasattr(self.speaker_identifier,'identify_words'):
                with self.speaker_lock:
                    turns=self.speaker_identifier.identify_words(raw,sample_rate,words,profiles,self.speaker_match_threshold)
                if turns:
                    complete['segments']=[{**complete,'text':turn['text'].strip(),
                        'speaker_match':turn['speaker_match'],
                        'duration_ms':max(1,round((turn['end']-turn['start'])*1000)),
                        'turn_end_ms':round(turn['end']*1000)} for turn in turns if turn['text'].strip()]
            return complete
        except TranscriptionFailure as exc:
            # Silence is a successful detection of nothing to transcribe,
            # rather than a missing piece of conversation or a model failure.
            if str(exc)=='no_speech_detected':
                return {'status':'no_speech'}
            # F6.4: a stage that cannot produce output still emits something
            # the room can see, never a silent drop of what was said. The
            # segment itself only ever says 'gap' (F6.3's provenance is not
            # a place for a raw exception), so the reason has to go
            # somewhere a person can actually read it: stderr. The cause
            # here is a network/HTTP/model-loading failure, not session
            # content, so printing it is not the audio-content leak the
            # worker's own 'never print provider/source-bearing exceptions'
            # rule in __main__.py is guarding against.
            import sys
            cause=f' (caused by {type(exc.__cause__).__name__}: {exc.__cause__})' if exc.__cause__ else ''
            print(f'Transcription failed ({getattr(self.transcriber,"name","unknown")}): '
                  f'{exc}{cause}',file=sys.stderr)
            return {'status':'gap','text':None,'confidence':0.0,
                'provider':getattr(self.transcriber,'name','unknown'),'model':'none','synthetic':True,
                'duration_ms':duration_ms,'checksum':checksum,'speaker_match':speaker_match}

    def _identify_speaker(self,raw,sample_rate,profiles):
        """F1.3 opt-in voice-ID: one embedding of this chunk, compared by
        cosine similarity (adapters.match_speaker) to this session's
        enrolled speaker_profile records. Only called when `profiles` is
        non-empty (see _transcribe_before_lock), so a session nobody has
        enrolled anyone in never pays for this at all and never changes the
        existing per-connection attribution (backward compatible, opt-in).

        Always returns a dict with a 'status' of 'matched' or
        'unidentified', never raises: an embedding failure is logged
        (stderr, same place TranscriptionFailure's cause goes, for the same
        reason: it is a model/audio-processing failure, not session
        content) and reported as 'unidentified' with confidence 0.0, which
        _source_audio stores as a visible, honest state rather than
        dropping the chunk's voice-ID or guessing (F6.4, F6.3).
        """
        try:
            with self.speaker_lock:
                embedding=self.speaker_identifier.embed(raw,sample_rate)
        except SpeakerIdentificationFailure as exc:
            import sys
            print(f'Speaker identification failed ({getattr(self.speaker_identifier,"name","unknown")}): '
                  f'{exc}',file=sys.stderr)
            return {'status':'unidentified','profile_id':None,'name':None,'confidence':0.0,
                'provider':getattr(self.speaker_identifier,'name','unknown'),'model':'none',
                'synthetic':True,'reason':'embedding_failed'}
        profile_id,name,confidence=match_speaker(embedding.vector,profiles,self.speaker_match_threshold)
        return {'status':'matched' if profile_id else 'unidentified',
            'profile_id':profile_id,'name':name,'confidence':confidence,
            'provider':embedding.provider,'model':embedding.model,'synthetic':embedding.synthetic,
            'reason':None if profile_id else ('below_threshold' if confidence < self.speaker_match_threshold else 'ambiguous_match')}

    def _enroll_before_lock(self,sid,token,request_id,b):
        """speaker.enroll's analogue of _transcribe_before_lock: runs voice-
        embedding extraction before command() opens its write transaction,
        for the same reason (a real embedding model is a second CPU-bound
        call and must not hold SQLite's write lock). Enrollment happens once
        per person before a meeting, not continuously like transcription, so
        the lock-avoidance matters less here, but there is exactly one
        pattern in this file for 'a model call that must not block
        everything else', not a second one invented for this command.

        Unlike _transcribe_before_lock, a failure here is raised (Problem),
        not degraded to a gap: this is one deliberate action by one person
        right now, not a continuous stream, so the honest response to 'could
        not extract a voice profile from this clip' is to say so and let
        them retake it, not to silently store a broken profile.
        """
        conn=self.db.connect()
        try:
            s,a=self._auth(conn,sid,token)
            old=conn.execute('SELECT 1 FROM requests WHERE session_id=? AND actor_id=? AND request_id=?',
                (sid,a['id'],request_id)).fetchone()
            if old:return None
            # F6.1: same order as source.audio above. Enrollment is still
            # audio capture, so it needs the same active-session/consent
            # gate every other capture command already requires, checked
            # here before the model call, not only on the write path below.
            self._editor(a);self._active(s)
            raw,sample_rate,duration_ms=self._validate_audio(b,required_extra=('name',))
            name=text(b['name'],'name',limit=200)
        finally:
            conn.close()
        checksum=hashlib.sha256(raw).hexdigest()
        try:
            with self.speaker_lock:
                result=self.speaker_identifier.embed(raw,sample_rate)
        except SpeakerIdentificationFailure as exc:
            raise Problem(422,'speaker_id_failed',
                f'Could not extract a voice profile from this clip: {exc}') from exc
        return {'name':name,'embedding':result.vector,'provider':result.provider,
            'model':result.model,'synthetic':result.synthetic,'duration_ms':duration_ms,'checksum':checksum}

    def _speaker_enroll(self,c,s,a,b,precomputed):
        """F1.3 opt-in voice-ID enrollment: one short reference clip plus a
        name in, one speaker_profile record out, scoped to this session.
        Gated by self._active(s), the same F6.1 consent/activation guard
        source.audio, source.text and source.image already require:
        recording a clip is still capture, so it does not get a separate,
        weaker gate. See decisions/decision-log.md for why this is additive
        to the existing per-connection fallback rather than replacing it,
        and why a low-confidence match (adapters.match_speaker) comes back
        unidentified rather than a guess.

        `precomputed` is always the result of _enroll_before_lock, this
        method's only caller's pre-lock step; this method re-runs the cheap
        field/duration validation (not the embedding extraction) in case
        session/role state changed between that read and this write
        acquiring the lock, same pattern _source_audio follows for audio.
        """
        self._editor(a);self._active(s)
        self._validate_audio(b,required_extra=('name',));name=text(b['name'],'name',limit=200)
        embedding=precomputed['embedding'];provider=precomputed['provider'];model=precomputed['model']
        synthetic=precomputed['synthetic'];checksum=precomputed['checksum']
        previous=next((r for r in self._list(c,s['id'],'speaker_profile') if r['data']['name'].strip().casefold()==name.strip().casefold()),None)
        profile_data={
            'name':name,'embedding':list(embedding),'enrolled_by':a['id'],
            'author_id':a['id'],'origin':'human','created_at':self.clock(),
            'provenance':{'producer':provider,'model_version':model,'synthetic':synthetic,
                          'checksum':checksum,'created_at':self.clock()}}
        profile=self._save(c,s['id'],previous,profile_data) if previous else self._new(c,s['id'],'speaker_profile',profile_data)
        return {'profile':profile}

    def _source_audio(self,c,s,a,b,precomputed):
        """F1.1-F1.3: one endpointed chunk in, one transcript_segment record out.

        Single-lane by design (see decisions/decision-log.md): no fast/slow
        two-lane split, so this stands for pipelines.md stages S5-S9 in one
        call. Consent/activation gate is self._active(s), the same guard
        source.text and source.image already require: F6.1 is enforced once,
        not re-implemented per source type. Diarisation (S7) is the
        documented per-connection fallback, not embedding+clustering: the
        speaking actor is whoever's credential sent the chunk. A slow or
        failing transcriber never drops a chunk silently (F6.4): it is
        recorded as a gap with its own provenance and duration.

        `precomputed` is always the result of _transcribe_before_lock, run by
        this method's only caller (command()) before it opened the write
        transaction this method runs inside, so the transcription call
        itself never holds it. This method re-runs the cheap field/duration
        validation (not the transcription) in case session/role state
        changed between that read and this write acquiring the lock.
        """
        self._editor(a);self._active(s)
        self._validate_audio(b)
        if precomputed.get('segments'):
            rows=[]
            for segment in precomputed['segments']:
                body=dict(b)
                if 'captured_at_ms' in body:
                    body['captured_at_ms']=max(0,body['captured_at_ms']-precomputed['duration_ms']+segment['turn_end_ms'])
                rows.append(self._source_audio(c,s,a,body,segment))
            return {'segments':rows}
        if precomputed['status']=='no_speech':
            return {'status':'no_speech','_noop':True}
        status=precomputed['status'];text_out=precomputed['text'];confidence=precomputed['confidence']
        provider=precomputed['provider'];model=precomputed['model'];synthetic=precomputed['synthetic']
        duration_ms=precomputed['duration_ms'];checksum=precomputed['checksum']
        count=c.execute("SELECT count(*) FROM records WHERE session_id=? AND kind='transcript_segment'",(s['id'],)).fetchone()[0]
        require(count<self.MAX_AUDIO_CHUNKS,'audio_capacity','Session transcript length limit reached.',429)
        # F1.3: speaker_match is None when no profiles are enrolled for this
        # session, in which case attribution is exactly what it always was
        # (per_connection, backward compatible). Once someone has enrolled a
        # profile, per_connection (whoever's device sent the chunk) is the
        # label this feature exists to replace, in a one-mic/many-people
        # room it is not a fallback worth keeping for that chunk, so a
        # confident match is named and anything else is the explicit
        # 'unidentified' state rather than a silently reused device label.
        # See decisions/decision-log.md.
        speaker_match=precomputed.get('speaker_match')
        if speaker_match is None:
            attribution='per_connection';speaker_profile_id=None;speaker_name=None
            speaker_confidence=None;speaker_provenance=None
        elif speaker_match['status']=='matched':
            attribution='voice_identified';speaker_profile_id=speaker_match['profile_id'];speaker_name=speaker_match['name']
            speaker_confidence=speaker_match['confidence']
            speaker_provenance={'producer':speaker_match['provider'],'model_version':speaker_match['model'],
                'synthetic':speaker_match['synthetic'],'matched_profile_id':speaker_match['profile_id'],
                'confidence':speaker_match['confidence']}
        else:
            attribution='unidentified';speaker_profile_id=None;speaker_name=None
            speaker_confidence=speaker_match['confidence']
            speaker_provenance={'producer':speaker_match['provider'],'model_version':speaker_match['model'],
                'synthetic':speaker_match['synthetic'],'confidence':speaker_match['confidence'],
                'reason':speaker_match['reason']}
        heard=recognise_command(text_out,status=status,synthetic=synthetic)
        correction=normalise_activation_phrase(text_out,status=status,synthetic=synthetic)
        self._calendar_capture_time(s, b)
        capture_fields={key:b[key] for key in ('capture_id','captured_at_ms','captured_at_utc_ms') if key in b}
        if capture_fields:
            capture_fields['capture_revision']=s['revision']
        if heard is None and capture_fields:
            previous=c.execute("SELECT id,data FROM records WHERE session_id=? AND kind='transcript_segment' AND json_extract(data,'$.speaker_actor_id')=? ORDER BY rowid DESC LIMIT 1",(s['id'],a['id'])).fetchone()
            if previous:
                heard=recognise_continuation({**capture_fields,'speaker_actor_id':a['id'],
                    'text':text_out,'status':status,'provenance':{'synthetic':synthetic}},json.loads(previous['data']))
                if heard:
                    heard['activation_segment_id']=previous['id']
        source=self._new(c,s['id'],'transcript_segment',{
            'status':status,'text':text_out,'confidence':confidence,
            **({'activation_correction':correction} if correction and correction['corrected'] else {}),
            **({'failure_reason':'transcription_failed'} if status=='gap' else {}),
            'voice_command':heard,**capture_fields,
            'speaker_actor_id':a['id'],'attribution':attribution,
            'speaker_profile_id':speaker_profile_id,'speaker_name':speaker_name,
            'speaker_confidence':speaker_confidence,
            'duration_ms':duration_ms,'ended_reason':b['ended_reason'],
            'author_id':a['id'],'origin':'model','created_at':self.clock(),
            'provenance':{'producer':provider,'model_version':model,'synthetic':synthetic,
                          'checksum':checksum,'created_at':self.clock(),
                          **({'speaker':speaker_provenance} if speaker_provenance else {})}})
        self._poll_heard(c,s,a,source)
        self._document_heard(c,s,a,source)
        return source

    def _source_correct(self,c,s,a,b):
        fields(b,('source_id','expected_revision','text'));self._editor(a)
        source=self._get(c,s['id'],b['source_id'],'source');self._expected(source,b['expected_revision'])
        require(a['role']=='facilitator' or source['data']['author_id']==a['id'],'forbidden','Only uploader or facilitator can correct this source.',403)
        require(source['data']['type']=='text','wrong_source_type','Use region review for image sources.')
        d=source['data'];d['text']=text(b['text'],'text');d['last_editor']=a['id']
        updated=self._save(c,s['id'],source,d)
        return {'source':updated,'invalidated':self._invalidate(c,s['id'],source['id'])}

    def _source_regions(self,c,s,a,b):
        fields(b,('source_id','expected_revision','regions'));self._editor(a)
        source=self._get(c,s['id'],b['source_id'],'source');self._expected(source,b['expected_revision'])
        require(source['data']['type']=='image','wrong_source_type','Regions belong to image sources.')
        require(a['role']=='facilitator' or source['data']['author_id']==a['id'],'forbidden','Only uploader or facilitator can change regions.',403)
        d=source['data'];d['regions']=deepcopy(regions(b['regions']));d['last_editor']=a['id'];d.pop('detect_notes',None)
        updated=self._save(c,s['id'],source,d)
        return {'source':self._public(updated),'invalidated':self._invalidate(c,s['id'],source['id'])}

    def _queue(self,c,s,a,b):
        fields(b,('source_id','expected_revision'),('retry_of','acknowledge_uncertain_cost'));self._editor(a);self._active(s)
        source=self._get(c,s['id'],b['source_id'],'source');self._expected(source,b['expected_revision'])
        require(source['data']['type']=='image','wrong_source_type','Extraction requires an image source.')
        self._media_row(c,s['id'],source)
        jobs=self._list(c,s['id'],'job')
        uncertain=[j for j in jobs if j['data']['status'] in ('failed','cancelled')
                   and (j['data'].get('execution_outcome')=='unknown' or j['data'].get('error')=='interrupted_unknown_outcome')
                   and j['data']['refs'][0]['id']==source['id']]
        retry_of=b.get('retry_of')
        if uncertain:
            require(retry_of==uncertain[-1]['id'] and b.get('acknowledge_uncertain_cost') is True,
                    'uncertain_retry_requires_acknowledgement','An earlier extraction may have completed or incurred cost. Explicitly acknowledge that outcome before a new attempt.',409,
                    retry_of=uncertain[-1]['id'])
        else:
            require(retry_of is None and 'acknowledge_uncertain_cost' not in b,
                    'invalid_retry','Retry acknowledgement is only valid for an interrupted extraction of this source.')
        require(sum(j['data']['status'] in ('queued','running') for j in jobs)<self.MAX_JOBS,'queue_full','Extraction queue is full; retry later or transcribe manually.',429)
        require(c.execute("SELECT count(*) FROM records WHERE kind='job' AND json_extract(data,'$.status') IN ('queued','running')").fetchone()[0]<self.MAX_INSTANCE_JOBS,
                'instance_queue_full','Instance extraction queue is full; retry later.',429)
        return self._new(c,s['id'],'job',{'status':'queued','refs':[{'id':source['id'],'revision':source['revision']}],
            'policy_version':s['policy_version'],'author_id':a['id'],'created_at':self.clock(),'deadline':self.clock()+60,
            'attempts':0,'adapter':self.extractor.name,'synthetic':True,'error':None,
            'retry_of':retry_of,'uncertain_cost_acknowledged':bool(uncertain)})

    def _cancel(self,c,s,a,b):
        fields(b,('job_id','expected_revision'));self._editor(a)
        job=self._get(c,s['id'],b['job_id'],'job');self._expected(job,b['expected_revision'])
        require(a['role']=='facilitator' or job['data']['author_id']==a['id'],'forbidden','Only requester or facilitator can cancel.',403)
        require(job['data']['status'] in ('queued','running'),'job_terminal','Job has already finished.',409)
        d=job['data'];d.update(status='cancelled',error='user_cancelled');return self._save(c,s['id'],job,d)

    # Position. See spec/canvas-layout.md for the vocabulary these use.
    #
    # Hand-placed means a person created, dragged, accepted or edited the item.
    # It is sticky for the rest of the session, because F3.4 protects a person's
    # arrangement permanently: once someone has put a note somewhere, the layout
    # engine may never move it again.

    def _positions(self,c,sid):
        rows=c.execute('SELECT * FROM positions WHERE session_id=?',(sid,)).fetchall()
        return {r['record_id']:{'x':r['x'],'y':r['y'],'w':r['w'],'h':r['h'],'revision':r['revision'],
                                'hand_placed':bool(r['hand_placed']),'placed_by':r['placed_by'],
                                'placed_at':r['placed_at']} for r in rows}

    def _position(self,c,sid,rid):
        row=c.execute('SELECT * FROM positions WHERE session_id=? AND record_id=?',(sid,rid)).fetchone()
        return None if row is None else {'x':row['x'],'y':row['y'],'w':row['w'],'h':row['h'],'revision':row['revision'],
                                         'hand_placed':bool(row['hand_placed']),'placed_by':row['placed_by'],
                                         'placed_at':row['placed_at']}

    @staticmethod
    def _board_order(positions):
        """Board z-order, innermost first, per spec/canvas-layout.md: the layout
        engine's guesses, then what people placed, then whatever was touched
        last. Ties break on record id so two clients agree.

        A pure function of the positions a client already holds, which is why a
        delta does not send it. See `delta`.
        """
        return sorted(positions,key=lambda rid:(positions[rid]['hand_placed'],
                                                positions[rid]['placed_at'],rid))

    def _write_position(self,c,sid,rid,x,y,hand,actor_id,size=None):
        """Write one position. Never touches the record, so no revision is bumped.

        `size` is (w, h) to set, or None to keep what the row has: a move that
        does not mention a size must not erase one.
        """
        row=c.execute('SELECT revision,hand_placed,w,h FROM positions WHERE session_id=? AND record_id=?',(sid,rid)).fetchone()
        revision=(row['revision'] if row else 0)+1
        w,h=size if size is not None else ((row['w'],row['h']) if row else (None,None))
        w,h=(None if w is None else float(w)),(None if h is None else float(h))
        # Once true this never goes back to false, and no second mechanism is
        # needed for that: a machine placement is refused outright on a
        # hand-placed record, so the only writes that reach here with hand=False
        # are on records nobody has touched. An `or existing` clause here would
        # be unreachable, which the mutation harness proved by deleting it and
        # watching the suite stay green.
        hand_placed=1 if hand else 0
        c.execute('INSERT OR REPLACE INTO positions(session_id,record_id,x,y,revision,hand_placed,placed_by,placed_at,w,h) '
                  'VALUES(?,?,?,?,?,?,?,?,?,?)',(sid,rid,float(x),float(y),revision,hand_placed,actor_id,self.clock(),w,h))
        self._track(c,{'id':rid,'revision':revision},'position')
        return {'id':rid,'x':float(x),'y':float(y),'w':w,'h':h,'revision':revision,'hand_placed':bool(hand_placed),
                'placed_by':actor_id}

    @staticmethod
    def _object_kind(record):
        """What a record is on the canvas: a canvas kind, 'note', 'cluster' or another kind."""
        d=record['data']
        if record['kind']=='proposal' and d.get('proposal_kind')=='canvas':return d.get('canvas_kind')
        kind=d.get('item_kind') if record['kind']=='item' else d.get('proposal_kind')
        if d.get('form')=='cluster':return 'cluster'
        return 'note' if kind=='content' else kind

    @staticmethod
    def _on_board(record):
        # The same test item.place uses, so "on the canvas" has one meaning.
        return record['kind'] in ('item','proposal') and record['data'].get('status') not in ('undone','rejected','superseded')

    def _coordinates(self,body,code='invalid_position'):
        for key in ('x','y'):
            value=body.get(key)
            require(type(value) in (int,float) and math.isfinite(value) and abs(value)<=self.MAX_COORDINATE,
                    code,'Coordinates must be finite and within \u00b1%d.'%self.MAX_COORDINATE)

    def _size(self,kind,body,required):
        """The (w, h) a body carries, or None when it carries neither.

        `required` is true when this write creates the position of a shape, text
        or section: without a size there is nothing to draw. A note or cluster
        is refused a size outright, because its width follows its text and a
        stored width would be a second answer to that.
        """
        if 'w' not in body and 'h' not in body:
            require(not required,'invalid_size','A shape, text or section needs w and h when it is first placed.')
            return None
        require(kind in self.CANVAS_KINDS,'invalid_size','Notes and clusters take their width from their text; only canvas objects carry a size.')
        for key in ('w','h'):
            value=body.get(key)
            require(type(value) in (int,float) and math.isfinite(value) and self.MIN_SIZE<=value<=self.MAX_SIZE,
                    'invalid_size','Give both w and h, each from %d to %d.'%(self.MIN_SIZE,self.MAX_SIZE))
        return (body.get('w'),body.get('h'))

    def _place(self,c,s,a,b):
        """Move records on the board. Any editor, no review, all or nothing.

        Moving is not agreement. Dragging a provisional note somewhere useful is
        how a person reads a board, and making it cost a facilitator decision
        was what forced two records and a review for one drag. What a move does
        assert is that a person touched it, which is why it sets hand_placed.
        """
        fields(b,('placements',),('origin',));self._editor(a)
        # Deliberately not gated on an active session, unlike capture. A move
        # adds no content and asserts no agreement, and chunk E documents that a
        # missed heartbeat alone pauses a session, so gating this would freeze
        # the board every time the facilitator stepped out of the room.
        origin=b.get('origin','human')
        require(origin in ('human','machine'),'invalid_origin','Placement origin is human or machine.')
        placements=b['placements']
        require(type(placements) is list and 1<=len(placements)<=self.MAX_PLACEMENTS,
                'invalid_placements','Move between 1 and %d records at once.'%self.MAX_PLACEMENTS)
        current=self._positions(c,s['id']);seen=set();validated=[]
        for p in placements:
            fields(p,('id','x','y','expected_position_revision'),('w','h'))
            # Before the set test, not after: an id of [1] is unhashable, and
            # `not in seen` raised TypeError, which surfaced as a 500.
            ident(p['id'])
            require(p['id'] not in seen,'duplicate_placement','Each record may appear once in a move.')
            seen.add(p['id'])
            record=self._get(c,s['id'],p['id'])
            require(record['kind'] in ('item','proposal','poll','command_document'),'invalid_target','Only items, proposals, polls and command documents occupy the board.')
            require(record['data'].get('status') not in ('undone','rejected','superseded'),
                    'invalid_target','That record is not on the board.',409)
            for key in ('x','y'):
                require(type(p[key]) in (int,float) and type(p[key]) is not bool and math.isfinite(p[key])
                        and abs(p[key])<=self.MAX_COORDINATE,
                        'invalid_position','Coordinates must be finite and within \u00b1%d.'%self.MAX_COORDINATE)
            existing=current.get(p['id'])
            integer(p['expected_position_revision'],'expected_position_revision',0)
            require((existing['revision'] if existing else 0)==p['expected_position_revision'],
                    'stale_position','The record moved. Fetch its current position before moving it again.',409,
                    record_id=p['id'],current_position_revision=existing['revision'] if existing else 0)
            require(origin=='human' or not (existing and existing['hand_placed']),
                    'hand_placed','A person placed this record; the layout engine may not move it.',409,record_id=p['id'])
            kind=self._object_kind(record)
            size=self._size(kind,p,kind in self.SIZED_KINDS and (existing is None or existing['w'] is None))
            validated.append((p,size))
        # Validated in full before anything is written. The transaction would roll
        # a partial move back anyway, but a half-checked move is not worth writing.
        return {'placements':[self._write_position(c,s['id'],p['id'],p['x'],p['y'],origin=='human',a['id'],size)
                              for p,size in validated]}

    # Canvas objects: shapes, text, arrows, sections and strokes. Made by hand,
    # they are arranging, like moving a note, so they are on the canvas at once
    # with no review. Made by a model, they are a `canvas` proposal and wait for
    # a facilitator like everything else a model makes. Not gated on an active
    # session for the reason item.place is not: arranging adds no captured
    # content, and a missed heartbeat alone pauses a session.

    def _canvas_data(self,c,sid,kind,data,self_id=None):
        """Validate one object's own fields and return a clean copy."""
        required,optional=self.CANVAS_FIELDS.get(kind,((),()))
        fields(data,required,optional)
        if 'tone' in required:
            require(data['tone'] in self.TONES,'invalid_tone','Tone is ink, accent or one of the three categories.')
        if kind=='shape':
            require(data['shape'] in self.SHAPES,'invalid_shape','Shape is rect, ellipse, diamond or line.')
            if 'text' in data:text(data['text'],'text',280,empty=True)
        elif kind=='text':
            text(data['text'],'text',1000)
            require(data['size'] in self.TEXT_SIZES,'invalid_text_size','Text size is body, title or heading.')
        elif kind=='arrow':
            for end in ('from','to'):self._endpoint(c,sid,data[end],end,self_id)
            # Checked after both ends validate, so `get` cannot meet a non-dict.
            require(not ('id' in data['from'] and data['from'].get('id')==data['to'].get('id')),
                    'self_arrow','An arrow cannot point from a record to itself.')
            if 'label' in data:text(data['label'],'label',80,empty=True)
        elif kind=='section':
            text(data['title'],'title',80,empty=True)
            require(data['form'] in self.SECTION_FORMS,'invalid_form','Section form is free, cluster, timeline, matrix or flow.')
            members=data['member_ids']
            require(type(members) is list,'invalid_members','member_ids is a list of record IDs.')
            require(len(members)<=self.MAX_SECTION_MEMBERS,'section_too_large',
                    'A section holds at most %d members.'%self.MAX_SECTION_MEMBERS)
            seen=set()
            for rid in members:
                ident(rid)
                require(rid not in seen,'duplicate_member','Each member appears once.');seen.add(rid)
                member=self._get(c,sid,rid)
                kind_of=self._object_kind(member)
                # Never a section: sections inside sections make "which area is
                # this in" a tree, and dragging one would move a hidden subtree.
                require(kind_of!='section' and rid!=self_id,'nested_section','A section cannot hold a section.')
                require(member['kind'] in ('item','proposal') and kind_of in ('note','shape','text','stroke'),
                        'invalid_member','A member is a note, shape, text or stroke.',record_id=rid)
                require(self._on_board(member),'invalid_member','That member is not on the canvas.',409,record_id=rid)
        elif kind=='stroke':
            points=data['points']
            require(type(points) is list and 2<=len(points)<=self.MAX_STROKE_POINTS,'invalid_points',
                    'A stroke has 2 to %d points.'%self.MAX_STROKE_POINTS)
            for point in points:
                require(type(point) is list and len(point)==2 and all(type(v) in (int,float) and math.isfinite(v)
                        and abs(v)<=self.MAX_STROKE_OFFSET for v in point),'invalid_points',
                        'Each point is [x, y], finite and within \u00b1%d of the position.'%self.MAX_STROKE_OFFSET)
            require(data['weight'] in self.STROKE_WEIGHTS,'invalid_weight','Weight is fine, regular or bold.')
        return deepcopy(data)

    def _endpoint(self,c,sid,value,name,self_id):
        require(type(value) is dict and (value.keys()=={'id'} or value.keys()=={'x','y'}),'invalid_endpoint',
                '%s is {"id": record} or {"x": n, "y": n}.'%name)
        if 'id' not in value:
            self._coordinates(value,'invalid_endpoint');return
        require(value['id']!=self_id,'self_arrow','An arrow cannot point at itself.')
        record=self._get(c,sid,value['id'])
        require(record['kind'] in ('item','proposal'),'invalid_endpoint','An arrow connects records on the canvas.',record_id=value['id'])
        require(self._on_board(record),'invalid_endpoint','That record is not on the canvas.',409,record_id=value['id'])

    def _canvas_create(self,c,s,a,b):
        """A person draws an object: an accepted item at once, hand-placed, no review."""
        fields(b,('kind','data','x','y'),('w','h'));self._editor(a)
        kind=b['kind']
        require(kind in self.CANVAS_KINDS,'invalid_kind','A canvas object is a shape, text, arrow, section or stroke.')
        data=self._canvas_data(c,s['id'],kind,b['data'])
        self._coordinates(b)
        size=self._size(kind,b,kind in self.SIZED_KINDS)
        item=self._new(c,s['id'],'item',{'item_kind':kind,**data,'origin':'human','made_by_hand':True,
            'author_id':a['id'],'accepted_by':a['id'],'last_editor':a['id'],'status':'accepted','created_at':self.clock()})
        return {'item':item,'position':self._write_position(c,s['id'],item['id'],b['x'],b['y'],True,a['id'],size)}

    def _canvas_target(self,c,s,b,verb):
        r=self._get(c,s['id'],b['item_id'],'item');self._expected(r,b['expected_revision'])
        kind=r['data'].get('item_kind')
        require(kind in self.CANVAS_KINDS,'invalid_target','Only shapes, text, arrows, sections and strokes can be %s this way.'%verb)
        require(r['data'].get('status')!='undone','item_undone','That object was removed; item.undo restores it.',409)
        return r,kind

    def _canvas_update(self,c,s,a,b):
        """Change an object's own fields: a new revision, no review.

        `data` names only the fields that change and is merged onto the current
        ones, then the whole object is validated again, so an update cannot
        leave an arrow pointing at itself that creation would have refused.
        Common fields (origin, author, status) are not the kind's own and are
        refused, because provenance is not something an edit may rewrite.
        """
        fields(b,('item_id','expected_revision','data'));self._editor(a)
        r,kind=self._canvas_target(c,s,b,'updated')
        require(type(b['data']) is dict and b['data'],'invalid_data','Name at least one field to change.')
        required,optional=self.CANVAS_FIELDS.get(kind,((),()))
        own=set(required)|set(optional)
        merged={key:value for key,value in r['data'].items() if key in own}
        merged.update(b['data'])
        clean=self._canvas_data(c,s['id'],kind,merged,self_id=r['id'])
        d={key:value for key,value in r['data'].items() if key not in own}
        d.update(clean);d['last_editor']=a['id']
        return {'item':self._save(c,s['id'],r,d),'invalidated':self._invalidate(c,s['id'],r['id'])}

    def _canvas_remove(self,c,s,a,b):
        """Take an object off the canvas. Marked undone, not deleted, so item.undo restores it."""
        fields(b,('item_id','expected_revision'));self._editor(a)
        r,_=self._canvas_target(c,s,b,'removed')
        d=r['data'];d.update(status='undone',last_editor=a['id'],removed_by=a['id'])
        return {'item':self._save(c,s['id'],r,d),'invalidated':self._invalidate(c,s['id'],r['id'])}

    def _canvas_proposal(self,c,s,a,b):
        """A canvas object somebody proposes rather than draws: reviewed like any proposal.

        `positions` is optional and holds exactly one entry, the proposal's own
        place, `{x, y, w?, h?}`, with the same size rules as item.place. It is a
        machine placement, so the layout engine may still refine it and a
        person's later drag overrides it.
        """
        fields(b,('proposal_kind','canvas_kind','canvas_data'),('positions',));self._editor(a)
        kind=b['canvas_kind']
        require(kind in self.CANVAS_KINDS,'invalid_kind','canvas_kind is shape, text, arrow, section or stroke.')
        data=self._canvas_data(c,s['id'],kind,b['canvas_data'])
        place=None
        if 'positions' in b:
            positions=b['positions']
            require(type(positions) is list and len(positions)==1,'invalid_positions',
                    'A canvas proposal takes one position, its own: [{x, y, w?, h?}].')
            place=positions[0];fields(place,('x','y'),('w','h'));self._coordinates(place,'invalid_positions')
            size=self._size(kind,place,kind in self.SIZED_KINDS)
        proposal=self._new(c,s['id'],'proposal',{'proposal_kind':'canvas','canvas_kind':kind,'canvas_data':data,
            'origin':'human','author_id':a['id'],'status':'needs_review','policy_version':s['policy_version'],
            'created_at':self.clock()})
        if place is not None:
            self._write_position(c,s['id'],proposal['id'],place['x'],place['y'],False,a['id'],size)
        return proposal

    def _proposal_create(self,c,s,a,b):
        if type(b) is dict and b.get('proposal_kind')=='canvas':return self._canvas_proposal(c,s,a,b)
        fields(b,('proposal_kind','text','refs'),('positions','region_id','form'));self._editor(a)
        kind=b['proposal_kind'];require(kind in ('content','relationship','placement'),'invalid_kind','Unknown proposal kind.')
        refs=self._refs(c,s['id'],b['refs']);value=text(b['text'],'text')
        extra={}
        if 'region_id' in b:
            require(kind=='content','invalid_region','Only content proposals can identify a crop region.')
            self._region_ref(c,s['id'],b['region_id'],refs)
            extra.update(region_id=b['region_id'],reading_status='human_transcribed')
        if kind in ('relationship','placement'):
            require(all(self._get(c,s['id'],r['id'])['kind']=='item' for r in refs),'invalid_targets','Relationships and placements target accepted items.')
        if 'form' in b:
            require(kind=='relationship','invalid_form','Only a relationship proposal takes a form.')
            require(b['form']=='cluster','invalid_form','The only implemented form is a cluster.')
            self._cluster_refs(c,s['id'],refs)
            extra['form']='cluster'
        if kind=='placement':
            positions=b.get('positions');require(type(positions) is list and len(positions)==len(refs),'invalid_positions','Give one position per target item.')
            ids=[]
            for p in positions:
                fields(p,('id','x','y'));ids.append(p['id'])
                require(all(type(p[k]) in (int,float) and math.isfinite(p[k]) and abs(p[k])<=100000 for k in ('x','y')),
                        'invalid_positions','Coordinates must be finite and within ±100000.')
            require(len(set(ids))==len(ids) and set(ids)=={r['id'] for r in refs},'invalid_positions','Positions must match target IDs exactly.')
            extra['positions']=deepcopy(positions)
        else:require('positions' not in b,'invalid_positions','Positions apply only to placement proposals.')
        return self._proposal(c,s,a,kind,value,refs,extra=extra)

    # Clusters. A cluster is a relationship with a form, so it rides the review
    # path like everything else a model makes: a grouping the model drew is
    # provisional until a person accepts it, which is the rule the whole product
    # turns on. Its hull is drawn by the client from the members' positions, and
    # membership is by explicit reference here rather than by geometry, so two
    # clients cannot disagree about who is in a group.

    def _clusters(self,c,sid,ignore=None):
        return [r for r in self._list(c,sid,'item')
                if r['data'].get('form')=='cluster' and r['data']['status']!='undone'
                and r['id']!=ignore]

    def _cluster_refs(self,c,sid,refs,cluster_id=None):
        """Membership rules, shared by proposing a cluster and editing one."""
        require(len(refs)<=self.MAX_CLUSTER_MEMBERS,'cluster_too_large',
                'A form holds at most %d items; past that it is a list.'%self.MAX_CLUSTER_MEMBERS)
        # One cluster per item. The spec draws a hull 12px outside its members
        # and asks for 24px between an item and a hull it is not in, so an item
        # inside two hulls cannot satisfy its own separation rules. That makes
        # this a drawing constraint, not a policy choice.
        taken={}
        for cluster in self._clusters(c,sid,ignore=cluster_id):
            for ref in cluster['data']['refs']:taken[ref['id']]=cluster['id']
        for ref in refs:
            require(ref['id'] not in taken,'already_clustered',
                    'That item is already in a cluster; take it out of that one first.',409,
                    record_id=ref['id'],cluster_id=taken.get(ref['id']))
        return refs

    def _cluster_membership(self,c,s,a,b):
        """Move items in and out of a cluster, without review.

        Joining a group by dragging is a person's arrangement act, the same as
        `item.place`, and the spec has the item land where it was dropped. What
        the model proposes still goes through review, because that is a claim
        about meaning rather than a person acting on their own board.
        """
        fields(b,('cluster_id','expected_revision'),('add','remove'));self._editor(a)
        cluster=self._get(c,s['id'],b['cluster_id'],'item');self._expected(cluster,b['expected_revision'])
        require(cluster['data'].get('form')=='cluster','not_a_cluster','That item is not a cluster.')
        require(cluster['data']['status']!='undone','item_undone','That cluster was undone.',409)
        add,remove=b.get('add',[]),b.get('remove',[])
        for value in (add,remove):
            require(type(value) is list and len(value)<=self.MAX_CLUSTER_MEMBERS,
                    'invalid_membership','add and remove are lists of item IDs.')
            for rid in value:ident(rid)
        require(add or remove,'invalid_membership','Name at least one item to add or remove.')
        require(not (set(add)&set(remove)),'invalid_membership','An item cannot be added and removed at once.')

        members=[ref for ref in cluster['data']['refs'] if ref['id'] not in set(remove)]
        require(len(members)+len(add)==len(cluster['data']['refs'])-len(remove)+len(add),'invalid_membership','Duplicate removal.')
        for rid in add:
            require(all(ref['id']!=rid for ref in members),'invalid_membership','That item is already in this cluster.')
            record=self._get(c,s['id'],rid,'item')
            require(record['data'].get('form')!='cluster','invalid_membership','A cluster cannot hold a cluster.')
            require(record['data']['status'] not in ('undone','stale'),'stale_reference',
                    'Referenced item requires review or was undone.',409)
            members.append({'id':rid,'revision':record['revision']})
        self._cluster_refs(c,s['id'],members,cluster_id=cluster['id'])

        d=cluster['data'];d['refs']=members;d['last_editor']=a['id']
        if not members:
            # An empty cluster has nothing to contain and no hull to draw. Marked
            # undone rather than deleted, because what the meeting grouped is
            # evidence, and item.undo can restore it with its members.
            d.update(status='undone',emptied_by=a['id'])
        return {'item':self._save(c,s['id'],cluster,d),'members':[ref['id'] for ref in members]}

    def _human_reading(self,d):
        # A person retyped the note, so the model's confidence no longer
        # describes this text. The version history keeps what the model said.
        # Colour stays: editing the words does not repaint the paper.
        d['reading_status']='human_transcribed'
        if 'confidence' in d:d['confidence']=None

    def _region_ref(self,c,sid,region_id,refs):
        ident(region_id)
        require(len(refs)==1,'invalid_region','A crop proposal must reference exactly one image source.')
        source=self._get(c,sid,refs[0]['id'],'source')
        require(source['data']['type']=='image' and any(r['id']==region_id for r in source['data']['regions']),
                'invalid_region','The crop region no longer exists; create a proposal for a current region.',409)

    def _proposal_edit(self,c,s,a,b):
        fields(b,('proposal_id','expected_revision','text','refs'));self._editor(a)
        r=self._get(c,s['id'],b['proposal_id'],'proposal');self._expected(r,b['expected_revision'])
        require(a['role']=='facilitator' or r['data']['author_id']==a['id'],'forbidden','Only author or facilitator can edit a proposal.',403)
        require(r['data']['status'] in ('needs_review','stale'),'proposal_terminal','Accepted/rejected proposals are immutable.',409)
        # A canvas proposal has no text or refs to edit. Changing what was
        # proposed is a rejection and a fresh proposal, so the history shows both.
        require(r['data'].get('proposal_kind')!='canvas','invalid_target','Reject a canvas proposal and propose again to change it.',409)
        refs=self._refs(c,s['id'],b['refs'])
        # Refreshing placement geometry after a target change needs a fresh proposal.
        if r['data']['proposal_kind']=='placement':
            require(refs==r['data']['refs'],'new_placement_required','Create a new placement preview for changed targets.',409)
        if r['data']['proposal_kind']=='relationship':
            require(all(self._get(c,s['id'],ref['id'])['kind']=='item' for ref in refs),'invalid_targets','Relationship targets must be items.')
        d=r['data'];d.update(text=text(b['text'],'text'),refs=deepcopy(refs),status='needs_review',policy_version=s['policy_version'],last_editor=a['id'])
        if 'region_id' in d:
            self._region_ref(c,s['id'],d['region_id'],refs)
            self._human_reading(d)
        return self._save(c,s['id'],r,d)

    def _review(self,c,s,a,b):
        fields(b,('proposal_id','expected_revision','decision'));self._facilitator(a)
        require(b['decision'] in ('accept','reject'),'invalid_decision','Choose accept or reject.')
        r=self._get(c,s['id'],b['proposal_id'],'proposal');self._expected(r,b['expected_revision'])
        require(r['data']['status'] in ('needs_review','stale'),'proposal_terminal','Proposal already resolved.',409)
        d=r['data']
        if b['decision']=='reject':
            d.update(status='rejected',reviewed_by=a['id']);return {'proposal':self._save(c,s['id'],r,d)}
        require(d['status']=='needs_review' and d['policy_version']==s['policy_version'],'stale_proposal','Refresh and review the proposal before accepting.',409)
        if d['proposal_kind']=='canvas':
            # Validated again: an arrow end or a section member may have been
            # removed since it was proposed, and an accepted item must satisfy
            # the rules a hand-made one does at the moment it is made.
            data=self._canvas_data(c,s['id'],d['canvas_kind'],d['canvas_data'])
            item=self._new(c,s['id'],'item',{'item_kind':d['canvas_kind'],**data,'origin':d['origin'],
                'author_id':d['author_id'],'status':'accepted','proposal_id':r['id'],'accepted_by':a['id'],
                'last_editor':a['id'],'created_at':self.clock()})
            self._carry_position(c,s,a,r,item)
            d.update(status='accepted',reviewed_by=a['id'],item_id=item['id'])
            return {'proposal':self._save(c,s['id'],r,d),'item':item}
        self._refs(c,s['id'],d['refs'])
        if 'region_id' in d:
            self._region_ref(c,s['id'],d['region_id'],d['refs'])
            require(d.get('reading_status')!='unreadable','unreadable_content','Transcribe unreadable content before acceptance.',409)
        if d['proposal_kind']=='placement':
            # An accepted arrangement is written onto the items it names and
            # creates no record of its own. A placement record that can
            # contradict another placement record is exactly what made "where is
            # this item" unanswerable, and two of them were both valid.
            placed=[self._write_position(c,s['id'],p['id'],p['x'],p['y'],True,a['id']) for p in d['positions']]
            d.update(status='accepted',reviewed_by=a['id'])
            return {'proposal':self._save(c,s['id'],r,d),'placements':placed}
        item_data={'item_kind':d['proposal_kind'],'text':d['text'],'refs':deepcopy(d['refs']),'origin':d['origin'],
            'status':'accepted','proposal_id':r['id'],'accepted_by':a['id'],'last_editor':a['id'],'created_at':self.clock()}
        for key in ('form','region_id','reading_status','provider','model','synthetic','confidence','colour',
                    'summary_title','summary_detail','summary_category','summary_importance','summary_batch_id','summary_order'):
            if key in d:item_data[key]=deepcopy(d[key])
        item=self._new(c,s['id'],'item',item_data)
        # A proposal a person already dragged keeps where they put it. Accepting
        # is itself a placing act under F3.4, so the item is hand-placed either
        # way, and the proposal leaves the board.
        self._carry_position(c,s,a,r,item)
        d.update(status='accepted',reviewed_by=a['id'],item_id=item['id'])
        return {'proposal':self._save(c,s['id'],r,d),'item':item}

    def _carry_position(self,c,s,a,proposal,item):
        """Move a proposal's position, size included, onto the item accepting it made."""
        carried=self._position(c,s['id'],proposal['id'])
        if carried is not None:
            self._write_position(c,s['id'],item['id'],carried['x'],carried['y'],True,a['id'],(carried['w'],carried['h']))
            c.execute('DELETE FROM positions WHERE session_id=? AND record_id=?',(s['id'],proposal['id']))
            self._track(c,{'id':proposal['id'],'revision':0},'position')

    def _item_edit(self,c,s,a,b):
        fields(b,('item_id','expected_revision','text','refs'));self._facilitator(a)
        r=self._get(c,s['id'],b['item_id'],'item');self._expected(r,b['expected_revision'])
        require(r['data']['status'] not in ('undone','superseded'),'item_undone','An undone item cannot be edited.',409)
        # A shape has no text and refs to edit, and writing them onto it would
        # turn a drawing into something shaped like a note.
        require(r['data'].get('item_kind') not in self.CANVAS_KINDS,'invalid_target','Change a canvas object with canvas.update.')
        refs=self._refs(c,s['id'],b['refs'])
        require(not any(ref['id']==r['id'] for ref in refs),'cyclic_reference','An item cannot reference itself.')
        self._no_cycle(c,s['id'],r['id'],refs)
        if r['data']['item_kind'] in ('placement','relationship'):
            require(refs==r['data']['refs'],'new_structure_required','Create a new structure proposal when targets change.',409)
        d=r['data'];d.update(text=text(b['text'],'text'),refs=deepcopy(refs),status='accepted',last_editor=a['id'])
        if 'region_id' in d:
            self._region_ref(c,s['id'],d['region_id'],refs)
            self._human_reading(d)
        return {'item':self._save(c,s['id'],r,d),'invalidated':self._invalidate(c,s['id'],r['id'])}

    def _no_cycle(self,c,sid,rid,refs):
        todo=[r['id'] for r in refs];seen=set()
        while todo:
            current=todo.pop()
            require(current!=rid,'cyclic_reference','References would create a cycle.')
            if current in seen:continue
            seen.add(current);item=self._get(c,sid,current)
            todo.extend(r['id'] for r in item['data'].get('refs',[]))

    def _undo(self,c,s,a,b):
        fields(b,('item_id','expected_revision','restore_revision'));self._facilitator(a)
        r=self._get(c,s['id'],b['item_id'],'item');self._expected(r,b['expected_revision'])
        target=integer(b['restore_revision'],'restore_revision',0,r['revision']-1)
        if target==0:
            d=deepcopy(r['data']);d.update(status='undone',last_editor=a['id'])
        else:
            old=c.execute('SELECT data FROM versions WHERE session_id=? AND record_id=? AND revision=?',(s['id'],r['id'],target)).fetchone()
            require(old is not None,'not_found','Revision not found.',404);d=json.loads(old['data'])
            # A canvas object has no refs: what it points at is named by id and
            # drawn only while it exists, so there is no dependency to recheck.
            if d.get('item_kind') not in self.CANVAS_KINDS:
                self._refs(c,s['id'],d['refs']);self._no_cycle(c,s['id'],r['id'],d['refs'])
            d['last_editor']=a['id']
        d['restored_from_revision']=target
        return {'item':self._save(c,s['id'],r,d),'invalidated':self._invalidate(c,s['id'],r['id'])}

    def _export(self,c,s,a,b,persist=True):
        fields(b,('include_unresolved',));self._facilitator(a)
        require(type(b['include_unresolved']) is bool,'invalid_boolean','include_unresolved must be true or false.')
        records=self._list(c,s['id']);items=[r for r in records if r['kind']=='item' and r['data']['status'] not in ('undone','superseded')]
        proposals=[r for r in records if r['kind']=='proposal' and r['data']['status'] in ('needs_review','stale')]
        included=[r for r in items if r['data']['status']=='accepted']
        unresolved=[r for r in items if r['data']['status']=='stale']+proposals
        exported=included+(unresolved if b['include_unresolved'] else [])
        manifest={'session_id':s['id'],'session_title':s['title'],'snapshot_seq':s['seq'],'policy_version':s['policy_version'],
            'created_at':self.clock(),'included':[{k:r[k] for k in ('id','kind','revision')} for r in exported],
            'unresolved_count':len(unresolved),'included_unresolved':b['include_unresolved'],
            'omitted_ids':[] if b['include_unresolved'] else [r['id'] for r in unresolved],
            'source_media_included':False,'source_evidence_included':False,'references_require_session':True,
            'format_version':1,'release_kind':'output_only','output_readable_offline':True,
            'evidence_availability':'Source references are identifiers, not bundled evidence; they stop resolving after session deletion.',
            'redaction_applied':False,
            'audience':'internal review; content has not been anonymized',
            'boundary':'Downloaded copies are outside service deletion control.'}
        # Escape HTML and Markdown punctuation; preserve visible labels in plain Markdown renderers.
        def safe(value):
            value=value.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
            for char in '\\`*_{}[]()#+-.!|':value=value.replace(char,'\\'+char)
            return value
        lines=['# Session export','',safe(s['title']),'',f"Snapshot sequence: {s['seq']}",
               f"Unresolved records: {len(unresolved)}; included: {b['include_unresolved']}",'',
               'Internal review artifact. Content has not been anonymized. Source evidence is excluded; references require the retained server session.','']
        for r in exported:
            d=r['data'];lines.extend([f"## {r['id']} · revision {r['revision']}",
                f"State: {'automatically_applied' if d.get('automatic') else d['status']} · Origin: {d['origin']} · Kind: {d.get('item_kind',d.get('canvas_kind',d.get('proposal_kind')))}",'',
                safe(self._export_text(d)),'',f"Source references: {encode(d.get('refs',[]))}",''])
        lines.append(manifest['boundary'])
        data={'manifest':manifest,'records':exported,'markdown':'\n'.join(lines)}
        return self._new(c,s['id'],'export',data) if persist else data

    @staticmethod
    def _export_text(d):
        """The words a record carries: a note's text, or a canvas object's text, title or label."""
        if d.get('summary_detail'):
            heading=d.get('text','')
            edited=heading and heading!=d.get('summary_title',heading)
            return (heading+'\n\n' if edited else '')+d['summary_detail']
        own=d.get('canvas_data',d)
        for key in ('text','title','label'):
            if type(own.get(key)) is str and own[key]:return own[key]
        return ''

    def export_snapshot(self,sid,token,body):
        """A consistent download without allocating durable export/retry records."""
        self.sweep()
        with self.db.transaction() as c:
            s,a=self._auth(c,sid,token);self._facilitator(a)
            return self._export(c,s,a,body,persist=False)

    @staticmethod
    def _public(record):
        r=deepcopy(record)
        r['data'].pop('base64',None)
        return r

    def snapshot(self,sid,token):
        self.sweep()
        with self.db.transaction() as c:
            s,a=self._auth(c,sid,token,deleted=True)
            if s['state']=='deleted':return {'session_id':sid,'state':'deleted','deleted_at':s['deleted_at'],'content_available':False}
            s.pop('deletion_hash',None)
            s['poll_ai']=self._poll_capability()
            s['command_ai']=self._document_capability()
            if self.summary_model is not None:s['summary_ai']={'available':True,'local':getattr(self.summary_model,'local',True),'provider':self.summary_model.name}
            s['timezone']=self._session_timezone(c,sid)
            s['wakeword_available']=self.wakewords.factory is not None
            if self.automatic_workspace:s['automatic_workspace']=True
            members=[dict(r) for r in c.execute('SELECT id,name,role,consent_version,agreed_at,withdrawn_at FROM actors WHERE session_id=? ORDER BY rowid',(sid,))]
            positions=self._positions(c,sid)
            records=[]
            for record in self._list(c,sid):
                public=self._public(record)
                if record['kind']=='export':public['data']={'manifest':record['data']['manifest']}
                public['position']=positions.get(record['id'])
                records.append(public)
            # Sent here, where the client is receiving the whole session anyway,
            # and not in a delta. See _board_order.
            return {'session':s,'actor_id':a['id'],'members':members,'next_control_sequence':a['control_seq']+1,
                    'records':records,'board_order':self._board_order(positions)}

    def delta(self,sid,token,since_seq):
        """The records that changed since a cursor, and nothing else.

        Built from the events themselves, so it reports exactly what the event
        stream reported, and both are read in one transaction: the records and
        the cursor describe the same point, never a mix of two.

        A cursor ahead of the session is refused rather than answered with an
        empty page, because that is a client holding state from a session that
        no longer exists, and an empty page would look like "nothing changed".

        When more than half the session changed, the answer is
        `resync_required` and no records. That is a normal answer, not an error:
        the client takes a snapshot and uses the seq that snapshot reports.
        """
        integer(since_seq,'since_seq',0)
        self.sweep()
        with self.db.transaction() as c:
            s,a=self._auth(c,sid,token)
            require(since_seq<=s['seq'],'cursor_ahead',
                    'That cursor is ahead of this session. Take a full snapshot.',409,current_seq=s['seq'])
            s.pop('deletion_hash',None)
            s['poll_ai']=self._poll_capability()
            s['command_ai']=self._document_capability()
            if self.summary_model is not None:s['summary_ai']={'available':True,'local':getattr(self.summary_model,'local',True),'provider':self.summary_model.name}
            s['timezone']=self._session_timezone(c,sid)
            s['wakeword_available']=self.wakewords.factory is not None
            if self.automatic_workspace:s['automatic_workspace']=True
            wanted=set()
            for row in c.execute('SELECT data FROM events WHERE session_id=? AND seq>? ORDER BY seq',
                                 (sid,since_seq)).fetchall():
                payload=json.loads(row['data'])
                if 'records' not in payload:
                    wanted.update(r['id'] for r in self._list(c,sid))
                else:wanted.update(r['id'] for r in payload['records'])
            # A cascade can name most of the session: a pause stales every
            # pending proposal, and a correction can stale a long dependency
            # chain. Past halfway there is nothing left to save. The snapshot is
            # then at most twice the bytes, in one request, with no merge to get
            # wrong, so the delta stops being the cheap path it exists to be and
            # says so instead of returning most of the session record by record.
            total=c.execute('SELECT count(*) FROM records WHERE session_id=?',(sid,)).fetchone()[0]
            if wanted and len(wanted)*2>total:
                return {'session':s,'actor_id':a['id'],'since_seq':since_seq,'current_seq':s['seq'],
                        'resync_required':True,'changed_records':len(wanted),'session_records':total,
                        'reason':'Too much of the session changed to be worth sending as a delta. '
                                 'Take a full snapshot and use the seq it reports as the new cursor.'}
            positions=self._positions(c,sid)
            records=[]
            for record in self._list(c,sid):
                if record['id'] not in wanted:continue
                public=self._public(record)
                if record['kind']=='export':public['data']={'manifest':record['data']['manifest']}
                public['position']=positions.get(record['id'])
                records.append(public)
            members=[dict(r) for r in c.execute('SELECT id,name,role,consent_version,agreed_at,withdrawn_at FROM actors WHERE session_id=? ORDER BY rowid',(sid,))]
            # No board_order here, deliberately. It is a pure function of the
            # positions the client already holds, and sending it made the delta
            # grow with the board: measured at 8183 B per client on a 320-item
            # board against a 5 KB budget, for a one-word edit. A client keeps
            # its own order with the same key, and every field that key needs
            # arrives on each record's position.
            return {'session':s,'actor_id':a['id'],'members':members,'next_control_sequence':a['control_seq']+1,
                    'records':records,'since_seq':since_seq,'current_seq':s['seq']}

    def record(self,sid,token,rid,revision=None):
        self.sweep()
        with self.db.transaction() as c:
            _,a=self._auth(c,sid,token);r=self._get(c,sid,rid)
            if r['kind']=='export':self._facilitator(a)
            if revision is not None:
                integer(revision,'revision')
                row=c.execute('SELECT data FROM versions WHERE session_id=? AND record_id=? AND revision=?',(sid,rid,revision)).fetchone()
                require(row is not None,'not_found','Revision not found.',404)
                r['revision']=revision;r['data']=json.loads(row['data'])
            public=self._public(r)
            # Position is not versioned, so a historical revision still reports
            # where the record is now. Restoring old text never moves anything.
            public['position']=self._position(c,sid,rid)
            return public

    def media(self,sid,token,rid):
        self.sweep()
        with self.db.transaction() as c:
            _,a=self._auth(c,sid,token);r=self._get(c,sid,rid,'source')
            require(r['data']['type']=='image','not_found','Source has no image.',404)
            require(a['role']=='facilitator' or (a['role']=='participant' and r['data']['author_id']==a['id']),
                    'forbidden','Only an active uploader or facilitator can read image evidence.',403)
            row=self._media_row(c,sid,r)
            return row['mime'],row['payload']

    @staticmethod
    def _media_row(c,sid,source):
        row=c.execute('SELECT * FROM media WHERE session_id=? AND id=?',(sid,source['data'].get('media_id'))).fetchone()
        require(row is not None,'media_unavailable','Image evidence is unavailable; upload a new source.',410)
        return row

    def crop(self,sid,token,rid,revision,region_id):
        ident(region_id);self.sweep()
        with self.db.transaction() as c:
            s,a=self._auth(c,sid,token);source=self._get(c,sid,rid,'source');self._expected(source,revision)
            require(a['role']=='facilitator' or (a['role']=='participant' and source['data']['author_id']==a['id']),
                    'forbidden','Only an active uploader or facilitator can read crop evidence.',403)
            region=next((r for r in source['data'].get('regions',[]) if r['id']==region_id),None)
            require(region is not None,'not_found','Region is not present in this source revision.',404)
            raw=self._media_row(c,sid,source)['payload'];box=region['box']
        result=crop_pixels(raw,box)
        with self.db.transaction() as c:
            _,current_actor=self._auth(c,sid,token);current=self._get(c,sid,rid,'source');self._expected(current,revision)
            require(current_actor['role']=='facilitator' or (current_actor['role']=='participant' and current['data']['author_id']==current_actor['id']),
                    'forbidden','Image evidence access changed.',403)
        return 'image/png',result

    def events(self,sid,token,after=0):
        integer(after,'after',0)
        self.sweep()
        with self.db.transaction() as c:
            s,a=self._auth(c,sid,token)
            rows=c.execute('SELECT seq,type,actor_id,created,data FROM events WHERE session_id=? AND seq>? ORDER BY seq LIMIT 200',(sid,after)).fetchall()
            events=[{**dict(row),'data':json.loads(row['data'])} for row in rows]
            return {'events':events,'next_after':events[-1]['seq'] if events else after,'current_seq':s['seq'],'has_more':bool(events and events[-1]['seq']<s['seq'])}

    def delete_session(self,sid,token):
        self.sweep()
        with self.db.transaction() as c:
            s,a=self._auth(c,sid,token,deleted=True);self._facilitator(a)
            if s['state']=='deleted':return {'session_id':sid,'state':'deleted','deleted_at':s['deleted_at'],'replayed':True}
            self._purge(c,s,digest(token))
            result={'session_id':sid,'state':'deleted','deleted_at':self.clock(),'replayed':False,
                    'boundary':'Live database content and retained completion results purged. Downloaded copies and external backups are not controlled.'}
        self._clear_pending(sid)
        return result

    def _clear_pending(self,sid):
        with self.pending_lock:
            for jid,ticket in list(self.executions.items()):
                if ticket['sid']==sid:
                    ticket['revoked']=True;ticket['cancel_event'].set();self.executions.pop(jid,None)
            for jid,args in list(self.pending_completions.items()):
                if args[0]['id']==sid:self.pending_completions.pop(jid,None)

    def _purge(self,c,s,receipt_hash=None):
        self.wakewords.invalidate(s['id'])
        if receipt_hash is None:
            row=c.execute("SELECT token_hash FROM actors WHERE session_id=? AND role='facilitator' ORDER BY rowid LIMIT 1",(s['id'],)).fetchone()
            receipt_hash=row['token_hash'] if row else ''
        for table in ('requests','control_requests','events','versions','positions','records','actors','invitations','media'):
            c.execute(f'DELETE FROM {table} WHERE session_id=?',(s['id'],))
            require(c.execute(f'SELECT count(*) FROM {table} WHERE session_id=?',(s['id'],)).fetchone()[0]==0,
                    'purge_failed','Store purge verification failed.',500)
        c.execute("UPDATE sessions SET title='',state='deleted',seq=0,policy_version=policy_version+1,deletion_hash=?,deleted_at=? WHERE id=?",
                  (receipt_hash,self.clock(),s['id']))

    def sweep(self):
        self.wakewords.expire()
        with self.db.transaction() as c:
            ids=[r['id'] for r in c.execute("SELECT id FROM sessions WHERE state!='deleted'")]
        for sid in ids:
            try:
                with self.db.transaction() as c:
                    row=c.execute('SELECT * FROM sessions WHERE id=?',(sid,)).fetchone()
                    if row is None or row['state']=='deleted':continue
                    s=dict(row);now=self.clock()
                    if s['expires']<=now:
                        self._purge(c,s)
                    elif s['state']=='active' and s['lease']<=now:
                        self._stop_capture(c,s)
                        self._event(c,sid,'system','session.lease_expired',{})
                    if s['expires']>now:
                        for job in self._list(c,sid,'job'):
                            if job['data']['status'] in ('queued','running') and job['data']['deadline']<=now:
                                data=job['data'];data.update(status='failed',error='deadline_exceeded')
                                self._save(c,sid,job,data)
                                self._event(c,sid,'system','job.failed',{'job_id':job['id'],'code':'deadline_exceeded'})
                self.maintenance_failures.pop(sid,None)
                if s['expires']<=now:self._clear_pending(sid)
                elif s['state']=='active' and s['lease']<=now:self._cancel_executions(sid)
            except (sqlite3.Error,Problem):
                # One expired session cannot stop unrelated reads or jobs.
                # _auth independently denies expired content while purge retries.
                self.maintenance_failures[sid]='maintenance_retry_pending'

    def recover_jobs(self):
        """Call once at single-process startup, never from a second competing server."""
        # Preserve claim uncertainty before expiry/lease cleanup makes it terminal.
        with self.db.transaction() as c:
            for row in c.execute("SELECT id FROM sessions WHERE state!='deleted'").fetchall():
                sid=row['id']
                for r in self._list(c,sid,'job'):
                    d=r['data']
                    if d['status']=='running':
                        d['status']='failed'
                        d.update(error='interrupted_unknown_outcome',execution_outcome='unknown',
                                 usage_status='unknown',usage=None,retry_requires_acknowledgement=True)
                        self._save(c,sid,r,d)
                        self._event(c,sid,'system','job.recovered',{'job_id':r['id']})
        self.sweep()

    def run_one_job(self):
        """Claim in a transaction; never hold its lock while an adapter is running."""
        self.sweep()
        with self.pending_lock:pending=list(self.pending_completions.items())
        for jid,args in pending:
            try:
                self._complete_job(*args)
                with self.pending_lock:self.pending_completions.pop(jid,None)
            except sqlite3.Error:pass
        with self.pending_lock:
            if len(self.pending_completions)>=8:return False
            pending_sessions={args[0]['id'] for args in self.pending_completions.values()}
        selected=None
        # Delete releases its database transaction before taking this lock.
        with self.pending_lock,self.db.transaction() as c:
            sessions=c.execute("SELECT * FROM sessions WHERE state='active' AND expires>? AND lease>? ORDER BY created,id",(self.clock(),self.clock())).fetchall()
            ids=[row['id'] for row in sessions]
            if self.last_claim_session in ids:
                split=ids.index(self.last_claim_session)+1;sessions=sessions[split:]+sessions[:split]
            for sr in sessions:
                s=dict(sr)
                if s['id'] in pending_sessions:continue
                for r in self._list(c,s['id'],'job'):
                    d=r['data']
                    if d['status']!='queued':continue
                    if d['deadline']<=self.clock():
                        d.update(status='failed',error='deadline_exceeded');self._save(c,s['id'],r,d)
                        self._event(c,s['id'],'system','job.failed',{'job_id':r['id'],'code':'deadline_exceeded'});continue
                    if d['policy_version']!=s['policy_version']:
                        d.update(status='cancelled',error='policy_changed');self._save(c,s['id'],r,d);continue
                    try:self._refs(c,s['id'],d['refs'])
                    except Problem:
                        d.update(status='cancelled',error='source_changed');self._save(c,s['id'],r,d);continue
                    source=self._get(c,s['id'],d['refs'][0]['id'],'source')
                    d.update(status='running',attempts=d['attempts']+1,started_at=self.clock(),
                             execution_outcome='unknown',usage_status='unknown',usage=None)
                    job=self._save(c,s['id'],r,d)
                    self._event(c,s['id'],'system','job.started',{'job_id':r['id']})
                    ticket={'sid':s['id'],'author_id':d['author_id'],'revoked':False,'cancel_event':threading.Event()};self.executions[job['id']]=ticket
                    selected=(s,job,source,self._media_row(c,s['id'],source)['payload'],ticket);self.last_claim_session=s['id'];break
                if selected:break
        if not selected:return False
        s,job,source,media_raw,ticket=selected;started=time.monotonic();output=None;failure=None
        try:
            require(job['data']['adapter']==self.extractor.name,'adapter_changed','Queued adapter is no longer configured.',409)
            extractor=self.extractor
            if isinstance(extractor,IsolatedExtractor):
                extractor=IsolatedExtractor(extractor.name,extractor.module,extractor.factory,extractor.configuration,
                    timeout_seconds=max(.001,min(extractor.timeout_seconds,job['data']['deadline']-self.clock())),cancel_event=ticket['cancel_event'])
            output=extractor.extract(ExtractionInput(source['id'],source['revision'],source['data']['mime'],
                media_raw,tuple(deepcopy(source['data']['regions']))))
            require(output.provider==self.extractor.name and type(output.synthetic) is bool,'invalid_adapter_output','Adapter metadata is inconsistent.')
            text(output.model,'model',100);require(type(output.usage) is dict,'invalid_adapter_output','Usage must be an object.')
            fields(output.usage,(),('input_units','output_units','cost','currency'))
            for key in ('input_units','output_units','cost'):
                value=output.usage.get(key)
                require(value is None or (type(value) in (int,float) and math.isfinite(value) and value>=0),
                        'invalid_adapter_output','Usage numbers must be finite and nonnegative, or null.')
            currency=output.usage.get('currency')
            require(currency is None or (type(currency) is str and len(currency)==3 and currency.isalpha()),
                    'invalid_adapter_output','Currency must be a three-letter code or null.')
            require(output.usage.get('cost') is None or currency is not None,'invalid_adapter_output','Reported cost needs a currency.')
            require(type(output.notes) in (tuple,list) and len(output.notes)<=60,'invalid_adapter_output','Invalid notes.')
            region_ids={r['id'] for r in source['data']['regions']};returned=set()
            for note in output.notes:
                automatic=source['data'].get('detect_notes') and not source['data']['regions']
                fields(note,('region_id','text','status'),('confidence','colour','box') if automatic else ('confidence','colour'))
                if automatic:
                    regions([{'id':note['region_id'],'box':note.get('box')}])
                require((automatic or note['region_id'] in region_ids) and note['region_id'] not in returned,'invalid_adapter_output','Adapter region identities do not match the request.')
                require(note['status'] in ('readable','unreadable'),'invalid_adapter_output','Unknown reading status.')
                # F02. Both are optional and nullable, and neither is acceptance
                # authority: a note the model is sure of is still provisional.
                # Confidence is on the named model's own scale, so it is only
                # comparable within one provider and model.
                confidence=note.get('confidence')
                require(confidence is None or (type(confidence) in (int,float) and math.isfinite(confidence) and 0<=confidence<=1),
                        'invalid_adapter_output','Confidence must be a number from 0 to 1, or null.')
                # A colour without a space and a source is a guess nobody can
                # check, so the shape is closed: sRGB hex, and who said so.
                colour=note.get('colour')
                if colour is not None:
                    fields(colour,('space','hex','source'))
                    require(colour['space']=='srgb' and type(colour['hex']) is str and re.fullmatch('#[0-9a-f]{6}',colour['hex']) is not None
                            and colour['source'] in ('model_reported','pixel_measured'),
                            'invalid_adapter_output','Colour must be lowercase sRGB hex with a named source, or null.')
                text(note['text'],'text',empty=note['status']=='unreadable');returned.add(note['region_id'])
            require((source['data'].get('detect_notes') and not region_ids) or returned==region_ids,'invalid_adapter_output','Adapter omitted regions.')
            encode(output.usage)
        except IsolatedFailure as error:
            output=None;failure=str(error) if str(error) in ('adapter_timeout','adapter_cancelled') else 'adapter_failed'
        except Exception:
            # Provider exception text may contain source material or keys. Store only a safe category.
            output=None;failure='adapter_failed'
        args=(s,job,output,failure,started)
        try:self._complete_job(*args)
        except sqlite3.Error:
            # Retain bounded validated output, not original media. A transient
            # completion-store failure must not repeat the extraction call.
            with self.pending_lock:
                if not ticket['revoked'] and s['expires']>self.clock():
                    self.pending_completions[job['id']]=args
        finally:
            with self.pending_lock:self.executions.pop(job['id'],None)
        return True

    def _complete_job(self,s,job,output,failure,started):
        with self.db.transaction() as c:
            sr=c.execute('SELECT * FROM sessions WHERE id=?',(s['id'],)).fetchone()
            if sr is None or sr['state']=='deleted':return True
            current=self._get(c,s['id'],job['id'],'job');d=current['data']
            outcome={'execution_outcome':'completed' if output is not None else 'unknown',
                     'usage_status':'reported' if output is not None and output.usage.get('cost') is not None else 'unknown',
                     'usage':deepcopy(output.usage) if output is not None else None}
            if d['status']!='running':
                # Cancellation discards proposals, not knowledge of an incurred charge.
                if d['status'] in ('failed','cancelled') and d['attempts']==job['data']['attempts'] and any(d.get(k)!=v for k,v in outcome.items()):
                    d.update(outcome);self._save(c,s['id'],current,d)
                    self._event(c,s['id'],'system','job.outcome_recorded',{'job_id':job['id']})
                return True
            d.update(outcome)
            c.execute('SAVEPOINT completion')
            if sr['state']!='active' or sr['policy_version']!=d['policy_version'] or sr['expires']<=self.clock() or sr['lease']<=self.clock():
                d.update(status='cancelled',error='policy_changed')
            elif d['deadline']<=self.clock():
                d.update(status='failed',error='deadline_exceeded')
            elif failure:
                d.update(status='failed',error=failure)
            else:
                try:self._refs(c,s['id'],d['refs'])
                except Problem:d.update(status='cancelled',error='source_changed')
                else:
                    author=c.execute('SELECT * FROM actors WHERE session_id=? AND id=?',(s['id'],d['author_id'])).fetchone()
                    if author is None or author['role'] not in ('participant','facilitator'):
                        d.update(status='cancelled',error='permission_changed')
                    elif c.execute('SELECT count(*) FROM records WHERE session_id=?',(s['id'],)).fetchone()[0]+len(output.notes)*(2 if self.automatic_workspace else 1)>self.MAX_RECORDS:
                        d.update(status='failed',error='record_capacity')
                    else:
                        proposals=[]
                        source=self._get(c,s['id'],d['refs'][0]['id'],'source')
                        if source['data'].get('detect_notes') and not source['data']['regions']:
                            source=self._save(c,s['id'],source,{**source['data'],
                                'regions':[{'id':n['region_id'],'box':n['box']} for n in output.notes]})
                            d['refs']=[{'id':source['id'],'revision':source['revision']}]
                        for note in output.notes:
                            proposal=self._proposal(c,dict(sr),dict(author),'content',note['text'],d['refs'],
                                origin='fixture' if output.synthetic else 'model',extra={'region_id':note['region_id'],'reading_status':note['status'],
                                'provider':output.provider,'model':output.model,'synthetic':output.synthetic,
                                'confidence':note.get('confidence'),'colour':deepcopy(note.get('colour'))})
                            proposals.append(proposal['id'])
                        d.update(status='succeeded',error=None,proposal_ids=proposals,provider=output.provider,model=output.model,
                                 synthetic=output.synthetic,usage=output.usage)
            d['duration_ms']=round((time.monotonic()-started)*1000,2)
            self._save(c,s['id'],current,d)
            self._event(c,s['id'],'system','job.'+d['status'],{'job_id':job['id'],'code':d.get('error')})
            if d['status']=='succeeded':
                try:self._budget(c,s['id'])
                except Problem:
                    c.execute('ROLLBACK TO completion')
                    current=self._get(c,s['id'],job['id'],'job');failed=current['data']
                    failed.update(status='failed',error='storage_capacity',duration_ms=round((time.monotonic()-started)*1000,2),**outcome)
                    self._save(c,s['id'],current,failed)
                    self._event(c,s['id'],'system','job.failed',{'job_id':job['id'],'code':'storage_capacity'})
            c.execute('RELEASE completion')
        return True
