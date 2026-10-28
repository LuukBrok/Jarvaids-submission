"""Session-owned polling. All mutations are transactional; model calls are not."""
import json
import re
import threading
from copy import deepcopy

from .poll_model import SCHEMA
from .validation import Problem, fields, require, text
from .voice_commands import recognise_command


ACTIVE = ('draft', 'open', 'closing')
UNRESOLVED = ('clarify', 'error', 'uncertain')
PENDING = ('queued', 'running')


def words(value):
    return ' '.join(re.findall(r'\w+', value.casefold()))


def control_phrase(value):
    return (recognise_command(value) or {}).get('poll_action')


class PollMixin:
    MAX_POLL_WORK = 80  # Per session, including ignored speech, bounds paid calls.
    MAX_POLL_QUEUE = 24

    def _init_polls(self, model, notice):
        self.poll_model = model
        self.poll_notice = notice or ('Voice AI is not configured. Set ANTHROPIC_API_KEY in .env and restart; manual controls still work.' if model is None else '')
        self.poll_lock = threading.Lock()
        self.handlers.update({
            'poll.edit': self._poll_edit, 'poll.confirm': self._poll_confirm,
            'poll.vote': self._poll_vote, 'poll.resolve': self._poll_resolve,
            'poll.close': self._poll_close, 'poll.finalise': self._poll_finalise,
            'poll.cancel': self._poll_cancel, 'poll.retry': self._poll_retry,
        })
        self._sync_poll_policy()

    def _sync_poll_policy(self):
        # Existing local-only consent must not silently become consent to cloud text.
        enabled = self.poll_model is not None
        with self.db.transaction() as c:
            for row in c.execute("SELECT * FROM sessions WHERE state NOT IN ('deleted','closed')").fetchall():
                s = dict(row)
                marker = next(iter(self._list(c, s['id'], 'poll_policy')), None)
                if not marker and not enabled:
                    continue
                if marker and marker['data']['cloud_text'] == enabled:
                    continue
                if s['state'] == 'active':
                    self._stop_capture(c, s)
                else:
                    c.execute('UPDATE sessions SET revision=revision+1 WHERE id=?', (s['id'],))
                c.execute('UPDATE sessions SET policy_version=policy_version+1 WHERE id=?', (s['id'],))
                if marker:
                    self._save(c, s['id'], marker, {'cloud_text': enabled})
                else:
                    self._new(c, s['id'], 'poll_policy', {'cloud_text': enabled})
                self._event(c, s['id'], 'system', 'policy.poll_changed', {})

    def _poll_capability(self):
        return {'available': self.poll_model is not None, 'notice': self.poll_notice,
                'cloud_text': self.poll_model is not None,
                'provider': getattr(self.poll_model, 'name', None)}

    def _poll_work(self, c, sid, pid):
        return [r for r in self._list(c, sid, 'poll_work') if r['data']['poll_id'] == pid]

    def _poll_ballots(self, c, sid, pid):
        return [r for r in self._list(c, sid, 'poll_ballot') if r['data']['poll_id'] == pid]

    @staticmethod
    def _poll_order(c, sid):
        return c.execute("SELECT coalesce(max(rowid),0) FROM records WHERE session_id=? AND kind='transcript_segment'", (sid,)).fetchone()[0]

    def _poll_editable(self, c, s, a, b, states=ACTIVE):
        self._editor(a)
        self._active(s)
        require(a['consent_version'] == s['policy_version'], 'agreement_incomplete', 'Current agreement is required.', 409)
        poll = self._get(c, s['id'], b['poll_id'], 'poll')
        self._expected(poll, b['expected_revision'])
        require(poll['data']['state'] in states, 'poll_state', 'This poll does not allow that action.', 409)
        return poll

    def _poll_save(self, c, sid, poll, **changes):
        return self._save(c, sid, poll, {**poll['data'], **changes})

    @staticmethod
    def _poll_options(values):
        require(type(values) is list and 2 <= len(values) <= 12, 'poll_options', 'Supply between 2 and 12 distinct choices.')
        labels = [text(v, 'option', 160).strip() for v in values]
        require(len({words(v) for v in labels}) == len(labels) and all(words(v) for v in labels),
                'poll_options', 'Choices must be distinct and contain words or numbers.')
        return [{'id': f'option_{i+1:02d}', 'label': label} for i, label in enumerate(labels)]

    def _poll_edit(self, c, s, a, b):
        fields(b, ('poll_id', 'expected_revision', 'question', 'options'))
        poll = self._poll_editable(c, s, a, b, ('draft',))
        return self._poll_save(c, s['id'], poll, question=text(b['question'], 'question', 500).strip(),
                               options=self._poll_options(b['options']), epoch=poll['data']['epoch']+1,
                               prompt='Check the question and choices, then start voting.', error=None,
                               definition_origin='human', last_editor=a['id'])

    def _poll_open(self, c, s, poll, actor_id, boundary):
        require(poll['data']['question'] and len(poll['data']['options']) >= 2,
                'poll_incomplete', 'Set the question and at least two choices first.', 409)
        row = c.execute("SELECT data FROM records WHERE session_id=? AND kind='transcript_segment' AND rowid=?", (s['id'], boundary)).fetchone()
        opening = json.loads(row['data']) if row else {}
        return self._poll_save(c, s['id'], poll, state='open', opened_after=boundary,
                               opened_capture_id=opening.get('capture_id'), opened_capture_time=opening.get('captured_at_ms'),
                               **({'automatic_opened':True} if self.automatic_workspace else {'confirmed_by':actor_id}),
                               prompt='Voting is open. Say your choice, or use the controls.', error=None)

    def _poll_confirm(self, c, s, a, b):
        fields(b, ('poll_id', 'expected_revision'))
        poll = self._poll_editable(c, s, a, b, ('draft',))
        # A click opens from now, so earlier submitted speech is not backfilled.
        poll['data']['epoch'] += 1
        return self._poll_open(c, s, poll, a['id'], self._poll_order(c, s['id']))

    def _poll_cast(self, c, s, poll, profile_id, option_id, actor_id, source_id, order, provenance=None):
        self._get(c, s['id'], profile_id, 'speaker_profile')
        require(option_id is None or option_id in {o['id'] for o in poll['data']['options']},
                'poll_option', 'Choose an option from this poll.')
        old = next((r for r in self._poll_ballots(c, s['id'], poll['id']) if r['data']['speaker_profile_id'] == profile_id), None)
        source = self._get(c, s['id'], source_id, 'transcript_segment')['data'] if source_id else {}
        if old and order < old['data']['source_order']:
            return old  # A delayed interpretation cannot undo a later manual correction.
        if old and provenance and source.get('capture_id') and source.get('capture_id') == old['data'].get('capture_id'):
            earlier, later = source.get('captured_at_ms'), old['data'].get('captured_at_ms')
            if earlier is not None and later is not None and earlier < later:
                return old
        data = {'poll_id': poll['id'], 'speaker_profile_id': profile_id, 'option_id': option_id,
                'source_id': source_id, 'source_order': order, 'operator_id': actor_id,
                'origin': 'model' if provenance else 'human', 'provenance': provenance,
                'capture_id': source.get('capture_id'), 'captured_at_ms': source.get('captured_at_ms'),
                'status': 'provisional' if provenance else 'accepted', 'updated_at': self.clock()}
        if old:
            return self._save(c, s['id'], old, data)
        return self._new(c, s['id'], 'poll_ballot', data)

    def _poll_vote(self, c, s, a, b):
        fields(b, ('poll_id', 'expected_revision', 'speaker_profile_id', 'option_id'))
        poll = self._poll_editable(c, s, a, b, ('open','closed') if self.automatic_workspace else ('open',))
        ballot = self._poll_cast(c, s, poll, b['speaker_profile_id'], b['option_id'], a['id'], None,
                                 self._poll_order(c, s['id']) + 0.5)
        self._poll_auto_finish(c,s,self._poll_save(c, s['id'], poll, last_editor=a['id']))
        return ballot

    def _poll_resolve(self, c, s, a, b):
        fields(b, ('poll_id', 'expected_revision', 'work_id', 'dismiss'), ('speaker_profile_id', 'option_id'))
        poll = self._poll_editable(c, s, a, b, (*ACTIVE,'closed') if self.automatic_workspace else ACTIVE)
        work = self._get(c, s['id'], b['work_id'], 'poll_work')
        require(work['data']['poll_id'] == poll['id'] and work['data']['status'] in UNRESOLVED,
                'poll_work_state', 'That reply no longer needs review.', 409)
        require(type(b['dismiss']) is bool, 'invalid_boolean', 'dismiss must be a boolean.')
        if not b['dismiss']:
            require(poll['data']['state'] in (('open','closing','closed') if self.automatic_workspace else ('open','closing')), 'poll_state', 'Open voting before assigning a ballot.', 409)
            require('speaker_profile_id' in b and 'option_id' in b, 'missing_fields', 'Choose a speaker and option.')
            self._poll_cast(c, s, poll, b['speaker_profile_id'], b['option_id'], a['id'], work['data']['source_id'],
                            self._poll_order(c, s['id']) + 0.5)
        self._save(c, s['id'], work, {**work['data'], 'status': 'dismissed' if b['dismiss'] else 'resolved', 'reviewed_by': a['id']})
        return self._poll_auto_finish(c,s,self._poll_save(c, s['id'], poll, last_editor=a['id']))

    def _poll_close(self, c, s, a, b):
        fields(b, ('poll_id', 'expected_revision'))
        poll = self._poll_editable(c, s, a, b, ('open',))
        poll = self._poll_save(c, s['id'], poll, state='closing', close_after=self._poll_order(c, s['id']),
                               prompt='Voting has stopped. Review outstanding replies, then accept the results.')
        return self._poll_auto_finish(c, s, poll)

    def _poll_auto_finish(self, c, s, poll):
        if not self.automatic_workspace or poll['data']['state'] not in ('closing','closed'): return poll
        if any(w['data']['status'] in PENDING for w in self._poll_work(c,s['id'],poll['id'])): return poll
        counts={o['id']:0 for o in poll['data']['options']}
        for ballot in self._poll_ballots(c,s['id'],poll['id']):
            if ballot['data']['option_id'] is not None: counts[ballot['data']['option_id']]+=1
        return self._poll_save(c,s['id'],poll,state='closed',counts=counts,automatic=True,
            prompt='Voting finished. Unclear replies are shown separately and are not counted.')

    def _poll_accept(self, c, s, a, poll):
        work = self._poll_work(c, s['id'], poll['id'])
        require(not any(r['data']['status'] in (*PENDING, *UNRESOLVED) for r in work),
                'poll_pending', 'Wait for processing and resolve or exclude outstanding replies before accepting.', 409)
        counts = {o['id']: 0 for o in poll['data']['options']}
        for ballot in self._poll_ballots(c, s['id'], poll['id']):
            if ballot['data']['option_id'] is not None:
                counts[ballot['data']['option_id']] += 1
            self._save(c, s['id'], ballot, {**ballot['data'], 'status': 'accepted', 'accepted_by': a['id']})
        return self._poll_save(c, s['id'], poll, state='closed', counts=counts, accepted_by=a['id'],
                               accepted_at=self.clock(), prompt='Results accepted by the team. A tie remains a tie.')

    def _poll_finalise(self, c, s, a, b):
        fields(b, ('poll_id', 'expected_revision'))
        poll = self._poll_editable(c, s, a, b, ('closing',))
        return self._poll_accept(c, s, a, poll)

    def _poll_cancel(self, c, s, a, b):
        fields(b, ('poll_id', 'expected_revision'))
        poll = self._poll_editable(c, s, a, b)
        for work in self._poll_work(c, s['id'], poll['id']):
            if work['data']['status'] in (*PENDING, *UNRESOLVED):
                self._save(c, s['id'], work, {**work['data'], 'status': 'cancelled'})
        return self._poll_save(c, s['id'], poll, state='cancelled', epoch=poll['data']['epoch']+1,
                               prompt='Poll cancelled. Its history is retained.')

    def _poll_retry(self, c, s, a, b):
        fields(b, ('poll_id', 'expected_revision', 'work_id', 'acknowledge_unknown_cost'))
        poll = self._poll_editable(c, s, a, b)
        require(self.poll_model is not None, 'poll_ai_unavailable', self.poll_notice, 409)
        require(b['acknowledge_unknown_cost'] is True, 'poll_retry_ack', 'A previous API call may have incurred cost. Acknowledge before retrying.')
        work = self._get(c, s['id'], b['work_id'], 'poll_work')
        require(work['data']['poll_id'] == poll['id'] and work['data']['status'] in ('error', 'uncertain'),
                'poll_work_state', 'Only failed or uncertain interpretations can be retried.', 409)
        require(work['data']['epoch'] == poll['data']['epoch'], 'poll_stale', 'The poll definition changed; correct it manually.', 409)
        self._save(c, s['id'], work, {**work['data'], 'status': 'queued', 'error': None, 'retried_by': a['id']})
        return self._poll_save(c, s['id'], poll, prompt='Retry queued; previous usage may be unknown.')

    def _poll_heard(self, c, s, a, source):
        """Called exactly once in the same transaction that stores final ASR."""
        data = source['data']
        if data['status'] != 'final' or data['provenance']['synthetic']:
            return
        poll = next((r for r in self._list(c, s['id'], 'poll') if r['data']['state'] in ACTIVE), None)
        heard = data.get('voice_command') or {}
        creating = heard.get('status') == 'recognised' and heard.get('intent') == 'voting' and not heard.get('poll_action')
        if creating:
            if poll:
                self._poll_save(c, s['id'], poll, prompt='A poll is already active. Finish or cancel it before starting another.')
                return
            poll = self._new(c, s['id'], 'poll', {
                'state': 'draft', 'question': '', 'options': [], 'epoch': 1,
                'command_source_id': source['id'], 'author_id': a['id'],
                'created_at': self.clock(), 'definition_origin': 'model', 'source_ids': [source['id']],
                'prompt': 'Finding the question and choices…', 'error': None,
                'capture_id': data.get('capture_id'), 'capture_actor_id': a['id'],
            })
        if not poll:
            return
        # V1 is one room microphone. A second device cannot duplicate its ballots.
        if not creating and a['id'] != poll['data']['capture_actor_id']:
            return
        if not creating and poll['data']['state'] != 'draft' and data.get('capture_id') == poll['data'].get('opened_capture_id'):
            stamp, opening = data.get('captured_at_ms'), poll['data'].get('opened_capture_time')
            if stamp is not None and opening is not None and stamp <= opening:
                return
        order = self._poll_order(c, s['id'])
        control = heard.get('poll_action') if heard.get('status') == 'recognised' else control_phrase(data['text'])
        if control == 'close' and poll['data']['state'] == 'open':
            self._poll_close(c,s,a,{'poll_id':poll['id'],'expected_revision':poll['revision']})
            return
        if control == 'cancel':
            self._poll_cancel(c, s, a, {'poll_id': poll['id'], 'expected_revision': poll['revision']})
            return
        if control == 'finalise' and poll['data']['state'] == 'closing':
            try:
                self._poll_accept(c, s, a, poll)
            except Problem as error:
                self._poll_save(c, s['id'], poll, prompt=error.message)
            return
        if control or poll['data']['state'] == 'closing':
            return
        if self.poll_model is None:
            if creating:
                self._poll_save(c, s['id'], poll, error='ai_unavailable', prompt=self.poll_notice)
            return
        all_work = self._list(c, s['id'], 'poll_work')
        if len(all_work) >= self.MAX_POLL_WORK or sum(w['data']['status'] in PENDING for w in all_work) >= self.MAX_POLL_QUEUE:
            self._poll_save(c, s['id'], poll, error='capacity', prompt='AI processing limit reached. Use manual controls for this poll.')
            return
        # Unknown votes are interpreted but cannot reach a named tally.
        self._new(c, s['id'], 'poll_work', {
            'poll_id': poll['id'], 'source_id': source['id'], 'source_order': order,
            'epoch': poll['data']['epoch'], 'status': 'queued', 'actor_id': a['id'],
            'session_revision': s['revision'], 'policy_version': s['policy_version'],
            'captured_at_ms': data.get('captured_at_ms'),
            'created_at': self.clock(), 'error': None,
        })

    def recover_poll_jobs(self):
        with self.db.transaction() as c:
            for row in c.execute("SELECT id FROM sessions WHERE state!='deleted'").fetchall():
                for work in self._list(c, row['id'], 'poll_work'):
                    if work['data']['status'] == 'running' or self.poll_model is None and work['data']['status'] == 'queued':
                        self._save(c, row['id'], work, {**work['data'], 'status': 'uncertain',
                            'error': 'Interrupted AI request; usage may be unknown. Review, exclude or retry explicitly.'})
                        self._event(c, row['id'], 'system', 'poll.recovered', {})

    def _poll_request(self, c, s, poll, source):
        # The input contains text and opaque IDs only, never voice embeddings or names.
        segments = self._list(c, s['id'], 'transcript_segment')
        index = next(i for i, r in enumerate(segments) if r['id'] == source['id'])
        recent = segments[:index+1][-40:]
        stamp = source['data'].get('captured_at_ms')
        recent = [r for r in recent if r['data']['status'] == 'final' and not r['data']['provenance']['synthetic']
                  and (stamp is None or r['data'].get('capture_id') == source['data'].get('capture_id') and
                       r['data'].get('captured_at_ms', stamp) >= stamp-120000)]
        if poll['data']['state'] != 'draft':
            recent = recent[-4:]
        def line(r):
            return {'id': r['id'], 'text': r['data']['text'][:4000],
                    'speaker_id': r['data'].get('speaker_profile_id')}
        pending = [w for w in self._poll_work(c, s['id'], poll['id']) if w['data']['status'] == 'clarify']
        speaker_id = source['data'].get('speaker_profile_id')
        own_pending = []
        if speaker_id:
            for w in pending:
                prior = self._get(c, s['id'], w['data']['source_id'], 'transcript_segment')
                if prior['data'].get('speaker_profile_id') == speaker_id:
                    own_pending.append({'source': line(prior), 'prompt': w['data'].get('prompt', '')})
        return {'phase': 'draft' if poll['data']['state'] == 'draft' else 'open',
                'poll': {'question': poll['data']['question'], 'options': poll['data']['options']},
                'current': line(source), 'context': [line(r) for r in recent],
                'unresolved_for_speaker': own_pending[-2:]}

    @staticmethod
    def _poll_validate(output, request):
        data = output.data
        require(type(data) is dict and set(data) == set(SCHEMA['required']), 'poll_model_output', 'AI response had an invalid structure.')
        require(type(data['action']) is str and data['action'] in SCHEMA['properties']['action']['enum'], 'poll_model_output', 'AI action is unsupported.')
        for key in ('question', 'option_id', 'prompt', 'quote'):
            text(data[key], key, 1000, empty=True)
        require(type(data['options']) is list and all(type(v) is str for v in data['options']) and len(data['options']) <= 12,
                'poll_model_output', 'Invalid AI choices.')
        ids = data['source_ids']
        supplied = {r['id']: r['text'] for r in [*request['context'], request['current'],
                    *(p['source'] for p in request.get('unresolved_for_speaker', []))]}
        require(type(ids) is list and len(ids) <= 40 and all(type(i) is str and i in supplied for i in ids),
                'poll_model_output', 'AI cited unknown evidence.')
        if data['action'] != 'ignore':
            require(bool(ids), 'poll_model_output', 'AI interpretation needs source evidence.')
        if data['action'] in ('confirm', 'select', 'remove'):
            require(request['current']['id'] in ids and bool(words(data['quote'])) and words(data['quote']) in words(request['current']['text']),
                    'poll_model_output', 'AI interpretation was not grounded in the current utterance.')
        if data['action'] == 'select':
            require(data['option_id'] in {o['id'] for o in request['poll']['options']}, 'poll_model_output', 'AI selected an unknown option.')
        if data['action'] == 'draft':
            text(data['question'], 'question', 500)
            options = PollMixin._poll_options(data['options'])
            cited = ' ' + words(' '.join(supplied[i] for i in ids)) + ' '
            binary = {words(o['label']) for o in options} == {'yes', 'no'}
            require(binary or all(' ' + words(o['label']) + ' ' in cited for o in options),
                    'poll_model_output', 'AI proposed choices not present in the cited discussion.')
        return data

    def _poll_authority(self, c, s, work):
        a = c.execute('SELECT * FROM actors WHERE session_id=? AND id=?', (s['id'], work['data']['actor_id'])).fetchone()
        return (s['state'] == 'active' and s['lease'] > self.clock() and s['expires'] > self.clock()
                and s['revision'] == work['data']['session_revision'] and s['policy_version'] == work['data']['policy_version']
                and a is not None and a['role'] in ('facilitator', 'participant') and a['consent_version'] == s['policy_version'])

    def run_one_poll_job(self):
        # Serial processing preserves utterance order, including voice confirmation.
        if not self.poll_lock.acquire(blocking=False):
            return False
        try:
            return self._run_poll_job()
        finally:
            self.poll_lock.release()

    def _run_poll_job(self):
        if self.poll_model is None:
            return False
        with self.db.transaction() as c:
            row = c.execute("SELECT session_id,id FROM records WHERE kind='poll_work' AND json_extract(data,'$.status')='queued' ORDER BY rowid LIMIT 1").fetchone()
            if row is None:
                return False
            sid = row['session_id']
            session = c.execute('SELECT * FROM sessions WHERE id=?', (sid,)).fetchone()
            work = self._get(c, sid, row['id'], 'poll_work')
            poll = self._get(c, sid, work['data']['poll_id'], 'poll')
            s = dict(session)
            wd, pd = work['data'], poll['data']
            stale = (not self._poll_authority(c, s, work) or pd['state'] not in ACTIVE or wd['epoch'] != pd['epoch']
                     or pd['state'] != 'draft' and wd['source_order'] <= pd.get('opened_after', 0)
                     or pd['state'] == 'closing' and wd['source_order'] > pd['close_after'])
            if stale:
                self._save(c, sid, work, {**wd, 'status': 'stale'})
                self._event(c, sid, 'system', 'poll.work_stale', {})
                return True
            source = self._get(c, sid, wd['source_id'], 'transcript_segment')
            request = self._poll_request(c, s, poll, source)
            work = self._save(c, sid, work, {**wd, 'status': 'running', 'started_at': self.clock()})
            self._event(c, sid, 'system', 'poll.processing', {})
        output = None
        error = None
        try:
            output = self.poll_model.interpret(request)
            interpreted = self._poll_validate(output, request)
            require(not output.synthetic, 'poll_synthetic', 'Synthetic interpretations cannot become live votes.')
        except Exception:
            error = 'AI interpretation failed or could not be validated. Review or retry explicitly; usage may be unknown.'
        try:
            with self.db.transaction() as c:
                session = c.execute('SELECT * FROM sessions WHERE id=?', (sid,)).fetchone()
                if session is None or session['state'] == 'deleted':
                    return True
                s = dict(session)
                work = self._get(c, sid, work['id'], 'poll_work')
                poll = self._get(c, sid, poll['id'], 'poll')
                pd, wd = poll['data'], {**work['data'], 'completed_at': self.clock()}
                provenance = None if output is None else {'producer': output.provider, 'model_version': output.model,
                                                         'usage': output.usage, 'synthetic': output.synthetic}
                stale = (wd['status'] != 'running' or not self._poll_authority(c, s, work) or pd['epoch'] != wd['epoch']
                         or pd['state'] not in ACTIVE or request['phase'] == 'draft' and pd['state'] != 'draft'
                         or pd['state'] == 'closing' and wd['source_order'] > pd['close_after'])
                if stale:
                    self._save(c, sid, work, {**wd, 'status': 'stale', 'provenance': provenance})
                elif error:
                    self._save(c, sid, work, {**wd, 'status': 'error', 'error': error, 'provenance': provenance})
                    self._poll_save(c, sid, poll, error='interpretation_failed', prompt=error)
                else:
                    self._apply_poll_output(c, s, poll, work, source, interpreted, provenance)
                self._poll_auto_finish(c,s,self._get(c,sid,poll['id'],'poll'))
                self._event(c, sid, 'system', 'poll.interpreted', {})
                self._budget(c, sid)
        except Exception:
            # The remote request may have completed. Never automatically call it again.
            # Startup recovery turns a retained running record into explicit uncertainty.
            with self.db.transaction() as c:
                row = c.execute('SELECT state FROM sessions WHERE id=?', (sid,)).fetchone()
                if row and row['state'] != 'deleted':
                    current = self._get(c, sid, work['id'], 'poll_work')
                    if current['data']['status'] == 'running':
                        self._save(c, sid, current, {**current['data'], 'status': 'uncertain',
                            'error': 'Interpretation could not be committed; review manually or retry with possible extra cost.'})
                        self._event(c, sid, 'system', 'poll.uncertain', {})
        return True

    def _apply_poll_output(self, c, s, poll, work, source, result, provenance):
        pid, sid = poll['id'], s['id']
        wd, pd, sd = work['data'], poll['data'], source['data']
        action = result['action']
        status, prompt = 'done', result['prompt']
        if pd['state'] == 'draft':
            if action == 'draft':
                poll = self._poll_save(c, sid, poll, question=text(result['question'], 'question', 500).strip(),
                    options=self._poll_options(result['options']), source_ids=result['source_ids'],
                    definition_origin='model', prompt=prompt or 'Check the draft, then say: yes, start voting.', error=None)
                if self.automatic_workspace and poll['data']['question'] and len(poll['data']['options']) >= 2:
                    self._poll_open(c,s,poll,wd['actor_id'],wd['source_order'])
            elif action == 'confirm':
                poll = self._poll_open(c, s, poll, wd['actor_id'], wd['source_order'])
            elif action != 'ignore':
                status = 'clarify'
                poll = self._poll_save(c, sid, poll, prompt=prompt or 'What are we voting on, and what are the choices?')
        elif action in ('select', 'remove'):
            profile = sd.get('speaker_profile_id') if sd.get('attribution') == 'voice_identified' else None
            # Synthetic voice profiles/matches cannot stand in for a real voter.
            speaker_provenance = sd['provenance'].get('speaker', {})
            if not profile or speaker_provenance.get('synthetic', True):
                status, prompt = 'clarify', 'A choice was heard, but the speaker was not reliably identified. Assign it or exclude it.'
            else:
                ballot = self._poll_cast(c, s, poll, profile, result['option_id'] if action == 'select' else None,
                                         wd['actor_id'], source['id'], wd['source_order'], provenance)
                if ballot['data']['source_order'] != wd['source_order']:
                    self._save(c, sid, work, {**wd, 'status': 'stale', 'interpretation': result, 'provenance': provenance})
                    self._poll_save(c, sid, poll, prompt='An earlier reply was ignored because a later choice or manual correction is already recorded.')
                    return
                # A clear follow-up by this same voice resolves its earlier ambiguous replies.
                for earlier in self._poll_work(c, sid, pid):
                    if earlier['data']['status'] != 'clarify':
                        continue
                    prior = self._get(c, sid, earlier['data']['source_id'], 'transcript_segment')
                    if prior['data'].get('speaker_profile_id') == profile:
                        self._save(c, sid, earlier, {**earlier['data'], 'status': 'resolved', 'resolved_by_source': source['id']})
                poll = self._poll_save(c, sid, poll, error=None, prompt='Choice updated. Voice-inferred votes remain provisional until results are accepted.')
        elif action not in ('ignore',):
            status = 'clarify'
            prompt = prompt or 'Which single option do you choose?'
        self._save(c, sid, work, {**wd, 'status': status, 'interpretation': result,
                                  'prompt': prompt, 'provenance': provenance})
