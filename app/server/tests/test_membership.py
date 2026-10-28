"""Independent joining and lifecycle transactions, including refused transitions."""
import concurrent.futures
import json
import secrets
import shutil
import threading
import unittest
from pathlib import Path
from genai_server.service import Service
from genai_server.validation import Problem


class MembershipTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1] / '.local/tests'
        root.mkdir(parents=True, exist_ok=True)
        directory = root / secrets.token_hex(16)
        directory.mkdir()
        assert directory.resolve().is_relative_to(root.resolve())
        self.addCleanup(shutil.rmtree, directory)
        self.now = 1000.0
        self.service = Service(directory / 'state.sqlite3', clock=lambda: self.now)
        self.sid, self.token = secrets.token_hex(16), secrets.token_urlsafe(32)
        self.service.create_session(dict(session_id=self.sid, owner_token=self.token, owner_name='Host', title='Test'))

    def snap(self):
        return self.service.snapshot(self.sid, self.token)

    def command(self, op, payload=None, token=None, key=None):
        payload=dict(payload or {})
        if op=='session.activate':payload.setdefault('expected_session_revision',self.snap()['session']['revision'])
        key=key or secrets.token_hex(16);sequence=None
        if op in self.service.CONTROL_COMMANDS:
            if not hasattr(self,'control_intents'):self.control_intents={}
            sequence=self.control_intents.setdefault(key,self.service.snapshot(self.sid,token or self.token)['next_control_sequence'])
        return self.service.command(self.sid, token or self.token, key, op, payload or {},sequence)['result']

    def invite(self, role='participant', expires_seconds=600):
        capability = secrets.token_urlsafe(32)
        result = self.command('participant.invite', dict(invitation=capability, role=role,
            expires_seconds=expires_seconds, expected_roster_revision=self.snap()['session']['roster_revision']))
        return capability, result

    def join(self, invitation, token=None, **changes):
        body = dict(invitation=invitation, token=token or secrets.token_urlsafe(32), name='Guest', policy_version=1)
        body.update(changes)
        return body, self.service.join(self.sid, body)

    def refuses(self, code, call):
        try:call()
        except Exception as caught:
            self.assertIsInstance(caught,Problem,'Domain refusal must have an API error contract')
            self.assertEqual(code,caught.code)
        else:self.fail('Expected refusal '+code)

    def active(self):
        self.command('consent.acknowledge', {'policy_version': 1})
        self.command('session.activate', {'policy_version': 1})

    def test_legacy_invitation_credential_payload_is_rejected(self):
        self.refuses('missing_fields', lambda: self.command('participant.invite', {'name':'Guest','token':secrets.token_urlsafe(32)}))

    def test_invitation_and_join_preserve_active_room(self):
        self.active()
        before = self.snap()
        invitation, _ = self.invite()
        self.assertEqual(1, len(self.snap()['members']))
        body, joined = self.join(invitation)
        after = self.snap()
        self.assertEqual('active', after['session']['state'])
        self.assertEqual(before['session']['policy_version'], after['session']['policy_version'])
        self.assertEqual(before['members'][0], after['members'][0])
        self.assertEqual(joined['actor_id'], self.service.snapshot(self.sid, body['token'])['actor_id'])

    def test_expired_invitation_creates_no_member(self):
        invitation, _ = self.invite(expires_seconds=60)
        self.now += 61
        self.refuses('invitation_expired', lambda: self.join(invitation))
        self.assertEqual(1, len(self.snap()['members']))

    def test_revoked_invitation_creates_no_member(self):
        invitation, issued = self.invite()
        self.command('invitation.revoke', {'invitation_id': issued['invitation_id'],
            'expected_roster_revision': self.snap()['session']['roster_revision']})
        self.refuses('invitation_revoked', lambda: self.join(invitation))

    def test_join_requires_current_policy(self):
        invitation, _ = self.invite()
        self.refuses('policy_changed', lambda: self.join(invitation, policy_version=2))
        self.assertEqual(1, len(self.snap()['members']))

    def test_invitation_is_scoped_to_its_session(self):
        invitation,_=self.invite();other=secrets.token_hex(16)
        self.service.create_session({'session_id':other,'owner_token':secrets.token_urlsafe(32),'owner_name':'Other','title':'Other'})
        self.refuses('invalid_invitation',lambda:self.service.join(other,{'invitation':invitation,'token':secrets.token_urlsafe(32),'name':'Guest','policy_version':1}))

    def test_join_retry_is_bound_to_exact_credential_and_payload(self):
        invitation, _ = self.invite()
        body, first = self.join(invitation)
        self.assertEqual(first['actor_id'], self.service.join(self.sid, body)['actor_id'])
        self.refuses('invitation_consumed', lambda: self.join(invitation))
        self.refuses('idempotency_conflict', lambda: self.service.join(self.sid, {**body,'name':'Changed'}))
        self.assertEqual(2, len(self.snap()['members']))

    def test_concurrent_redemption_has_one_member(self):
        invitation, _ = self.invite()
        barrier = threading.Barrier(2)
        def redeem(_):
            barrier.wait()
            try:
                return self.join(invitation)[1]['actor_id']
            except Problem as problem:
                return problem.code
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            outcomes = list(pool.map(redeem, range(2)))
        self.assertEqual(1, outcomes.count('invitation_consumed'))
        self.assertEqual(2, len(self.snap()['members']))

    def test_secret_capabilities_are_not_persisted_in_plaintext(self):
        invitation, _ = self.invite()
        body, _ = self.join(invitation)
        with self.service.db.transaction() as connection:
            dump = '\n'.join(connection.iterdump())
        for secret in (invitation, body['token'], self.token):
            self.assertNotIn(secret, dump)
            self.assertNotIn(secret, json.dumps(self.snap()))

    def test_removal_revokes_cached_commands_and_join_replay(self):
        invitation, _ = self.invite()
        body, joined = self.join(invitation)
        key = secrets.token_hex(16)
        self.command('consent.acknowledge', {'policy_version':1}, body['token'], key)
        self.command('participant.remove', {'actor_id':joined['actor_id'],
            'expected_roster_revision':self.snap()['session']['roster_revision']})
        self.refuses('unauthorized', lambda:self.service.snapshot(self.sid, body['token']))
        self.refuses('unauthorized', lambda:self.command('consent.acknowledge', {'policy_version':1}, body['token'], key))
        self.refuses('membership_removed', lambda:self.service.join(self.sid, body))
        for call in (
            lambda:self.service.record(self.sid,body['token'],'record_001'),
            lambda:self.service.media(self.sid,body['token'],'source_001'),
            lambda:self.service.crop(self.sid,body['token'],'source_001',1,'region_001'),
            lambda:self.service.events(self.sid,body['token'],0),
            lambda:self.service.export_snapshot(self.sid,body['token'],{'include_unresolved':True}),
        ):self.refuses('unauthorized',call)

    def test_last_facilitator_cannot_be_removed(self):
        snapshot = self.snap()
        self.refuses('last_facilitator', lambda:self.command('participant.remove', {
            'actor_id':snapshot['actor_id'], 'expected_roster_revision':snapshot['session']['roster_revision']}))
        self.assertEqual(snapshot, self.snap())

    def test_stale_roster_action_has_no_effect(self):
        invitation, _ = self.invite()
        body, joined = self.join(invitation)
        revision = self.snap()['session']['roster_revision']
        self.command('participant.role', {'actor_id':joined['actor_id'],'role':'viewer','expected_roster_revision':revision})
        before = self.snap()
        self.refuses('stale_roster', lambda:self.command('participant.remove', {'actor_id':joined['actor_id'],'expected_roster_revision':revision}))
        self.assertEqual(before, self.snap())

    def test_concurrent_roster_writes_have_one_winner(self):
        invitation,_=self.invite();_,joined=self.join(invitation);revision=self.snap()['session']['roster_revision']
        barrier=threading.Barrier(2)
        def change(role):
            barrier.wait()
            try:return self.command('participant.role',{'actor_id':joined['actor_id'],'role':role,'expected_roster_revision':revision})['role']
            except Problem as problem:return problem.code
        with concurrent.futures.ThreadPoolExecutor(2) as pool:results=list(pool.map(change,('viewer','facilitator')))
        self.assertEqual(1,results.count('stale_roster'))

    def test_withdrawal_preserves_other_agreement_and_blocks_activation(self):
        self.active()
        invitation, _ = self.invite()
        body, _ = self.join(invitation)
        owner = self.snap()['members'][0]
        self.now += 1
        self.command('consent.withdraw', token=body['token'])
        self.assertEqual(owner, self.snap()['members'][0])
        self.assertEqual('paused', self.snap()['session']['state'])
        self.refuses('agreement_incomplete', lambda:self.command('session.activate', {'policy_version':1}))
        self.command('consent.acknowledge', {'policy_version':1}, body['token'])
        self.command('session.activate', {'policy_version':1})

    def test_lease_preserves_policy_and_proposals(self):
        self.active()
        proposal = self.command('source.text', {'text':'Keep this proposal'})['proposal']
        before = self.snap()
        self.now += 301
        self.service.sweep()
        after = self.snap()
        self.assertEqual(before['members'], after['members'])
        self.assertEqual(before['session']['policy_version'], after['session']['policy_version'])
        self.assertEqual({**proposal,'position':None}, self.service.record(self.sid, self.token, proposal['id']))
        self.assertEqual('paused', after['session']['state'])
        self.command('session.heartbeat')
        self.assertEqual('paused', self.snap()['session']['state'])

    def test_pause_noop_preserves_state_revision_and_event_cursor(self):
        self.active()
        self.command('session.pause')
        before = self.snap()
        self.command('session.pause')
        after=self.snap()
        for field in ('session','members','records'):self.assertEqual(before[field],after[field])

    def test_stale_close_cannot_end_changed_session(self):
        revision = self.snap()['session']['revision']
        self.active()
        self.refuses('stale_session', lambda:self.command('session.close', {'expected_session_revision':revision}))
        self.assertEqual('active', self.snap()['session']['state'])
