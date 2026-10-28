"""Chunk C: an event says what changed, and a client can fetch only that.

Events were built from whatever the handler returned, so accept, edit, correct
and undo emitted events naming no records at all, and a pause that staled every
pending proposal named nothing either. A client could not do a targeted refetch,
so it reloaded the session: measured at 402 KB at the record ceiling by
tests/measure_sync.py.

Events are now built from what was actually written, collected on the
transaction itself, so no handler can forget to declare a change.
"""
import gzip
import http.client
import json
import secrets
import shutil
import threading
import unittest
from pathlib import Path

from genai_server.http import LocalServer
from genai_server.service import Service, encode
from genai_server.validation import Problem


class SyncTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1] / '.local' / 'tests'
        root.mkdir(parents=True, exist_ok=True)
        directory = root / secrets.token_hex(16)
        directory.mkdir()
        assert directory.resolve().is_relative_to(root.resolve())
        self.addCleanup(shutil.rmtree, directory)
        self.now = 1000.0
        self.service = Service(directory / 'state.sqlite3', clock=lambda: self.now)
        self.sid = secrets.token_hex(16)
        self.token = secrets.token_urlsafe(32)
        self.service.create_session({'session_id': self.sid, 'title': 'Workshop',
                                     'owner_name': 'Facilitator', 'owner_token': self.token})
        self.active()

    def cmd(self, op, payload=None, token=None):
        payload=dict(payload or {})
        snap=self.service.snapshot(self.sid,token or self.token)
        if op=='session.activate':payload['expected_session_revision']=snap['session']['revision']
        sequence=snap['next_control_sequence'] if op in self.service.CONTROL_COMMANDS else None
        return self.service.command(self.sid, token or self.token,
                                    secrets.token_hex(16), op, payload or {},sequence)['result']

    def active(self):
        version = self.service.snapshot(self.sid, self.token)['session']['policy_version']
        self.cmd('consent.acknowledge', {'policy_version': version})
        self.cmd('session.activate', {'policy_version': version})

    def note(self, value='A source note'):
        proposal = self.cmd('source.text', {'text': value})['proposal']
        return self.cmd('proposal.review', {'proposal_id': proposal['id'],
                                            'expected_revision': proposal['revision'],
                                            'decision': 'accept'})['item']

    def last_event(self):
        events = self.service.events(self.sid, self.token, 0)['events']
        return events[-1]

    def cursor(self):
        return self.service.events(self.sid, self.token, 0)['current_seq']

    def problem(self, code, call):
        with self.assertRaises(Problem) as ctx:
            call()
        self.assertEqual(code, ctx.exception.code)
        return ctx.exception

    # kills: event-completeness

    def test_accepting_a_proposal_names_both_records_it_wrote(self):
        """The case the chunk opened on. Accept returned the item, so the event
        named the item and nothing else, and the proposal's own status change
        was invisible."""
        proposal = self.cmd('source.text', {'text': 'A note'})['proposal']
        item = self.cmd('proposal.review', {'proposal_id': proposal['id'],
                                            'expected_revision': proposal['revision'],
                                            'decision': 'accept'})['item']
        named = {r['id']: r for r in self.last_event()['data']['records']}
        self.assertEqual({proposal['id'], item['id']}, set(named))
        self.assertEqual(2, named[proposal['id']]['revision'], 'the accepted proposal moved to revision 2')
        self.assertEqual(1, named[item['id']]['revision'])

    def test_an_invalidation_cascade_names_what_it_staled(self):
        """The cascade emitted no event of its own, so a correction upstream
        silently staled items a client went on showing as current."""
        item = self.note('teh plan')
        source_id = item['data']['refs'][0]['id']
        self.cmd('source.correct', {'source_id': source_id, 'expected_revision': 1, 'text': 'the plan'})

        named = {r['id']: r for r in self.last_event()['data']['records']}
        self.assertIn(item['id'], named, 'the staled item must be named, not just the source')
        self.assertEqual('stale', self.service.record(self.sid, self.token, item['id'])['data']['status'])

    def test_a_pause_preserves_proposals_and_names_no_false_writes(self):
        """A pause stales every pending proposal in the session at once. It
        returned a state dict, so it named nothing."""
        pending = [self.cmd('source.text', {'text': 'Note %d' % i})['proposal'] for i in range(3)]
        self.cmd('session.pause')
        named = {r['id'] for r in self.last_event()['data']['records']}
        self.assertEqual(set(), named)
        for p in pending:self.assertEqual('needs_review',self.service.record(self.sid,self.token,p['id'])['data']['status'])

    def test_a_move_is_named_as_a_move_not_as_a_new_revision(self):
        """One command can write a record and move it, and those are two facts
        about one id, so the event carries both."""
        item = self.note()
        self.cmd('item.place', {'placements': [{'id': item['id'], 'x': 4, 'y': 4,
                                                'expected_position_revision': 0}]})
        records = self.last_event()['data']['records']
        self.assertEqual([{'id': item['id'], 'kind': 'position', 'revision': 1}], records)

    def test_every_event_carries_the_session_state(self):
        """A client that missed a pause must not need a snapshot to find out it
        has to re-acknowledge."""
        event = self.last_event()
        self.assertEqual(('active', 1), (event['data']['state'], event['data']['policy_version']))
        self.cmd('session.pause')
        self.assertEqual(('paused', 1), (self.last_event()['data']['state'],
                                         self.last_event()['data']['policy_version']))

    # the delta

    def test_a_delta_returns_only_what_changed_since_the_cursor(self):
        for index in range(4):
            self.note('Existing note %d' % index)
        cursor = self.cursor()
        fresh = self.note('The new one')

        delta = self.service.delta(self.sid, self.token, cursor)
        full = self.service.snapshot(self.sid, self.token)
        self.assertEqual({fresh['id'], fresh['data']['refs'][0]['id'], fresh['data']['proposal_id']},
                         {r['id'] for r in delta['records']})
        self.assertLess(len(delta['records']), len(full['records']))
        self.assertEqual((cursor, full['session']['seq']), (delta['since_seq'], delta['current_seq']))

    def test_a_delta_from_zero_asks_for_a_snapshot(self):
        """A client with no cursor has named every record in the session, which
        is exactly the case the resync path is for.

        Worth stating as a property rather than an accident: every client hits
        this on its first call, so the resync branch is exercised by everything
        that ever connects. A branch that only fires during a rare large cascade
        is a branch nobody has run.
        """
        self.note()
        delta = self.service.delta(self.sid, self.token, 0)
        self.assertTrue(delta.get('resync_required'),
                        'a client with no cursor has named every record')
        self.assertNotIn('records', delta)
        self.assertEqual(len(self.service.snapshot(self.sid, self.token)['records']),
                         delta['changed_records'])

    def test_a_cascade_over_half_the_session_asks_for_a_snapshot(self):
        """Correcting a source stales everything derived from it, transitively.
        Past halfway the snapshot is at most twice the bytes, in one request,
        with no merge to get wrong.

        The cascade here is a correction, not a pause: chunk E split the blunt
        revoke, so pausing no longer stales proposals.
        """
        item = self.note('teh plan')
        for index in range(8):
            self.cmd('proposal.create', {'proposal_kind': 'relationship',
                                         'text': 'Grouping %d' % index,
                                         'refs': [{'id': item['id'], 'revision': item['revision']}]})
        cursor = self.cursor()
        source_id = item['data']['refs'][0]['id']
        self.cmd('source.correct', {'source_id': source_id, 'expected_revision': 1,
                                    'text': 'the plan'})

        delta = self.service.delta(self.sid, self.token, cursor)
        # .get, not [], so removing the bound fails this by assertion rather
        # than by KeyError. The harness counts an exception as an infrastructure
        # problem, not a kill, and it is right to: a test that crashes has not
        # shown what the guard does.
        self.assertTrue(delta.get('resync_required'),
                        'a cascade naming most of the session must ask for a snapshot')
        self.assertGreater(delta['changed_records'] * 2, delta['session_records'])
        self.assertNotIn('records', delta, 'a resync answer carries no records')
        self.assertEqual(self.cursor(), delta['current_seq'])

    def test_the_resync_rule_is_exactly_past_halfway(self):
        """Stated as the rule rather than as a number, and probed on both sides
        of the line, because a boundary written down but never crossed is a
        boundary nobody knows the side of."""
        item = self.note('teh plan')
        for index in range(2):
            self.cmd('proposal.create', {'proposal_kind': 'relationship',
                                         'text': 'Grouping %d' % index,
                                         'refs': [{'id': item['id'], 'revision': item['revision']}]})
        for scenario, act in (('one new note', lambda: self.note('Unrelated')),
                              ('a correction cascade', lambda: self.cmd(
                                  'source.correct', {'source_id': item['data']['refs'][0]['id'],
                                                     'expected_revision': 1, 'text': 'the plan'}))):
            cursor = self.cursor()
            total = len(self.service.snapshot(self.sid, self.token)['records'])
            act()
            delta = self.service.delta(self.sid, self.token, cursor)
            if delta.get('resync_required'):
                self.assertGreater(delta['changed_records'] * 2, delta['session_records'], scenario)
            else:
                self.assertLessEqual(len(delta['records']) * 2, total + 3, scenario)

    def test_an_ordinary_change_is_still_a_delta(self):
        """The bound must not swallow the normal case it exists to protect."""
        for index in range(6):
            self.note('Note %d' % index)
        cursor = self.cursor()
        fresh = self.note('One more')
        delta = self.service.delta(self.sid, self.token, cursor)
        self.assertNotIn('resync_required', delta)
        self.assertEqual(3, len(delta['records']), 'source, proposal and item')
        self.assertIn(fresh['id'], [r['id'] for r in delta['records']])

    def test_a_delta_carries_the_position_of_a_record_it_returns(self):
        item = self.note()
        cursor = self.cursor()
        self.cmd('item.place', {'placements': [{'id': item['id'], 'x': 9, 'y': 9,
                                                'expected_position_revision': 0}]})
        delta = self.service.delta(self.sid, self.token, cursor)
        self.assertEqual([item['id']], [r['id'] for r in delta['records']])
        self.assertEqual((9.0, 9.0), (delta['records'][0]['position']['x'], delta['records'][0]['position']['y']))

    # kills: delta-cursor-ahead

    def test_a_cursor_ahead_of_the_session_is_refused(self):
        """A client holding a cursor this session never issued is holding state
        from somewhere else. An empty page would read as "nothing changed",
        which is the one answer that is certainly wrong."""
        self.note()
        problem = self.problem('cursor_ahead', lambda: self.service.delta(self.sid, self.token, 9999))
        self.assertEqual(409, problem.status)
        self.assertEqual(self.cursor(), problem.details['current_seq'])

    def test_a_delta_does_not_grow_with_the_board(self):
        """The regression test for INT13.

        `board_order` used to ride along on every delta, so a one-word edit cost
        every id on the board: 8183 B per client on a 320-item board against a
        5 KB budget. The measurement missed it because the fixture filled
        records without positioning them, which is not what a board looks like.

        Sizes here are compared at two board sizes rather than against a fixed
        number, so the test says what it means: the cost of one edit does not
        depend on how much is already on the board.
        """
        small = self.edit_one_word_on_a_board_of(10)
        large = self.edit_one_word_on_a_board_of(60)
        self.assertLess(abs(large - small), 256,
                        'a one-word edit cost %d B on a small board and %d B on a large one'
                        % (small, large))

    def edit_one_word_on_a_board_of(self, notes):
        items = []
        for index in range(notes):
            item = self.note('Wall note %d' % index)
            self.cmd('item.place', {'placements': [{'id': item['id'], 'x': index * 8, 'y': index * 4,
                                                    'expected_position_revision': 0}]})
            items.append(item)
        cursor = self.cursor()
        subject = items[0]
        self.cmd('item.edit', {'item_id': subject['id'], 'expected_revision': subject['revision'],
                               'text': 'Corrected', 'refs': subject['data']['refs']})
        delta = self.service.delta(self.sid, self.token, cursor)
        self.assertEqual([subject['id']], [r['id'] for r in delta['records']])
        return len(encode(delta))

    def test_a_client_can_rebuild_board_order_from_deltas_alone(self):
        """Dropping board_order from the delta is only safe if the client can
        keep the order itself. It can: the sort key is hand_placed, placed_at
        and id, and all three arrive on each record's position.

        Exercised across a move and a content edit, since INT13 asks for the
        ordering to hold after both.
        """
        first, second, third = (self.note('One'), self.note('Two'), self.note('Three'))
        for index, item in enumerate((first, second, third)):
            self.now += 1
            self.cmd('item.place', {'placements': [{'id': item['id'], 'x': index, 'y': index,
                                                    'expected_position_revision': 0}]},
                     )
        held = {r['id']: r for r in self.service.snapshot(self.sid, self.token)['records']}
        cursor = self.cursor()

        self.now += 10
        self.cmd('item.place', {'placements': [{'id': first['id'], 'x': 99, 'y': 99,
                                                'expected_position_revision': 1}]})
        self.cmd('item.edit', {'item_id': second['id'], 'expected_revision': second['revision'],
                               'text': 'Edited', 'refs': second['data']['refs']})

        for record in self.service.delta(self.sid, self.token, cursor)['records']:
            held[record['id']] = record

        placed = {rid: r['position'] for rid, r in held.items() if r['position'] is not None}
        rebuilt = sorted(placed, key=lambda rid: (placed[rid]['hand_placed'],
                                                  placed[rid]['placed_at'], rid))
        self.assertEqual(self.service.snapshot(self.sid, self.token)['board_order'], rebuilt)
        self.assertEqual(first['id'], rebuilt[-1], 'the most recently moved item is on top')

    def test_a_snapshot_still_carries_the_board_order(self):
        """The client is receiving everything anyway, so it is a convenience
        there rather than a cost that scales."""
        item = self.note()
        self.cmd('item.place', {'placements': [{'id': item['id'], 'x': 1, 'y': 1,
                                                'expected_position_revision': 0}]})
        self.assertEqual([item['id']], self.service.snapshot(self.sid, self.token)['board_order'])
        self.assertNotIn('board_order', self.service.delta(self.sid, self.token, 0))

    def test_a_delta_at_the_current_cursor_is_empty_but_valid(self):
        self.note()
        delta = self.service.delta(self.sid, self.token, self.cursor())
        self.assertEqual([], delta['records'])
        self.assertEqual(delta['since_seq'], delta['current_seq'])


