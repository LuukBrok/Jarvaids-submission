"""One test per guard, each written so that removing the guard fails it.

The existing suite covers the happy path of every feature and almost none of the
refusals. `tests/mutation_check.py` measured that: ten guards could be deleted
with all forty-five tests still green, including the credential check on the
deletion receipt and the rule that stops the last facilitator demoting
themselves out of the session.

These tests exist to make `mutation_check.py` exit 0. Each one names the mutant
it kills, so when a guard changes shape you can see which test has to move with
it. If you add a guard, add a mutant and a test in the same commit.

Where a limit is a constant, the test lowers it on the instance rather than
building a thousand records. The guard is the subject, not the number.
"""
import base64
import secrets
import shutil
import struct
import unittest
import zlib
from pathlib import Path

from genai_server.adapters import ExtractionOutput, FixtureExtractor
from genai_server.service import Service
from genai_server.validation import Problem


def png(width=1, height=1):
    def chunk(kind, data):
        return (struct.pack('>I', len(data)) + kind + data
                + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff))
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b'\x00' + b'\xff' * (3 * width)))
            + chunk(b'IEND', b''))


class RenamedFixture(FixtureExtractor):
    """A reconfigured provider, counting what it was asked to look at.

    The count is the point. `FixtureExtractor.extract` hardcodes its provider
    name, so a job run by this adapter fails either way, with the same
    `adapter_failed` category. What the guard actually defends is that the
    photograph is never handed to a provider nobody queued, and only the call
    count shows that.
    """
    name = 'other-provider'

    def __init__(self):
        self.calls = 0

    def extract(self, request):
        self.calls += 1
        return super().extract(request)


class AnnotatedReading(FixtureExtractor):
    """An adapter that reports confidence and colour, which the fixture never does.

    It keeps the fixture's name so the queued job still matches it. Every note
    gets the same annotation, because the guard is about the shape the server
    accepts, not about what a real model would say.
    """
    def __init__(self, confidence=None, colour=None):
        self.confidence = confidence
        self.colour = colour

    def extract(self, request):
        output = super().extract(request)
        notes = tuple(dict(n, confidence=self.confidence, colour=self.colour) for n in output.notes)
        return ExtractionOutput(notes=notes, provider=output.provider, model=output.model,
                                synthetic=output.synthetic, usage=output.usage)


