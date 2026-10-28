"""Chunk B: an item has one position, and moving it is not agreeing with it.

Before this, coordinates lived inside accepted `placement` items. Two of them
could name the same item at (0,0) and at (500,500), both `accepted`, with no
field ordering them, so the API could not answer where an item was. Moving a
note cost a proposal, a facilitator decision and two records, and a participant
could not commit their own drag.

Position now lives in its own table, keyed by record. It is deliberately not in
`records.data`, and these tests pin the two reasons: refs pin revisions, so a
move stored as a record revision would stale every pending proposal about the
item, and every revision writes the whole record into `versions` again.

Vocabulary is `spec/canvas-layout.md`: hand-placed means a person created,
dragged, accepted or edited it, and it is sticky for the session because F3.4
protects a person's arrangement permanently.
"""
import base64
import secrets
import shutil
import sqlite3
import struct
import unittest
import zlib
from contextlib import contextmanager
from pathlib import Path

from genai_server.service import Service, encode
from genai_server.validation import Problem


@contextmanager
def database_connection(path):
    conn=sqlite3.connect(path)
    try:
        with conn:yield conn
    finally:conn.close()


def png(width=1, height=1):
    def chunk(kind, data):
        return (struct.pack('>I', len(data)) + kind + data
                + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff))
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b'\x00' + b'\xff' * (3 * width)))
            + chunk(b'IEND', b''))


class PositionTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1] / '.local' / 'tests'
        root.mkdir(parents=True, exist_ok=True)
        directory = root / secrets.token_hex(16)
        directory.mkdir()
        assert directory.resolve().is_relative_to(root.resolve())
        self.addCleanup(shutil.rmtree, directory)
        self.path = directory / 'state.sqlite3'
        self.now = 1000.0
        self.service = Service(self.path, clock=lambda: self.now)
        self.sid = secrets.token_hex(16)
        self.token = secrets.token_urlsafe(32)
        self.service.create_session({'session_id': self.sid, 'title': 'Workshop',
                                     'owner_name': 'Facilitator', 'owner_token': self.token})

    # helpers

    def cmd(self, op, payload=None, token=None, key=None):
        payload=dict(payload or {})
        snap=self.service.snapshot(self.sid,token or self.token)
        if op=='session.activate':payload['expected_session_revision']=snap['session']['revision']
        sequence=snap['next_control_sequence'] if op in self.service.CONTROL_COMMANDS else None
        return self.service.command(self.sid, token or self.token,
                                    key or secrets.token_hex(16), op, payload or {},sequence)['result']

    def active(self, tokens=()):
        version = self.service.snapshot(self.sid, self.token)['session']['policy_version']
        for token in (self.token, *tokens):
            self.cmd('consent.acknowledge', {'policy_version': version}, token)
        self.cmd('session.activate', {'policy_version': version})

    def invite(self, name='Bea', role='participant'):
        token = secrets.token_urlsafe(32)
        invitation=secrets.token_urlsafe(32)
        snap=self.service.snapshot(self.sid,self.token)
        self.cmd('participant.invite', {'invitation':invitation,'role':role,'expected_roster_revision':snap['session']['roster_revision']})
        self.service.join(self.sid,{'invitation':invitation,'token':token,'name':name,'policy_version':snap['session']['policy_version']})
        return token

    def note(self, value='A source note'):
        return self.accept(self.cmd('source.text', {'text': value})['proposal'])

    def accept(self, proposal):
        return self.cmd('proposal.review', {'proposal_id': proposal['id'],
                                            'expected_revision': proposal['revision'],
                                            'decision': 'accept'})['item']

    def place(self, rid, x, y, revision=0, token=None, origin=None):
        body = {'placements': [{'id': rid, 'x': x, 'y': y, 'expected_position_revision': revision}]}
        if origin is not None:
            body['origin'] = origin
        return self.cmd('item.place', body, token)['placements'][0]

    def position(self, rid):
        return self.service.record(self.sid, self.token, rid)['position']

    def problem(self, code, call):
        with self.assertRaises(Problem) as ctx:
            call()
        self.assertEqual(code, ctx.exception.code)
        return ctx.exception

    # the two things chunk B is done when

    def test_where_an_item_is_has_exactly_one_answer(self):
        """Two arrangements naming the same item, accepted in order. The second
        replaces the first rather than sitting beside it, and the position
        revision counts the moves so a client can tell which it has."""
        self.active()
        item = self.note()
        for x, y in ((0, 0), (500, 500)):
            p = self.cmd('proposal.create', {'proposal_kind': 'placement', 'text': 'Arrange',
                                             'refs': [{'id': item['id'], 'revision': item['revision']}],
                                             'positions': [{'id': item['id'], 'x': x, 'y': y}]})
            self.cmd('proposal.review', {'proposal_id': p['id'], 'expected_revision': p['revision'],
                                         'decision': 'accept'})

        self.assertEqual((500.0, 500.0, 2), tuple(self.position(item['id'])[k] for k in ('x', 'y', 'revision')))
        snapshot = self.service.snapshot(self.sid, self.token)
        placed = [r for r in snapshot['records'] if r['position'] is not None]
        self.assertEqual([item['id']], [r['id'] for r in placed])
        self.assertEqual([], [r for r in snapshot['records'] if r['data'].get('item_kind') == 'placement'])

    def test_a_participant_moves_their_own_note_without_review(self):
        """The whole point of the chunk. No proposal, no facilitator, no second
        record, and the mover is recorded so the move is still attributable."""
        self.active()
        item = self.note()
        guest = self.invite()

        moved = self.place(item['id'], 120, 40, token=guest)
        self.assertEqual({'x': 120.0, 'y': 40.0, 'revision': 1, 'hand_placed': True}, 
                         {k: moved[k] for k in ('x', 'y', 'revision', 'hand_placed')})
        members = {m['id']: m['name'] for m in self.service.snapshot(self.sid, self.token)['members']}
        self.assertEqual('Bea', members[moved['placed_by']])

    # moving is not editing

    def test_moving_an_item_leaves_the_item_untouched(self):
        """Not cosmetic: refs pin revisions. If a move bumped the record
        revision, dragging a note would stale every proposal about it."""
        self.active()
        item = self.note()
        before = self.service.record(self.sid, self.token, item['id'])
        self.place(item['id'], 10, 10)
        after = self.service.record(self.sid, self.token, item['id'])
        self.assertEqual((before['revision'], before['data']), (after['revision'], after['data']))

    def test_a_move_does_not_stale_a_pending_proposal_about_the_item(self):
        self.active()
        first, second = self.note('One'), self.note('Two')
        pending = self.cmd('proposal.create', {
            'proposal_kind': 'relationship', 'text': 'These two belong together',
            'refs': [{'id': first['id'], 'revision': first['revision']},
                     {'id': second['id'], 'revision': second['revision']}]})

        self.place(first['id'], 300, 300)

        accepted = self.accept(pending)
        self.assertEqual('accepted', accepted['data']['status'])

    def test_correcting_the_text_leaves_the_position_alone(self):
        """The complaint that opened the chunk: fixing a bad reading knocked the
        item out of the layout, so nobody fixed readings."""
        self.active()
        item = self.note('teh plan')
        self.place(item['id'], 640, 480)
        self.cmd('item.edit', {'item_id': item['id'], 'expected_revision': item['revision'],
                               'text': 'the plan', 'refs': item['data']['refs']})
        self.assertEqual((640.0, 480.0, 1),
                         tuple(self.position(item['id'])[k] for k in ('x', 'y', 'revision')))

    def test_undo_restores_text_without_restoring_a_position(self):
        """Undo must not erase somebody else's later move. Position is not
        versioned, so there is no old position for undo to put back."""
        self.active()
        item = self.note('first text')
        edited = self.cmd('item.edit', {'item_id': item['id'], 'expected_revision': item['revision'],
                                        'text': 'second text', 'refs': item['data']['refs']})['item']
        self.place(item['id'], 77, 88)
        self.cmd('item.undo', {'item_id': item['id'], 'expected_revision': edited['revision'],
                               'restore_revision': 1})

        current = self.service.record(self.sid, self.token, item['id'])
        self.assertEqual('first text', current['data']['text'])
        self.assertEqual((77.0, 88.0), (current['position']['x'], current['position']['y']))

    # guards

    # kills: position-concurrency
    def test_a_move_from_a_stale_view_is_refused(self):
        """Two people dragging the same note: the second is told to look before
        moving, rather than silently winning."""
        self.active()
        item = self.note()
        self.place(item['id'], 10, 10)
        problem = self.problem('stale_position', lambda: self.place(item['id'], 900, 900, revision=0))
        self.assertEqual(409, problem.status)
        self.assertEqual(1, problem.details['current_position_revision'])
        self.assertEqual((10.0, 10.0), (self.position(item['id'])['x'], self.position(item['id'])['y']))

    # kills: hand-placed-protected
    def test_the_layout_engine_may_not_move_what_a_person_placed(self):
        """F3.4 without exception. The rule is enforced here rather than trusted
        to the client, because the client running the layout scan is the one
        with the motive."""
        self.active()
        item = self.note()
        self.place(item['id'], 200, 200)
        problem = self.problem('hand_placed',
                               lambda: self.place(item['id'], 0, 0, revision=1, origin='machine'))
        self.assertEqual(409, problem.status)
        # The same move by a person is allowed.
        self.place(item['id'], 0, 0, revision=1)

    # kills: machine-placement-unowned
    def test_a_machine_placement_is_not_owned_until_a_person_moves_it(self):
        """If every placement counted as hand-placed, the layout engine could
        place an item once and would then be forbidden from ever refining it,
        so the meeting's first guess would keep the best space on the board."""
        self.active()
        item = self.note()
        machine = self.place(item['id'], 5, 5, origin='machine')
        self.assertFalse(machine['hand_placed'], 'the engine placed it, so nobody has touched it')
        self.assertFalse(self.place(item['id'], 6, 6, revision=1, origin='machine')['hand_placed'],
                         'the engine can still refine its own guess')
        self.assertTrue(self.place(item['id'], 7, 7, revision=2)['hand_placed'])
        # And from then on it is theirs.
        self.problem('hand_placed', lambda: self.place(item['id'], 8, 8, revision=3, origin='machine'))

    # kills: placement-bounds
    def test_coordinates_off_the_board_are_refused(self):
        self.active()
        item = self.note()
        for x, y in ((100001, 0), (0, -100001), (True, 0)):
            self.problem('invalid_position', lambda x=x, y=y: self.place(item['id'], x, y))
        # The handler also refuses a non-finite coordinate, but no command can
        # reach it with one: the idempotency fingerprint encodes the body with
        # allow_nan=False and raises ValueError first, which the HTTP layer turns
        # into a 500. That is J02 in decisions/backend-chunks.md, and it affects
        # every command, so it is not fixed here.
        self.assertIsNone(self.position(item['id']))

    # kills: placement-duplicate
    def test_one_record_cannot_appear_twice_in_one_move(self):
        """Two coordinates for one item in one command is the contradiction this
        chunk removed, arriving by another door."""
        self.active()
        item = self.note()
        self.problem('duplicate_placement', lambda: self.cmd('item.place', {'placements': [
            {'id': item['id'], 'x': 1, 'y': 1, 'expected_position_revision': 0},
            {'id': item['id'], 'x': 2, 'y': 2, 'expected_position_revision': 0}]}))
        self.assertIsNone(self.position(item['id']))

    def test_a_multi_item_move_is_all_or_nothing(self):
        self.active()
        first, second = self.note('One'), self.note('Two')
        self.problem('stale_position', lambda: self.cmd('item.place', {'placements': [
            {'id': first['id'], 'x': 1, 'y': 1, 'expected_position_revision': 0},
            {'id': second['id'], 'x': 2, 'y': 2, 'expected_position_revision': 9}]}))
        self.assertIsNone(self.position(first['id']))
        self.assertIsNone(self.position(second['id']))

    def test_an_undone_item_is_not_on_the_board(self):
        self.active()
        item = self.note()
        self.cmd('item.undo', {'item_id': item['id'], 'expected_revision': item['revision'],
                               'restore_revision': 0})
        self.problem('invalid_target', lambda: self.place(item['id'], 1, 1))

    # acceptance carries a drag

    def test_a_proposal_dragged_out_of_the_queue_keeps_where_it_was_put(self):
        """spec/canvas-layout.md: a provisional item a person has dragged is
        hand-placed and still provisional."""
        self.active()
        proposal = self.cmd('source.text', {'text': 'Drag me'})['proposal']
        self.place(proposal['id'], 320, 240)
        item = self.accept(proposal)

        self.assertEqual((320.0, 240.0, True),
                         tuple(self.position(item['id'])[k] for k in ('x', 'y', 'hand_placed')))
        self.assertIsNone(self.position(proposal['id']), 'the proposal has left the board')

    # board order and deletion

    def test_board_order_puts_hand_placed_above_model_placed(self):
        self.active()
        guessed, dragged = self.note('Guessed'), self.note('Dragged')
        self.place(guessed['id'], 1, 1, origin='machine')
        self.now += 1
        self.place(dragged['id'], 2, 2)
        self.assertEqual([guessed['id'], dragged['id']],
                         self.service.snapshot(self.sid, self.token)['board_order'])

    def test_deleting_a_session_takes_the_positions_with_it(self):
        """Coordinates are content: where a person put a note about somebody is
        a fact about the meeting, and the deletion promise covers it."""
        self.active()
        item = self.note()
        self.place(item['id'], 42, 42)
        self.service.delete_session(self.sid, self.token)
        with database_connection(self.path) as conn:
            self.assertEqual(0, conn.execute('SELECT count(*) FROM positions WHERE session_id=?',
                                             (self.sid,)).fetchone()[0])


