"""The canvas object model: shapes, text, arrows, sections and strokes.

`docs/specs/2026-10-18-canvas-object-model.md` is the contract. One test per
rule, each written so that removing its guard makes the test fail rather than
error; `tests/mutation_check.py` names the test that kills each guard.

The rule the whole model turns on, and the reason two paths exist: a person
drawing by hand is arranging, like moving a note, so `canvas.create` puts an
accepted item on the canvas at once. Anything proposed goes through
`proposal.create` with `proposal_kind: "canvas"` and waits for a facilitator,
as everything a model makes does.

Helpers call `Service.command` directly and take a snapshot only when a
control command needs its sequence, because the record-cap test makes many
commands and a snapshot per command made it quadratic.
"""
import secrets
import shutil
import sqlite3
import unittest
from pathlib import Path

from genai_server.db import Database
from genai_server.service import Service, encode
from genai_server.validation import Problem


class CanvasObjectTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1] / '.local' / 'tests'
        root.mkdir(parents=True, exist_ok=True)
        directory = root / secrets.token_hex(16)
        directory.mkdir()
        assert directory.resolve().is_relative_to(root.resolve())
        self.addCleanup(shutil.rmtree, directory)
        self.directory = directory
        self.path = directory / 'state.sqlite3'
        self.now = 1000.0
        self.service = Service(self.path, clock=lambda: self.now)
        self.sid = secrets.token_hex(16)
        self.token = secrets.token_urlsafe(32)
        self.service.create_session({'session_id': self.sid, 'title': 'Workshop',
                                     'owner_name': 'Facilitator', 'owner_token': self.token})

    # helpers

    def cmd(self, op, payload, token=None):
        return self.service.command(self.sid, token or self.token, secrets.token_hex(16), op, payload)['result']

    def control(self, op, payload=None, token=None):
        snap = self.service.snapshot(self.sid, token or self.token)
        payload = dict(payload or {})
        if op in ('session.activate', 'session.close'):
            payload['expected_session_revision'] = snap['session']['revision']
        sequence = snap['next_control_sequence'] if op in Service.CONTROL_COMMANDS else None
        return self.service.command(self.sid, token or self.token, secrets.token_hex(16), op, payload, sequence)['result']

    def active(self):
        version = self.service.snapshot(self.sid, self.token)['session']['policy_version']
        self.cmd('consent.acknowledge', {'policy_version': version})
        self.control('session.activate', {'policy_version': version})

    def invite(self, role='participant'):
        token = secrets.token_urlsafe(32)
        invitation = secrets.token_urlsafe(32)
        snap = self.service.snapshot(self.sid, self.token)
        self.cmd('participant.invite', {'invitation': invitation, 'role': role,
                                        'expected_roster_revision': snap['session']['roster_revision']})
        self.service.join(self.sid, {'invitation': invitation, 'token': token, 'name': 'Bea',
                                     'policy_version': snap['session']['policy_version']})
        return token

    def problem(self, code, call, status=None):
        with self.assertRaises(Problem) as ctx:
            call()
        self.assertEqual(code, ctx.exception.code, ctx.exception.message)
        if status is not None:
            self.assertEqual(status, ctx.exception.status)
        return ctx.exception

    def create(self, kind, data, x=0, y=0, token=None, **size):
        return self.cmd('canvas.create', {'kind': kind, 'data': data, 'x': x, 'y': y, **size}, token)

    def shape(self, x=0, y=0, token=None, **data):
        return self.create('shape', {'shape': 'rect', 'tone': 'ink', **data}, x, y, token, w=120, h=80)['item']

    def arrow(self, start, end, **data):
        return self.create('arrow', {'from': start, 'to': end, 'tone': 'ink', **data})

    def section(self, members, **data):
        body = {'title': 'Ideas', 'form': 'free', 'member_ids': [m['id'] for m in members], **data}
        return self.create('section', body, w=400, h=300)

    def stroke(self, points, **data):
        return self.create('stroke', {'points': points, 'weight': 'regular', 'tone': 'ink', **data})

    def note(self):
        """An accepted typed note, which needs an active session."""
        made = self.cmd('source.text', {'text': 'A typed note'})
        proposal = made['proposal']
        item = self.cmd('proposal.review', {'proposal_id': proposal['id'], 'expected_revision': proposal['revision'],
                                            'decision': 'accept'})['item']
        return made['source'], item

    def propose(self, kind='shape', data=None, positions=None):
        body = {'proposal_kind': 'canvas', 'canvas_kind': kind,
                'canvas_data': data if data is not None else {'shape': 'ellipse', 'tone': 'accent', 'text': 'Maybe'}}
        if positions is not None:
            body['positions'] = positions
        return self.cmd('proposal.create', body)

    def review(self, proposal, decision='accept', token=None):
        return self.cmd('proposal.review', {'proposal_id': proposal['id'], 'expected_revision': proposal['revision'],
                                            'decision': decision}, token)

    def record(self, rid):
        return self.service.record(self.sid, self.token, rid)

    def update(self, item, data, token=None):
        return self.cmd('canvas.update', {'item_id': item['id'], 'expected_revision': item['revision'], 'data': data}, token)

    def remove(self, item, token=None):
        return self.cmd('canvas.remove', {'item_id': item['id'], 'expected_revision': item['revision']}, token)

    def place(self, rid, revision=0, **extra):
        return self.cmd('item.place', {'placements': [{'id': rid, 'x': 10, 'y': 20,
                                                       'expected_position_revision': revision, **extra}]})

    # the review rule

    def test_a_hand_made_object_is_an_accepted_item_at_once(self):
        made = self.create('shape', {'shape': 'diamond', 'tone': 'category-2', 'text': 'Decision'}, 40, 50, w=120, h=90)
        item, position = made['item'], made['position']
        actor = self.service.snapshot(self.sid, self.token)['actor_id']
        self.assertEqual('item', item['kind'])
        self.assertEqual({'item_kind': 'shape', 'shape': 'diamond', 'tone': 'category-2', 'text': 'Decision',
                          'origin': 'human', 'made_by_hand': True, 'status': 'accepted',
                          'author_id': actor, 'accepted_by': actor},
                         {k: item['data'][k] for k in ('item_kind', 'shape', 'tone', 'text', 'origin', 'made_by_hand',
                                                       'status', 'author_id', 'accepted_by')})
        self.assertEqual((40.0, 50.0, 120.0, 90.0, True), (position['x'], position['y'], position['w'],
                                                          position['h'], position['hand_placed']))
        kinds = [r['kind'] for r in self.service.snapshot(self.sid, self.token)['records']]
        self.assertEqual(['item'], kinds, 'drawing by hand writes no proposal to review')

    def test_a_canvas_proposal_waits_for_a_facilitator(self):
        participant = self.invite()
        proposal = self.cmd('proposal.create', {'proposal_kind': 'canvas', 'canvas_kind': 'text',
                                                'canvas_data': {'text': 'Proposed heading', 'size': 'heading'},
                                                'positions': [{'x': 5, 'y': 6, 'w': 200, 'h': 40}]}, participant)
        self.assertEqual(('proposal', 'needs_review', 'canvas', 'text'),
                         (proposal['kind'], proposal['data']['status'], proposal['data']['proposal_kind'],
                          proposal['data']['canvas_kind']))
        self.assertEqual([], [r for r in self.service.snapshot(self.sid, self.token)['records'] if r['kind'] == 'item'])
        position = self.record(proposal['id'])['position']
        self.assertEqual((5.0, 6.0, 200.0, 40.0, False),
                         (position['x'], position['y'], position['w'], position['h'], position['hand_placed']))
        self.problem('forbidden', lambda: self.review(proposal, token=participant), 403)
        accepted = self.review(proposal)
        item = accepted['item']
        self.assertEqual(('text', 'Proposed heading', 'heading', 'human', proposal['id'], 'accepted'),
                         (item['data']['item_kind'], item['data']['text'], item['data']['size'],
                          item['data']['origin'], item['data']['proposal_id'], item['data']['status']))
        self.assertNotIn('made_by_hand', item['data'], 'an accepted proposal was not drawn by hand')
        carried = self.record(item['id'])['position']
        self.assertEqual((5.0, 6.0, 200.0, 40.0, True),
                         (carried['x'], carried['y'], carried['w'], carried['h'], carried['hand_placed']))
        self.assertIsNone(self.record(proposal['id'])['position'], 'the proposal leaves the board')

    def test_a_rejected_canvas_proposal_creates_no_item(self):
        proposal = self.propose()
        result = self.review(proposal, 'reject')
        self.assertEqual('rejected', result['proposal']['data']['status'])
        self.assertNotIn('item', result)
        self.assertEqual([], [r for r in self.service.snapshot(self.sid, self.token)['records'] if r['kind'] == 'item'])

    def test_a_typed_note_is_still_reviewed(self):
        self.active()
        made = self.cmd('source.text', {'text': 'Typed'})
        self.assertEqual('needs_review', made['proposal']['data']['status'])
        self.assertEqual([], [r for r in self.service.snapshot(self.sid, self.token)['records'] if r['kind'] == 'item'])

    # who and when

    def test_drawing_is_not_gated_on_an_active_session(self):
        drawn = self.shape()
        self.assertEqual('draft', self.service.snapshot(self.sid, self.token)['session']['state'])
        self.active()
        self.control('session.pause')
        self.assertEqual('paused', self.service.snapshot(self.sid, self.token)['session']['state'])
        updated = self.update(drawn, {'tone': 'accent'})['item']
        self.remove(updated)
        self.propose()

    def test_a_closed_session_refuses_canvas_commands(self):
        drawn = self.shape()
        self.control('session.close')
        self.problem('session_closed', lambda: self.shape(), 409)
        self.problem('session_closed', lambda: self.update(drawn, {'tone': 'accent'}), 409)
        self.problem('session_closed', lambda: self.remove(drawn), 409)
        self.problem('session_closed', lambda: self.propose(), 409)

    def test_a_viewer_cannot_draw(self):
        viewer = self.invite('viewer')
        drawn = self.shape()
        self.problem('forbidden', lambda: self.shape(token=viewer), 403)
        self.problem('forbidden', lambda: self.update(drawn, {'tone': 'accent'}, viewer), 403)
        self.problem('forbidden', lambda: self.remove(drawn, viewer), 403)

    def test_a_participant_may_change_what_somebody_else_drew(self):
        participant = self.invite()
        drawn = self.shape()
        updated = self.update(drawn, {'text': 'Renamed'}, participant)['item']
        self.assertEqual('Renamed', updated['data']['text'])
        self.assertEqual('undone', self.remove(updated, participant)['item']['data']['status'])

    # kinds and closed sets

    def test_an_unknown_canvas_kind_is_refused(self):
        self.problem('invalid_kind', lambda: self.create('sticker', {'shape': 'rect', 'tone': 'ink'}, w=10, h=10))

    def test_an_unknown_canvas_proposal_kind_is_refused(self):
        self.problem('invalid_kind', lambda: self.propose('sticker'))

    def test_an_unknown_tone_is_refused(self):
        self.problem('invalid_tone', lambda: self.shape(tone='danger'))

    def test_an_unknown_shape_is_refused(self):
        self.problem('invalid_shape', lambda: self.shape(shape='star'))

    def test_an_unknown_text_size_is_refused(self):
        self.problem('invalid_text_size', lambda: self.create('text', {'text': 'Hi', 'size': 'huge'}, w=50, h=20))

    def test_an_unknown_section_form_is_refused(self):
        self.problem('invalid_form', lambda: self.section([], form='hierarchy'))

    def test_an_unknown_stroke_weight_is_refused(self):
        self.problem('invalid_weight', lambda: self.stroke([[0, 0], [5, 5]], weight='heavy'))

    def test_a_field_the_kind_does_not_have_is_refused(self):
        self.problem('unknown_fields', lambda: self.shape(colour='#ff0000'))

    def test_a_kind_field_cannot_be_left_out(self):
        self.problem('missing_fields', lambda: self.create('shape', {'shape': 'rect'}, w=10, h=10))

    # text lengths

    def test_shape_text_is_at_most_280_characters(self):
        self.shape(text='x' * 280)
        self.problem('invalid_text', lambda: self.shape(text='x' * 281))

    def test_text_is_1_to_1000_characters(self):
        self.create('text', {'text': 'x' * 1000, 'size': 'body'}, w=200, h=100)
        self.problem('invalid_text', lambda: self.create('text', {'text': 'x' * 1001, 'size': 'body'}, w=200, h=100))
        self.problem('invalid_text', lambda: self.create('text', {'text': '  ', 'size': 'body'}, w=200, h=100))

    def test_an_arrow_label_is_at_most_80_characters(self):
        self.arrow({'x': 0, 'y': 0}, {'x': 9, 'y': 9}, label='x' * 80)
        self.problem('invalid_text', lambda: self.arrow({'x': 0, 'y': 0}, {'x': 9, 'y': 9}, label='x' * 81))

    def test_a_section_title_is_at_most_80_characters(self):
        self.section([], title='x' * 80)
        self.problem('invalid_text', lambda: self.section([], title='x' * 81))

    # arrows

    def test_an_arrow_end_must_exist(self):
        self.problem('not_found', lambda: self.arrow({'id': 'missing-record-id'}, {'x': 0, 'y': 0}), 404)

    def test_an_arrow_end_must_be_on_the_canvas(self):
        gone = self.shape()
        self.remove(gone)
        self.problem('invalid_endpoint', lambda: self.arrow({'id': gone['id']}, {'x': 0, 'y': 0}), 409)

    def test_an_arrow_end_must_be_an_item_or_proposal(self):
        self.active()
        source, _ = self.note()
        self.problem('invalid_endpoint', lambda: self.arrow({'id': source['id']}, {'x': 0, 'y': 0}), 422)

    def test_an_arrow_end_is_an_id_or_a_point_not_both(self):
        target = self.shape()
        self.problem('invalid_endpoint', lambda: self.arrow({'id': target['id'], 'x': 0}, {'x': 0, 'y': 0}))

    def test_an_arrow_end_point_stays_on_the_board(self):
        self.problem('invalid_endpoint', lambda: self.arrow({'x': 100001, 'y': 0}, {'x': 0, 'y': 0}))

    def test_an_arrow_cannot_point_from_a_record_to_itself(self):
        target = self.shape()
        self.problem('self_arrow', lambda: self.arrow({'id': target['id']}, {'id': target['id']}))

    def test_an_arrow_cannot_be_turned_to_point_at_itself(self):
        target = self.shape()
        made = self.arrow({'id': target['id']}, {'x': 0, 'y': 0})['item']
        self.problem('self_arrow', lambda: self.update(made, {'to': {'id': made['id']}}))

    def test_an_arrow_connects_two_records(self):
        a, b = self.shape(), self.shape(x=300)
        made = self.arrow({'id': a['id']}, {'id': b['id']}, label='leads to')['item']
        self.assertEqual(({'id': a['id']}, {'id': b['id']}), (made['data']['from'], made['data']['to']))
        self.assertEqual((None, None), (self.record(made['id'])['position']['w'],
                                        self.record(made['id'])['position']['h']))

    # sections

    def test_a_section_member_must_exist(self):
        self.problem('not_found', lambda: self.create('section', {'title': 'A', 'form': 'free',
                                                                  'member_ids': ['missing-record-id']}, w=50, h=50), 404)

    def test_a_section_holds_at_most_60_members(self):
        members = [self.shape(x=index) for index in range(61)]
        self.section(members[:60])
        self.problem('section_too_large', lambda: self.section(members))

    def test_a_section_cannot_hold_a_section(self):
        inner = self.section([self.shape()])['item']
        self.problem('nested_section', lambda: self.section([inner]))

    def test_a_section_member_is_a_note_shape_text_or_stroke(self):
        a, b = self.shape(), self.shape()
        link = self.arrow({'id': a['id']}, {'id': b['id']})['item']
        self.problem('invalid_member', lambda: self.section([link]), 422)

    def test_a_section_takes_notes_text_and_strokes(self):
        self.active()
        _, note = self.note()
        words = self.create('text', {'text': 'Label', 'size': 'title'}, w=80, h=20)['item']
        line = self.stroke([[0, 0], [3, 4]])['item']
        made = self.section([note, words, line, self.shape()])['item']
        self.assertEqual(4, len(made['data']['member_ids']))

    def test_a_section_member_appears_once(self):
        member = self.shape()
        self.problem('duplicate_member', lambda: self.section([member, member]))

    def test_a_removed_record_cannot_join_a_section(self):
        gone = self.shape()
        self.remove(gone)
        self.problem('invalid_member', lambda: self.section([gone]), 409)

    # strokes

    def test_a_stroke_has_at_least_two_points(self):
        self.problem('invalid_points', lambda: self.stroke([[0, 0]]))

    def test_a_stroke_has_at_most_256_points(self):
        self.stroke([[index, index] for index in range(256)])
        self.problem('invalid_points', lambda: self.stroke([[index, index] for index in range(257)]))

    def test_stroke_points_stay_within_10000_of_the_position(self):
        self.stroke([[0, 0], [10000, -10000]])
        self.problem('invalid_points', lambda: self.stroke([[0, 0], [10001, 0]]))

    def test_a_stroke_point_is_a_pair_of_numbers(self):
        self.problem('invalid_points', lambda: self.stroke([[0, 0], [1, 2, 3]]))

    # sizes

    def test_a_shape_text_or_section_needs_a_size_when_made(self):
        for kind, data in (('shape', {'shape': 'rect', 'tone': 'ink'}), ('text', {'text': 'A', 'size': 'body'}),
                           ('section', {'title': 'A', 'form': 'free', 'member_ids': []})):
            with self.subTest(kind=kind):
                self.problem('invalid_size', lambda: self.create(kind, data))

    def test_an_arrow_or_stroke_needs_no_size(self):
        self.arrow({'x': 0, 'y': 0}, {'x': 1, 'y': 1})
        self.stroke([[0, 0], [1, 1]])
        made = self.create('stroke', {'points': [[0, 0], [1, 1]], 'weight': 'fine', 'tone': 'ink'}, w=20, h=20)
        self.assertEqual((20.0, 20.0), (made['position']['w'], made['position']['h']))

    def test_a_note_is_refused_a_size(self):
        self.active()
        _, note = self.note()
        self.problem('invalid_size', lambda: self.place(note['id'], w=100, h=40))
        self.assertIsNone(self.record(note['id'])['position'], 'nothing was written')

    def test_a_cluster_is_refused_a_size(self):
        self.active()
        _, note = self.note()
        proposal = self.cmd('proposal.create', {'proposal_kind': 'relationship', 'form': 'cluster', 'text': 'Group',
                                                'refs': [{'id': note['id'], 'revision': note['revision']}]})
        cluster = self.review(proposal)['item']
        self.problem('invalid_size', lambda: self.place(cluster['id'], w=100, h=40))

    def test_a_size_below_8_is_refused(self):
        self.create('shape', {'shape': 'rect', 'tone': 'ink'}, w=8, h=8)
        self.problem('invalid_size', lambda: self.create('shape', {'shape': 'rect', 'tone': 'ink'}, w=7.5, h=8))

    def test_a_size_above_4000_is_refused(self):
        self.create('shape', {'shape': 'rect', 'tone': 'ink'}, w=4000, h=4000)
        self.problem('invalid_size', lambda: self.create('shape', {'shape': 'rect', 'tone': 'ink'}, w=100, h=4001))

    def test_a_width_needs_a_height(self):
        self.problem('invalid_size', lambda: self.create('shape', {'shape': 'rect', 'tone': 'ink'}, w=100))

    def test_moving_a_shape_keeps_its_size_unless_given_one(self):
        drawn = self.shape()
        moved = self.place(drawn['id'], 1)['placements'][0]
        self.assertEqual((120.0, 80.0), (moved['w'], moved['h']))
        resized = self.place(drawn['id'], 2, w=300, h=200)['placements'][0]
        self.assertEqual((300.0, 200.0, 3), (resized['w'], resized['h'], resized['revision']))

    def test_first_placing_a_proposed_shape_needs_a_size(self):
        proposal = self.propose()
        self.problem('invalid_size', lambda: self.place(proposal['id']))
        placed = self.place(proposal['id'], w=60, h=60)['placements'][0]
        self.assertEqual((60.0, 60.0), (placed['w'], placed['h']))

    def test_a_canvas_proposal_has_one_position_of_its_own(self):
        self.problem('invalid_positions', lambda: self.propose(positions=[{'x': 0, 'y': 0, 'w': 50, 'h': 50},
                                                                         {'x': 9, 'y': 9, 'w': 50, 'h': 50}]))

    def test_a_canvas_proposal_position_needs_a_size_for_a_shape(self):
        self.problem('invalid_size', lambda: self.propose(positions=[{'x': 0, 'y': 0}]))

    def test_moving_a_canvas_object_needs_its_current_position_revision(self):
        drawn = self.shape()
        self.problem('stale_position', lambda: self.place(drawn['id'], 0), 409)

    def test_a_hand_made_object_must_be_drawn_on_the_board(self):
        self.problem('invalid_position', lambda: self.create('shape', {'shape': 'rect', 'tone': 'ink'},
                                                             x=100001, w=10, h=10))

    # update and remove

    def test_an_update_is_a_new_revision_of_the_changed_fields(self):
        drawn = self.shape(text='First')
        updated = self.update(drawn, {'text': 'Second'})['item']
        self.assertEqual(2, updated['revision'])
        self.assertEqual(('rect', 'ink', 'Second', True, 'human'),
                         (updated['data']['shape'], updated['data']['tone'], updated['data']['text'],
                          updated['data']['made_by_hand'], updated['data']['origin']))

    def test_an_update_cannot_change_common_fields(self):
        drawn = self.shape()
        self.problem('unknown_fields', lambda: self.update(drawn, {'origin': 'model'}))
        self.assertEqual('human', self.record(drawn['id'])['data']['origin'])

    def test_an_update_names_at_least_one_field(self):
        drawn = self.shape()
        self.problem('invalid_data', lambda: self.update(drawn, {}))

    def test_an_update_needs_the_current_revision(self):
        drawn = self.shape()
        self.update(drawn, {'tone': 'accent'})
        error = self.problem('stale_revision', lambda: self.update(drawn, {'tone': 'ink'}), 409)
        self.assertEqual(2, error.details['current_revision'])

    def test_a_removal_needs_the_current_revision(self):
        drawn = self.shape()
        self.update(drawn, {'tone': 'accent'})
        self.problem('stale_revision', lambda: self.remove(drawn), 409)

    def test_an_update_is_only_for_canvas_objects(self):
        self.active()
        _, note = self.note()
        self.problem('invalid_target', lambda: self.update(note, {'tone': 'ink'}))

    def test_only_canvas_objects_can_be_removed_this_way(self):
        self.active()
        _, note = self.note()
        self.problem('invalid_target', lambda: self.remove(note))
        self.assertEqual('accepted', self.record(note['id'])['data']['status'])

    def test_a_removed_object_cannot_be_updated(self):
        drawn = self.shape()
        removed = self.remove(drawn)['item']
        self.problem('item_undone', lambda: self.update(removed, {'tone': 'accent'}), 409)

    def test_removing_marks_undone_and_item_undo_restores_it(self):
        drawn = self.shape(x=70, y=80)
        removed = self.remove(drawn)['item']
        self.assertEqual('undone', removed['data']['status'])
        restored = self.cmd('item.undo', {'item_id': drawn['id'], 'expected_revision': removed['revision'],
                                          'restore_revision': 1})['item']
        self.assertEqual(('accepted', 3), (restored['data']['status'], restored['revision']))
        position = self.record(drawn['id'])['position']
        self.assertEqual((70.0, 80.0, 120.0, 80.0), (position['x'], position['y'], position['w'], position['h']))

    def test_item_edit_refuses_a_canvas_object(self):
        self.active()
        source, _ = self.note()
        drawn = self.shape()
        self.problem('invalid_target', lambda: self.cmd('item.edit', {
            'item_id': drawn['id'], 'expected_revision': drawn['revision'], 'text': 'Now a note',
            'refs': [{'id': source['id'], 'revision': source['revision']}]}))

    def test_proposal_edit_refuses_a_canvas_proposal(self):
        self.active()
        source, _ = self.note()
        proposal = self.propose()
        self.problem('invalid_target', lambda: self.cmd('proposal.edit', {
            'proposal_id': proposal['id'], 'expected_revision': proposal['revision'], 'text': 'Changed',
            'refs': [{'id': source['id'], 'revision': source['revision']}]}), 409)

    def test_accepting_a_canvas_proposal_rechecks_its_ends(self):
        target = self.shape()
        proposal = self.propose('arrow', {'from': {'id': target['id']}, 'to': {'x': 0, 'y': 0}, 'tone': 'accent'})
        self.remove(target)
        self.problem('invalid_endpoint', lambda: self.review(proposal), 409)

    # limits and sync

    def test_canvas_objects_count_toward_the_record_cap(self):
        """998 records written directly, then two drawn, then the cap refuses a third.

        Writing the filler through commands costs a snapshot or a budget scan
        per record. The guard under test is `_new`, which counts every record,
        so filler rows of any kind exercise it.
        """
        with self.service.db.transaction() as c:
            for index in range(Service.MAX_RECORDS - 2):
                c.execute('INSERT INTO records VALUES(?,?,?,?,?)',
                          ('filler-%06d' % index, self.sid, 'source', 1, encode({'type': 'text', 'text': 'x'})))
        self.shape()
        self.arrow({'x': 0, 'y': 0}, {'x': 1, 'y': 1})
        self.problem('record_capacity', lambda: self.shape(), 429)
        self.problem('record_capacity', lambda: self.propose(), 429)

    def test_a_delta_carries_a_drawn_object_and_its_size(self):
        # Three earlier records, so one change is under half the session and
        # the answer is a delta rather than resync_required.
        for index in range(3):
            self.shape(x=index)
        cursor = self.service.snapshot(self.sid, self.token)['session']['seq']
        drawn = self.shape()
        delta = self.service.delta(self.sid, self.token, cursor)
        if delta.get('resync_required'):
            self.fail('one new record in a four-record session should be a delta, not a resync')
        records = {r['id']: r for r in delta['records']}
        self.assertIn(drawn['id'], records)
        self.assertEqual((120.0, 80.0), (records[drawn['id']]['position']['w'], records[drawn['id']]['position']['h']))
        events = self.service.events(self.sid, self.token, cursor)['events']
        named = {(r['id'], r['kind']) for r in events[-1]['data']['records']}
        self.assertEqual({(drawn['id'], 'item'), (drawn['id'], 'position')}, named)

    def test_a_note_position_reports_no_size(self):
        self.active()
        _, note = self.note()
        self.place(note['id'])
        position = self.service.snapshot(self.sid, self.token)['records'][-1]['position']
        self.assertEqual((None, None), (position['w'], position['h']))

    def test_an_export_includes_drawn_objects(self):
        self.shape(text='Exported words')
        self.stroke([[0, 0], [1, 1]])
        exported = self.cmd('export.create', {'include_unresolved': True})
        self.assertEqual(2, len(exported['data']['records']))
        self.assertIn('Exported words', exported['data']['markdown'])