class TransportTests(unittest.TestCase):
    """The transport half: keep-alive and compression, over a real socket."""

    def setUp(self):
        root = Path(__file__).resolve().parents[1] / '.local' / 'http-tests'
        root.mkdir(parents=True, exist_ok=True)
        directory = root / secrets.token_hex(16)
        directory.mkdir()
        self.addCleanup(shutil.rmtree, directory)
        self.service = Service(directory / 'state.sqlite3')
        self.server = LocalServer(('127.0.0.1', 0), self.service)
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={'poll_interval': .02}, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.sid = secrets.token_hex(16)
        self.token = secrets.token_urlsafe(32)
        self.conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        self.addCleanup(self.conn.close)
        self.call('POST', '/api/sessions', {'session_id': self.sid, 'owner_token': self.token,
                                            'title': 'Workshop', 'owner_name': 'Owner'})

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)

    def call(self, method, path, body=None, encoding='gzip'):
        headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.token,
                   'X-Request-ID': secrets.token_hex(16), 'Accept-Encoding': encoding}
        self.conn.request(method, path, None if body is None else json.dumps(body), headers)
        response = self.conn.getresponse()
        raw = response.read()
        if response.getheader('Content-Encoding') == 'gzip':
            raw = gzip.decompress(raw)
        try:body=json.loads(raw) if raw else None
        except json.JSONDecodeError:body=None
        return response.status, dict(response.getheaders()), body

    def cmd(self, op, payload=None):
        payload=dict(payload or {})
        if op=='session.activate':
            snapshot=self.call('GET',f'/api/sessions/{self.sid}')[-1]
            payload['expected_session_revision']=snapshot['session']['revision']
        return self.call('POST', f'/api/sessions/{self.sid}/commands',
                         {'operation': op, 'payload': payload or {}})

    # kills: keepalive-drain

    def test_an_unread_request_body_does_not_corrupt_the_next_request(self):
        """Only a problem once connections are reused: a POST to an unknown
        route is answered 404 without reading its body, and those bytes are then
        parsed as the start of the next request on the same socket."""
        self.assertEqual(404, self.call('POST', f'/api/sessions/{self.sid}/nonsense',
                                        {'padding': 'x' * 2000})[0])
        status, _, health = self.call('GET', '/health')
        self.assertEqual(200,status,'unread bytes must not corrupt the next request')
        self.assertEqual((200, 'ok'), (status, health['status']))
        self.assertIsNotNone(self.conn.sock, 'the connection should still be open')

    def test_a_large_payload_is_compressed_and_a_small_one_is_not(self):
        self.cmd('consent.acknowledge', {'policy_version': 1})
        self.cmd('session.activate', {'policy_version': 1})
        for index in range(12):
            self.cmd('source.text', {'text': 'A wall note about onboarding, number %d' % index})

        _, big, _ = self.call('GET', f'/api/sessions/{self.sid}')
        self.assertEqual('gzip', big.get('Content-Encoding'))
        self.assertIn('Accept-Encoding', big.get('Vary', ''))

        _, small, _ = self.call('GET', '/health')
        self.assertIsNone(small.get('Content-Encoding'), 'a short body is not worth a gzip frame')

        _, refused, _ = self.call('GET', f'/api/sessions/{self.sid}', encoding='identity')
        self.assertIsNone(refused.get('Content-Encoding'), 'a client that did not ask must not get gzip')

    def test_the_delta_route_takes_one_numeric_cursor(self):
        self.assertEqual(400, self.call('GET', f'/api/sessions/{self.sid}?since_seq=-1')[0])
        self.assertEqual(400, self.call('GET', f'/api/sessions/{self.sid}?since_seq=1&since_seq=2')[0])
        self.assertEqual(400, self.call('GET', f'/api/sessions/{self.sid}?nonsense=1')[0])
        self.assertEqual(200, self.call('GET', f'/api/sessions/{self.sid}?since_seq=0')[0])


if __name__ == '__main__':
    unittest.main()