class MigrationTests(unittest.TestCase):
    """Schema 1 to 2, the reconciliation half of B01.

    A version 1 database can hold two accepted placement items naming the same
    target at different coordinates. Both are valid and nothing orders them. The
    migration picks rowid order, so the last accepted arrangement wins, and says
    so rather than leaving each client to resolve it differently.
    """

    def setUp(self):
        root = Path(__file__).resolve().parents[1] / '.local' / 'tests'
        root.mkdir(parents=True, exist_ok=True)
        self.directory = root / secrets.token_hex(16)
        self.directory.mkdir()
        self.addCleanup(shutil.rmtree, self.directory)
        self.path = self.directory / 'legacy.sqlite3'

    def legacy(self, placements):
        """A version 1 database: no positions table, coordinates inside items."""
        from genai_server.db import SCHEMA
        with database_connection(self.path) as initial:
            initial.executescript(SCHEMA)
            initial.execute("INSERT INTO sessions VALUES('session1','Old','draft',1,0,1000,9000,1300,NULL,NULL)")
        initial.close()
        with database_connection(self.path) as conn:
            for rid, positions in placements:
                data = encode({'item_kind': 'placement', 'text': 'Arrange', 'status': 'accepted',
                               'origin': 'machine', 'accepted_by': 'actor1', 'created_at': 1000.0,
                               'refs': [{'id': p['id'], 'revision': 1} for p in positions],
                               'positions': positions})
                conn.execute('INSERT INTO records VALUES(?,?,?,?,?)', (rid, 'session1', 'item', 1, data))
                conn.execute('INSERT INTO versions VALUES(?,?,?,?)', ('session1', rid, 1, data))
            conn.execute('PRAGMA user_version=1')

    def test_the_last_accepted_arrangement_wins(self):
        self.legacy([('place1', [{'id': 'note1', 'x': 0, 'y': 0}]),
                     ('place2', [{'id': 'note1', 'x': 500, 'y': 500}])])

        Service(self.path, clock=lambda: 2000.0)

        with database_connection(self.path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute('SELECT * FROM positions').fetchall()
            self.assertEqual(1, len(rows), 'one item, one position')
            self.assertEqual((500.0, 500.0, 1), (rows[0]['x'], rows[0]['y'], rows[0]['hand_placed']))
            self.assertEqual(6, conn.execute('PRAGMA user_version').fetchone()[0])

    def test_a_folded_placement_is_kept_as_evidence(self):
        self.legacy([('place1', [{'id': 'note1', 'x': 7, 'y': 9}])])
        Service(self.path, clock=lambda: 2000.0)
        with database_connection(self.path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM records WHERE id='place1'").fetchone()
            self.assertIn('"status":"superseded"', row['data'])
            self.assertEqual(2, row['revision'])
            self.assertEqual(2, conn.execute("SELECT count(*) FROM versions WHERE record_id='place1'")
                             .fetchone()[0], 'every revision keeps a version row')

    def test_migrating_twice_changes_nothing(self):
        self.legacy([('place1', [{'id': 'note1', 'x': 7, 'y': 9}])])
        Service(self.path, clock=lambda: 2000.0)
        with database_connection(self.path) as conn:
            after = conn.execute('SELECT * FROM positions').fetchall()
        Service(self.path, clock=lambda: 3000.0)
        with database_connection(self.path) as conn:
            self.assertEqual(after, conn.execute('SELECT * FROM positions').fetchall())


if __name__ == '__main__':
    unittest.main()