class CanvasMigrationTests(unittest.TestCase):
    """Schema 6 adds a size to positions and leaves every existing one without."""

    def setUp(self):
        root = Path(__file__).resolve().parents[1] / '.local' / 'tests'
        root.mkdir(parents=True, exist_ok=True)
        directory = root / secrets.token_hex(16)
        directory.mkdir()
        self.addCleanup(shutil.rmtree, directory)
        self.path = directory / 'legacy.sqlite3'

    def version_five(self):
        """A converged version 5 database holding one placed record."""
        Database(self.path)
        conn = sqlite3.connect(self.path)
        try:
            for name in ('w', 'h'):
                conn.execute('ALTER TABLE positions DROP COLUMN ' + name)
            conn.execute("INSERT INTO sessions(id,title,state,policy_version,seq,created,expires,lease) "
                         "VALUES('session1','Old','draft',1,0,1000,9000,1300)")
            conn.execute("INSERT INTO positions VALUES('session1','record1',20,30,7,1,'actor1',1000)")
            conn.execute('PRAGMA user_version=5')
            conn.commit()
        finally:
            conn.close()

    def test_a_version_5_database_keeps_its_positions_with_no_size(self):
        self.version_five()
        for _ in range(2):
            Service(self.path, clock=lambda: 2000.0)
            conn = sqlite3.connect(self.path)
            try:
                self.assertEqual(6, conn.execute('PRAGMA user_version').fetchone()[0])
                self.assertEqual([(20.0, 30.0, 7, 1, None, None)],
                                 conn.execute('SELECT x,y,revision,hand_placed,w,h FROM positions').fetchall())
            finally:
                conn.close()


if __name__ == '__main__':
    unittest.main()
