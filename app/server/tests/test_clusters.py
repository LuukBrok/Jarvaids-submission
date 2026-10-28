"""B06: grouping items into a form, and what happens when the group empties.

A cluster is a relationship with a `form`, so it rides the review path like
everything else a model makes. That is the point: a grouping the model drew is a
claim about meaning, and the product's central rule is that anything a model
made is provisional until a person accepts it. A separate direct-write command
for clusters would have quietly exempted the model's groupings from review.

Membership is by explicit reference, not by geometry. `spec/canvas-layout.md`
has the client decide a drop joins a group when the item's centre falls inside
the hull, but the result is recorded here as a reference, so two clients cannot
disagree about who is in a group.

Two things the spec does not settle, decided here and worth arguing with:

  An item belongs to at most one cluster. The spec draws a hull 12px outside its
  members and wants 24px between an item and a hull it is not in, so an item
  inside two hulls cannot satisfy its own separation rules. That makes it a
  drawing constraint rather than a policy preference.

  Removing the last member marks the cluster undone rather than deleting it.
  What the meeting grouped is evidence, and undo can restore it.
"""
import secrets
import shutil
import unittest
from pathlib import Path

from genai_server.service import Service
from genai_server.validation import Problem

import test_membership as membership


class ClusterTests(unittest.TestCase):
    setUp = membership.MembershipTests.setUp
    command = membership.MembershipTests.command
    active = membership.MembershipTests.active
    snap = membership.MembershipTests.snap
    invite = membership.MembershipTests.invite
    join = membership.MembershipTests.join
    refuses = membership.MembershipTests.refuses

    def note(self, value='A note'):
        proposal = self.command('source.text', {'text': value})['proposal']
        return self.command('proposal.review', {'proposal_id': proposal['id'],
                                                'expected_revision': proposal['revision'],
                                                'decision': 'accept'})['item']

    def cluster(self, items, label='Onboarding complaints'):
        proposal = self.command('proposal.create', {
            'proposal_kind': 'relationship', 'form': 'cluster', 'text': label,
            'refs': [{'id': i['id'], 'revision': i['revision']} for i in items]})
        return proposal

    def accept(self, proposal):
        return self.command('proposal.review', {'proposal_id': proposal['id'],
                                                'expected_revision': proposal['revision'],
                                                'decision': 'accept'})['item']

    def members(self, cluster_id):
        return [r['id'] for r in
                self.service.record(self.sid, self.token, cluster_id)['data']['refs']]

    # the review path

    def test_a_cluster_is_provisional_until_someone_accepts_it(self):
        """The reason a cluster is a proposal and not a direct write."""
        self.active()
        items = [self.note('One'), self.note('Two')]
        proposal = self.cluster(items)
        self.assertEqual('needs_review', proposal['data']['status'])
        self.assertEqual('cluster', proposal['data']['form'])

        accepted = self.accept(proposal)
        self.assertEqual('cluster', accepted['data']['form'], 'the form survives acceptance')
        self.assertEqual([i['id'] for i in items], [r['id'] for r in accepted['data']['refs']])

    def test_a_form_must_be_one_the_server_implements(self):
        self.active()
        items = [self.note('One')]
        for form in ('timeline', 'matrix', 'nonsense'):
            self.refuses('invalid_form', lambda form=form: self.command('proposal.create', {
                'proposal_kind': 'relationship', 'form': form, 'text': 'x',
                'refs': [{'id': items[0]['id'], 'revision': items[0]['revision']}]}))

    def test_only_a_relationship_takes_a_form(self):
        self.active()
        note = self.command('source.text', {'text': 'A note'})
        self.refuses('invalid_form', lambda: self.command('proposal.create', {
            'proposal_kind': 'content', 'form': 'cluster', 'text': 'x',
            'refs': [{'id': note['source']['id'], 'revision': 1}]}))

    # kills: cluster-size-cap

    def test_a_form_cannot_hold_more_than_twenty_four_items(self):
        """spec/canvas-layout.md: past 24 it is a list that has been drawn
        badly, so it is not a form and is refused."""
        self.active()
        items = [self.note('Note %d' % index) for index in range(25)]
        self.refuses('cluster_too_large', lambda: self.cluster(items))
        self.assertEqual(24, len(self.cluster(items[:24])['data']['refs']),
                         'exactly 24 is still a form')

    # kills: one-cluster-per-item

    def test_an_item_belongs_to_at_most_one_cluster(self):
        self.active()
        first, second, third = self.note('One'), self.note('Two'), self.note('Three')
        group = self.accept(self.cluster([first, second]))

        with self.assertRaises(Problem) as caught:
            self.cluster([second, third])
        self.assertEqual(('already_clustered', 409), (caught.exception.code, caught.exception.status))
        self.assertEqual(second['id'], caught.exception.details['record_id'])

        # Free once it leaves the first, which is what makes this a constraint
        # rather than a trap.
        self.command('cluster.membership', {'cluster_id': group['id'],
                                            'expected_revision': group['revision'],
                                            'remove': [second['id']]})
        self.assertEqual('cluster', self.accept(self.cluster([second, third]))['data']['form'])

    def test_a_proposed_cluster_cannot_claim_an_already_clustered_item(self):
        """Checked when proposed, so a facilitator is never asked to review a
        grouping that cannot be accepted."""
        self.active()
        first, second = self.note('One'), self.note('Two')
        self.accept(self.cluster([first, second]))
        self.refuses('already_clustered', lambda: self.cluster([first]))

    # membership, without review

    def test_any_editor_moves_an_item_into_a_group_without_review(self):
        """Joining a group by dragging is a person's arrangement act, like
        item.place. What the model proposes still goes through review."""
        self.active()
        first, second, outsider = self.note('One'), self.note('Two'), self.note('Three')
        group = self.accept(self.cluster([first, second]))
        body, joined = self.join(self.invite()[0])

        result = self.command('cluster.membership', {'cluster_id': group['id'],
                                                     'expected_revision': group['revision'],
                                                     'add': [outsider['id']]},
                              token=body['token'])
        self.assertEqual({first['id'], second['id'], outsider['id']}, set(result['members']))

    def test_a_membership_change_from_a_stale_view_is_refused(self):
        self.active()
        first, second = self.note('One'), self.note('Two')
        group = self.accept(self.cluster([first, second]))
        self.command('cluster.membership', {'cluster_id': group['id'],
                                            'expected_revision': group['revision'],
                                            'remove': [first['id']]})
        self.refuses('stale_revision', lambda: self.command('cluster.membership', {
            'cluster_id': group['id'], 'expected_revision': group['revision'],
            'remove': [second['id']]}))

    def test_a_cluster_cannot_hold_a_cluster(self):
        self.active()
        first, second, third = self.note('One'), self.note('Two'), self.note('Three')
        inner = self.accept(self.cluster([first, second]))
        outer = self.accept(self.cluster([third], 'Another group'))
        self.refuses('invalid_membership', lambda: self.command('cluster.membership', {
            'cluster_id': outer['id'], 'expected_revision': outer['revision'],
            'add': [inner['id']]}))

    def test_membership_cannot_add_and_remove_the_same_item(self):
        self.active()
        first, second = self.note('One'), self.note('Two')
        group = self.accept(self.cluster([first, second]))
        self.refuses('invalid_membership', lambda: self.command('cluster.membership', {
            'cluster_id': group['id'], 'expected_revision': group['revision'],
            'add': [first['id']], 'remove': [first['id']]}))

    def test_membership_must_name_something(self):
        self.active()
        group = self.accept(self.cluster([self.note('One')]))
        self.refuses('invalid_membership', lambda: self.command('cluster.membership', {
            'cluster_id': group['id'], 'expected_revision': group['revision']}))

    def test_only_a_cluster_takes_a_membership_change(self):
        self.active()
        plain = self.note('One')
        self.refuses('not_a_cluster', lambda: self.command('cluster.membership', {
            'cluster_id': plain['id'], 'expected_revision': plain['revision'],
            'remove': [plain['id']]}))

    # kills: empty-cluster-undone

    def test_removing_the_last_member_undoes_the_cluster(self):
        """An empty cluster has nothing to contain and no hull to draw. Undone
        rather than deleted, because what the meeting grouped is evidence."""
        self.active()
        only = self.note('One')
        group = self.accept(self.cluster([only]))

        result = self.command('cluster.membership', {'cluster_id': group['id'],
                                                     'expected_revision': group['revision'],
                                                     'remove': [only['id']]})
        self.assertEqual([], result['members'])
        self.assertEqual('undone', result['item']['data']['status'])

        # Its members are free again, and the record is still there to read.
        self.assertEqual('cluster', self.accept(self.cluster([only]))['data']['form'])
        self.assertIn(group['id'], [r['id'] for r in
                                    self.service.snapshot(self.sid, self.token)['records']])

    def test_an_undone_cluster_takes_no_further_membership_changes(self):
        self.active()
        only = self.note('One')
        group = self.accept(self.cluster([only]))
        emptied = self.command('cluster.membership', {'cluster_id': group['id'],
                                                      'expected_revision': group['revision'],
                                                      'remove': [only['id']]})['item']
        self.refuses('item_undone', lambda: self.command('cluster.membership', {
            'cluster_id': group['id'], 'expected_revision': emptied['revision'],
            'add': [only['id']]}))


if __name__ == '__main__':
    unittest.main()
