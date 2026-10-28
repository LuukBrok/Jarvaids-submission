import secrets
import unittest
import test_membership as helpers


class ControlTests(unittest.TestCase):
    setUp=helpers.MembershipTests.setUp
    command=helpers.MembershipTests.command
    active=helpers.MembershipTests.active
    snap=helpers.MembershipTests.snap
    refuses=helpers.MembershipTests.refuses

    def test_control_history_is_bounded_and_old_replay_is_refused(self):
        self.active();before=self.snap();key=secrets.token_hex(16)
        first=self.service.command(self.sid,self.token,key,'session.heartbeat',{},1)
        self.service.MAX_REQUESTS=0;self.service.MAX_SESSION_BYTES=0
        for sequence in range(2,1002):
            self.service.command(self.sid,self.token,secrets.token_hex(16),'session.heartbeat',{},sequence)
        with self.service.db.transaction() as c:
            self.assertEqual(128,c.execute('SELECT count(*) FROM control_requests').fetchone()[0])
            self.assertEqual(before['session']['seq'],c.execute('SELECT count(*) FROM events').fetchone()[0])
            self.assertEqual(0,c.execute('SELECT count(*) FROM versions').fetchone()[0])
        self.refuses('control_replay_expired',lambda:self.service.command(self.sid,self.token,key,'session.heartbeat',{},1))
        self.command('session.pause')
        self.command('session.close',{'expected_session_revision':self.snap()['session']['revision']})
        self.assertEqual('closed',self.snap()['session']['state'])

    def test_control_sequence_cannot_be_allocated_twice(self):
        key=secrets.token_hex(16)
        self.service.command(self.sid,self.token,key,'session.pause',{},1)
        self.refuses('control_sequence_conflict',lambda:self.service.command(self.sid,self.token,secrets.token_hex(16),'session.pause',{},1))
        self.assertTrue(self.service.command(self.sid,self.token,key,'session.pause',{},1)['replayed'])
        self.refuses('idempotency_conflict',lambda:self.service.command(self.sid,self.token,key,'consent.withdraw',{},1))

    def test_snapshot_export_works_at_every_logical_cap_without_writes(self):
        self.active()
        self.command('source.text',{'text':'A pending proposal'})
        self.service.MAX_RECORDS=0;self.service.MAX_REQUESTS=0;self.service.MAX_SESSION_BYTES=0
        with self.service.db.transaction() as c:before='\n'.join(c.iterdump())
        result=self.service.export_snapshot(self.sid,self.token,{'include_unresolved':True})
        self.assertEqual({r['id'] for r in result['records']},{r['id'] for r in result['manifest']['included']})
        self.assertEqual(1,len(result['records']))
        with self.service.db.transaction() as c:self.assertEqual(before,'\n'.join(c.iterdump()))
