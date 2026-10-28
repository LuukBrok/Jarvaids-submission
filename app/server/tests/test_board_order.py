"""The board z-order fixture is what the server produces today, not what it
produced once.

`tests/board-order-unit.mjs` checks the client's ordering against
`tests/board-order-fixture.json`. That check is only worth anything while the
fixture still says what this server says: a stale fixture would let the server's
rule move and still report the two implementations as agreeing, which is exactly
the drift the fixture exists to catch.

So the fixture is regenerated here and compared. It is regenerated into a
temporary directory and never written over the committed file, because CI fails
a job whose checks modify tracked files, and because a test that quietly fixes
what it is checking cannot fail.
"""
import json
import unittest

from genai_server.service import Service
from make_order_fixture import FIXTURE, render


class BoardOrderFixtureTests(unittest.TestCase):
    def setUp(self):
        self.text = FIXTURE.read_text(encoding='utf-8')
        self.snapshot = json.loads(self.text)['snapshot']
        self.placed = [r for r in self.snapshot['records'] if r['position'] is not None]

    def test_the_committed_fixture_is_what_this_server_produces(self):
        """Regenerate and compare. The message says how to fix it, because the
        fix is one command and the failure is otherwise mystifying."""
        self.assertEqual(self.text, render(),
                         'The fixture no longer matches this server. If the z-order rule changed '
                         'deliberately, change the client to match and run '
                         'python3 tests/make_order_fixture.py.')

    def test_regeneration_is_reproducible(self):
        """Two runs, one file. Identifiers and timestamps are normally random or
        wall-clock; if either leaked in, the comparison above would fail on an
        unrelated commit and get deleted as flaky."""
        self.assertEqual(render(), render())

    def test_the_fixture_exercises_every_part_of_the_rule(self):
        """A board that any plausible sort would order correctly would leave the
        JavaScript check green while proving nothing. Each assertion here is one
        of the three sort keys being load-bearing."""
        machine = [r for r in self.placed if not r['position']['hand_placed']]
        hand = [r for r in self.placed if r['position']['hand_placed']]
        self.assertGreaterEqual(len(machine), 2)
        self.assertGreaterEqual(len(hand), 2)

        times = [r['position']['placed_at'] for r in machine]
        tied = [t for t in set(times) if times.count(t) >= 3]
        self.assertTrue(tied, 'three records must share a placed_at or the id tie-break is untested')
        shared = [r['id'] for r in machine if r['position']['placed_at'] == tied[0]]
        self.assertNotEqual(shared, sorted(shared),
                            'the tied records must arrive in a different order from their id order, '
                            'otherwise dropping the tie-break changes nothing')
        self.assertGreater(len(set(times)), 1, 'placed_at must separate records of one origin')
        hand_times = [r['position']['placed_at'] for r in hand]
        self.assertLess(min(hand_times), max(times),
                        'a person must have placed something before the engine did, so that '
                        'hand_placed outranks placed_at rather than agreeing with it; without '
                        'that the first sort key can be dropped and nothing notices')
        self.assertGreater(max(hand_times), max(times),
                           'a record a person moved later must sort above the machine group')
        self.assertTrue(any(r['position'] is None for r in self.snapshot['records']),
                        'an unplaced record must be present and absent from the order')

    def test_the_servers_tie_break_does_not_depend_on_the_order_positions_arrive_in(self):
        """The fixture cannot catch this one, which is why it is here.

        SQLite answers `WHERE session_id=?` on the positions table from the
        primary-key index, so the rows already arrive in record-id order and a
        stable sort produces the right answer with the tie-break deleted.
        Deleting it from `_board_order` leaves the regenerated fixture
        byte-identical: verified by doing it. The rule is still load-bearing,
        because nothing promises that query plan, so it is pinned directly with
        two tied records handed over in the wrong order.
        """
        tied = {'record-zebra': {'hand_placed': False, 'placed_at': 5.0},
                'record-alpha': {'hand_placed': False, 'placed_at': 5.0}}
        self.assertEqual(['record-alpha', 'record-zebra'], Service._board_order(tied))

    def test_the_order_is_not_reachable_by_a_simpler_rule(self):
        """If the answer happened to equal record order or plain id order, the
        JavaScript check would pass against a client that had lost a key."""
        order = self.snapshot['board_order']
        ids = [r['id'] for r in self.placed]
        self.assertEqual(len(order), len(ids))
        self.assertNotEqual(order, ids)
        self.assertNotEqual(order, sorted(ids))
        self.assertNotEqual(order, sorted(ids, key=lambda rid: next(
            r['position']['placed_at'] for r in self.placed if r['id'] == rid)))


if __name__ == '__main__':
    unittest.main()