class GuardTests(unittest.TestCase):
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

    # helpers, mirroring tests/test_service.py so the two read the same way

    def cmd(self, op, payload=None, token=None, key=None):
        payload=dict(payload or {})
        if op=='session.activate':payload.setdefault('expected_session_revision',self.service.snapshot(self.sid,self.token)['session']['revision'])
        if op=='participant.role':
            payload.setdefault('expected_roster_revision',self.service.snapshot(self.sid,self.token)['session']['roster_revision'])
        key=key or secrets.token_hex(16);sequence=None
        if op in self.service.CONTROL_COMMANDS:
            if not hasattr(self,'control_intents'):self.control_intents={}
            sequence=self.control_intents.setdefault(key,self.service.snapshot(self.sid,token or self.token)['next_control_sequence'])
        return self.service.command(self.sid, token or self.token,key, op, payload or {},sequence)['result']

    def active(self, tokens=()):
        version = self.service.snapshot(self.sid, self.token)['session']['policy_version']
        for token in (self.token, *tokens):
            self.cmd('consent.acknowledge', {'policy_version': version}, token)
        self.cmd('session.activate', {'policy_version': version})

    def invite(self, name='Bea', role='participant'):
        token = secrets.token_urlsafe(32)
        capability=secrets.token_urlsafe(32)
        self.cmd('participant.invite', {'invitation':capability,'role':role,
            'expected_roster_revision':self.service.snapshot(self.sid,self.token)['session']['roster_revision']})
        result=self.service.join(self.sid,{'invitation':capability,'token':token,'name':name,'policy_version':1})
        return result['actor_id'], token

    def problem(self, code, call):
        with self.assertRaises(Problem) as ctx:
            call()
        self.assertEqual(code, ctx.exception.code)
        return ctx.exception

    # kills: deletion-receipt-credential

    def test_deletion_receipt_refuses_a_credential_that_is_not_the_deleters(self):
        """After a purge the actors rows are gone, so the receipt is gated only by
        a hash comparison. Without that comparison any string reads the receipt,
        which leaks that a session existed and when it was deleted."""
        self.active()
        self.service.delete_session(self.sid, self.token)

        self.assertEqual('deleted', self.service.snapshot(self.sid, self.token)['state'])
        self.problem('unauthorized',
                     lambda: self.service.snapshot(self.sid, secrets.token_urlsafe(32)))
        self.problem('unauthorized',
                     lambda: self.service.delete_session(self.sid, secrets.token_urlsafe(32)))

    # kills: last-facilitator

    def test_the_only_facilitator_cannot_demote_themselves(self):
        """A session with no facilitator can never be closed, exported or deleted,
        so the demotion has to be refused while they are the only one."""
        self.active()
        me = self.service.snapshot(self.sid, self.token)['actor_id']
        self.problem('last_facilitator',
                     lambda: self.cmd('participant.role', {'actor_id': me, 'role': 'viewer'}))

        # With a replacement promoted first, the same demotion is allowed.
        other_id, other_token = self.invite('Cai')
        self.cmd('participant.role', {'actor_id': other_id, 'role': 'facilitator'})
        self.cmd('participant.role', {'actor_id': me, 'role': 'viewer'})
        roles = {m['name']: m['role'] for m in self.service.snapshot(self.sid, other_token)['members']}
        self.assertEqual('viewer', roles['Facilitator'])
        self.assertEqual('facilitator', roles['Cai'])

    # kills: record-cap

    def test_a_session_cannot_exceed_its_record_cap(self):
        """Fills the real cap rather than lowering it.

        Lowering `MAX_RECORDS` on the instance would shadow the class constant,
        so the test would pass just as well with the constant raised to a number
        no session could ever reach, which is the same as having no cap. Costs
        about 1.3 seconds: each `source.text` writes a source and a proposal, so
        the 1000-record cap is reached in 500 commands.
        """
        self.active()
        made = 0
        # The contract is 1000 records. Deriving the attempt limit from the
        # mutated constant lets a removed cap turn this test into billions of
        # writes and eventually fail for an unrelated quota.
        for index in range(501):
            try:
                self.cmd('source.text', {'text': 'note %d' % index})
                made += 1
            except Problem as problem:
                self.assertEqual('record_capacity', problem.code)
                self.assertEqual(429, problem.status)
                self.assertGreater(made, 0, 'the cap rejected the very first record')
                return
        self.fail('the record cap never rejected anything, so it is not a cap')

    # kills: image-byte-cap

    def test_the_image_budget_can_actually_bind(self):
        """The test below lowers the cap on the instance, because reaching the
        real one needs 20 MB of photographs through a 4 MiB per-image limit, and
        about 55 MB of SQLite writes per suite run. That shadows the class
        constant, so the constant is checked separately here.

        An image budget above the whole-session storage budget can never be the
        binding constraint, so it is not a cap at all.
        """
        self.assertLessEqual(Service.MAX_IMAGE_BYTES, Service.MAX_SESSION_BYTES)

    def test_a_session_cannot_exceed_its_image_byte_cap(self):
        self.service.MAX_IMAGE_BYTES = 10
        self.active()
        problem = self.problem('image_capacity', lambda: self.cmd('source.image', {
            'mime': 'image/png',
            'base64': base64.b64encode(png()).decode(),
            'regions': [{'id': 'region_001', 'box': [0, 0, 1, 1]}]}))
        self.assertEqual(429, problem.status)

    # kills: duplicate-reference

    def test_a_proposal_cannot_reference_the_same_record_twice(self):
        """A duplicate ref would be counted twice by anything that walks refs,
        including the invalidation traversal."""
        self.active()
        item = self.accept(self.cmd('source.text', {'text': 'A note'})['proposal'])
        ref = {'id': item['id'], 'revision': item['revision']}
        self.problem('duplicate_reference', lambda: self.cmd('proposal.create', {
            'proposal_kind': 'relationship', 'text': 'these two', 'refs': [ref, dict(ref)]}))

    def accept(self, proposal):
        return self.cmd('proposal.review', {'proposal_id': proposal['id'],
                                            'expected_revision': proposal['revision'],
                                            'decision': 'accept'})['item']

    # kills: job-terminal

    def test_a_finished_job_cannot_be_cancelled(self):
        """Cancelling a succeeded job would move a terminal record back out of its
        terminal state, and the proposals it already wrote would stay."""
        self.active()
        source = self.cmd('source.image', {
            'mime': 'image/png', 'base64': base64.b64encode(png()).decode(),
            'regions': [{'id': 'region_001', 'box': [0, 0, 1, 1]}]})
        job = self.cmd('extraction.queue', {'source_id': source['id'],
                                            'expected_revision': source['revision']})
        self.service.run_one_job()

        finished = self.service.record(self.sid, self.token, job['id'])
        self.assertEqual('succeeded', finished['data']['status'])
        problem = self.problem('job_terminal', lambda: self.cmd('job.cancel', {
            'job_id': job['id'], 'expected_revision': finished['revision']}))
        self.assertEqual(409, problem.status)

    # kills: events-has-more

    def test_a_full_event_page_reports_that_more_remain(self):
        """A client that pages on has_more stops early if it is hardcoded false,
        and silently never sees the rest of the session."""
        self.active()
        for _ in range(205):
            self.cmd('source.text',{'text':'Pagination fixture'})

        first = self.service.events(self.sid, self.token, 0)
        self.assertEqual(200, len(first['events']), 'expected a full page')
        self.assertTrue(first['has_more'], 'a full page with events behind it must say so')

        rest = self.service.events(self.sid, self.token, first['next_after'])
        self.assertGreater(len(rest['events']), 0)
        self.assertFalse(rest['has_more'], 'the last page must not claim more')

    # kills: recovery-no-automatic-retry

    def test_recovery_requires_manual_retry_after_any_interruption(self):
        """Without the cap an adapter that kills the process is retried forever,
        and with a paid provider each retry is billed."""
        self.active()
        source = self.cmd('source.image', {
            'mime': 'image/png', 'base64': base64.b64encode(png()).decode(),
            'regions': [{'id': 'region_001', 'box': [0, 0, 1, 1]}]})
        job = self.cmd('extraction.queue', {'source_id': source['id'],
                                            'expected_revision': source['revision']})

        self.set_job(job['id'], status='running', attempts=2)
        self.service.recover_jobs()
        self.assertEqual('failed', self.job_status(job['id']),
                         'any interrupted call has an uncertain outcome and must not be requeued')

        self.set_job(job['id'], status='running', attempts=3)
        self.service.recover_jobs()
        self.assertEqual('failed', self.job_status(job['id']),
                         'at the cap it must stop, not requeue')

    def set_job(self, job_id, **fields):
        with self.service.db.transaction() as c:
            record = self.service._get(c, self.sid, job_id, 'job')
            record['data'].update(fields)
            self.service._save(c, self.sid, record, record['data'])

    def job_status(self, job_id):
        return self.service.record(self.sid, self.token, job_id)['data']['status']

    # kills: adapter-changed

    def test_a_result_from_a_reconfigured_adapter_is_refused(self):
        """A job queued under one provider must not be completed by another. The
        provenance on every proposal it would write would name the wrong one."""
        self.active()
        source = self.cmd('source.image', {
            'mime': 'image/png', 'base64': base64.b64encode(png()).decode(),
            'regions': [{'id': 'region_001', 'box': [0, 0, 1, 1]}]})
        job = self.cmd('extraction.queue', {'source_id': source['id'],
                                            'expected_revision': source['revision']})

        extractor = RenamedFixture()
        reconfigured = Service(self.path, extractor=extractor, clock=lambda: self.now)
        reconfigured.run_one_job()

        self.assertEqual(0, extractor.calls,
                         'the photograph reached a provider that was never queued')
        self.assertEqual('failed', self.job_status(job['id']))
        proposals = [r for r in self.service.snapshot(self.sid, self.token)['records']
                     if r['kind'] == 'proposal']
        self.assertEqual([], proposals, 'a refused job must write no proposals')

    # kills: purge-verification

    def test_deletion_fails_loudly_if_a_table_is_not_emptied(self):
        """The verification only fires when a DELETE leaves rows, which cannot
        happen by accident, so it is provoked here. A silent partial purge is the
        worst outcome available: the session reports deleted and the content is
        still on disk."""
        self.active()
        self.accept(self.cmd('source.text', {'text': 'Something private'})['proposal'])

        real_transaction = self.service.db.transaction

        class SkipOneDelete:
            """Passes everything through except the DELETE on `records`."""
            def __init__(self, conn):
                self._conn = conn

            def execute(self, sql, *args, **kwargs):
                if sql.strip().upper().startswith('DELETE FROM RECORDS'):
                    return self._conn.execute('SELECT 1 WHERE 0')
                return self._conn.execute(sql, *args, **kwargs)

            def __getattr__(self, name):
                return getattr(self._conn, name)

        import contextlib

        @contextlib.contextmanager
        def sabotaged():
            with real_transaction() as conn:
                yield SkipOneDelete(conn)

        self.service.db.transaction = sabotaged
        try:
            problem = self.problem('purge_failed',
                                   lambda: self.service.delete_session(self.sid, self.token))
            self.assertEqual(500, problem.status)
        finally:
            self.service.db.transaction = real_transaction

        # The transaction rolled back, so the session is untouched rather than
        # half deleted.
        self.assertEqual('active', self.service.snapshot(self.sid, self.token)['session']['state'])


    # F02: confidence and colour on a reading. Optional, nullable, checked, and
    # never a reason to treat a note as accepted.

    def extracted(self, adapter=None):
        """Run one image extraction and return its proposals."""
        if adapter is not None:
            self.service.extractor = adapter
        self.active()
        source = self.cmd('source.image', {'mime': 'image/png', 'base64': base64.b64encode(png()).decode(),
                                           'regions': [{'id': 'region_a', 'box': [0, 0, 1, 1]}]})
        job = self.cmd('extraction.queue', {'source_id': source['id'], 'expected_revision': source['revision']})
        self.assertTrue(self.service.run_one_job())
        done = self.service.record(self.sid, self.token, job['id'])['data']
        proposals = [self.service.record(self.sid, self.token, pid) for pid in done.get('proposal_ids', [])]
        return done, proposals

    def test_the_fixture_reports_no_confidence_and_no_colour(self):
        """F02 says not to fabricate either in fixtures. The keys are present and
        null, so a client can tell "nobody measured this" from an old record."""
        done, (proposal,) = self.extracted()
        self.assertEqual('succeeded', done['status'])
        self.assertIn('confidence', proposal['data'])
        self.assertIsNone(proposal['data']['confidence'])
        self.assertIn('colour', proposal['data'])
        self.assertIsNone(proposal['data']['colour'])

    def test_a_confident_reading_is_still_provisional_and_carries_to_the_item(self):
        """Confidence is not acceptance authority. A reading at 1.0 waits for a
        person exactly as one at 0.0 does, and what the model said survives
        acceptance so the item can still say where it came from."""
        colour = {'space': 'srgb', 'hex': '#f5d33b', 'source': 'model_reported'}
        _, (proposal,) = self.extracted(AnnotatedReading(1.0, colour))
        self.assertEqual('needs_review', proposal['data']['status'])
        self.assertEqual([], [r for r in self.service.snapshot(self.sid, self.token)['records'] if r['kind'] == 'item'])
        item = self.cmd('proposal.review', {'proposal_id': proposal['id'], 'expected_revision': proposal['revision'],
                                            'decision': 'accept'})['item']
        self.assertEqual(1.0, item['data']['confidence'])
        self.assertEqual(colour, item['data']['colour'])

    # kills: note-confidence-range

    def test_a_confidence_outside_zero_to_one_fails_the_job(self):
        """A score of 1.5 or NaN has no meaning on any scale, and a client
        drawing a bar from it would draw nonsense. The whole reading is refused
        rather than stored with the score dropped, because an adapter emitting
        it is broken in a way that makes its text suspect too."""
        for bad in (1.5, -0.1, True):
            with self.subTest(confidence=bad):
                self.setUp()
                done, proposals = self.extracted(AnnotatedReading(bad))
                self.assertEqual('failed', done['status'])
                self.assertEqual('adapter_failed', done.get('error'))
                self.assertEqual([], proposals)

    def test_a_nan_reading_score_is_refused_before_it_reaches_storage(self):
        """Kept apart from the range test on purpose. Without the guard a NaN
        does not produce a wrong answer, it crashes the worker when the record
        is encoded, and the mutation runner rightly counts a crash as no
        evidence. So this one pins the behaviour, and the range test above is
        the one that proves the guard matters."""
        done, proposals = self.extracted(AnnotatedReading(float('nan')))
        self.assertEqual('failed', done['status'])
        self.assertEqual('adapter_failed', done.get('error'))
        self.assertEqual([], proposals)

    # kills: note-colour-shape

    def test_a_colour_without_a_space_and_a_source_fails_the_job(self):
        """A colour nobody can say the space or the origin of cannot be checked
        against the photograph, so it is refused rather than drawn."""
        for bad in ({'space': 'srgb', 'hex': 'yellow', 'source': 'model_reported'},
                    {'space': 'display-p3', 'hex': '#f5d33b', 'source': 'model_reported'},
                    {'space': 'srgb', 'hex': '#f5d33b', 'source': 'vibes'},
                    {'space': 'srgb', 'hex': '#F5D33B', 'source': 'model_reported'}):
            with self.subTest(colour=bad):
                self.setUp()
                done, proposals = self.extracted(AnnotatedReading(0.5, bad))
                self.assertEqual('failed', done['status'])
                self.assertEqual('adapter_failed', done.get('error'))
                self.assertEqual([], proposals)

    # kills: edited-text-drops-confidence

    def test_retyping_a_reading_clears_the_models_confidence(self):
        """Once a person has retyped the words, the model's score describes text
        that is no longer there. Keeping it would put a model's certainty on a
        person's sentence. Colour stays, because the paper did not change."""
        colour = {'space': 'srgb', 'hex': '#f5d33b', 'source': 'pixel_measured'}
        _, (proposal,) = self.extracted(AnnotatedReading(0.4, colour))
        edited = self.cmd('proposal.edit', {'proposal_id': proposal['id'], 'expected_revision': proposal['revision'],
                                            'text': 'What a person read', 'refs': proposal['data']['refs']})
        self.assertEqual('human_transcribed', edited['data']['reading_status'])
        self.assertIsNone(edited['data'].get('confidence', 'missing'))
        self.assertEqual(colour, edited['data']['colour'])

        _, (second,) = self.extracted(AnnotatedReading(0.9, colour))
        item = self.cmd('proposal.review', {'proposal_id': second['id'], 'expected_revision': second['revision'],
                                            'decision': 'accept'})['item']
        self.assertEqual(0.9, item['data']['confidence'])
        fixed = self.cmd('item.edit', {'item_id': item['id'], 'expected_revision': item['revision'],
                                       'text': 'Corrected by a person', 'refs': item['data']['refs']})['item']
        self.assertIsNone(fixed['data'].get('confidence', 'missing'))
        self.assertEqual(colour, fixed['data']['colour'])


if __name__ == '__main__':
    unittest.main()
