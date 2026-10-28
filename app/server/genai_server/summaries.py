"""Persisted rolling summaries; model calls never hold the session write lock."""
from copy import deepcopy
import json
import threading
from .summary_model import label, validate_result
from .validation import Problem, fields, integer, require, text


class SummaryMixin:
    SUMMARY_WORDS = 60
    SUMMARY_EXTRA_WORDS = 40

    def _init_summaries(self, model):
        self.summary_model = model
        self.summary_lock = threading.Lock()
        self._summary_policy_update()
        self.handlers.update({'summary.configure': self._summary_configure,
            'summary.flush': self._summary_flush, 'summary.retry': self._summary_retry})

    def _summary_policy_update(self):
        cloud = self.summary_model is not None and not getattr(self.summary_model, 'local', True)
        with self.db.transaction() as c:
            for row in c.execute("SELECT * FROM sessions WHERE state NOT IN ('deleted','closed')").fetchall():
                session = dict(row)
                policy = next(iter(self._list(c, session['id'], 'summary_policy')), None)
                if (policy is None and not cloud) or (policy and policy['data']['cloud_text'] == cloud): continue
                if session['state'] == 'active': self._stop_capture(c, session)
                else: c.execute('UPDATE sessions SET revision=revision+1 WHERE id=?', (session['id'],))
                c.execute('UPDATE sessions SET policy_version=policy_version+1 WHERE id=?', (session['id'],))
                if policy: self._save(c, session['id'], policy, {'cloud_text': cloud})
                else: self._new(c, session['id'], 'summary_policy', {'cloud_text': cloud})
                self._event(c, session['id'], 'system', 'summary.policy_changed', {})

    def _summary_state(self, c, sid):
        return next(iter(self._list(c, sid, 'summary_state')), None)

    def _summary_ensure(self, c, sid):
        return self._summary_state(c, sid) or self._new(c, sid, 'summary_state', {
            'enabled': True, 'agenda': [], 'cursor': 0, 'force': False,
            'buffered_words': 0, 'last_topic_id': None, 'message': 'Waiting for discussion.'})

    def _summary_configure(self, c, s, a, b):
        fields(b, ('agenda', 'enabled'))
        self._editor(a)
        require(self.summary_model is not None, 'summary_unavailable', 'The local summariser is not configured.', 409)
        require(type(b['enabled']) is bool and type(b['agenda']) is list and len(b['agenda']) <= 30,
                'summary_config', 'Supply a boolean and at most 30 agenda topics.')
        agenda = [text(v, 'agenda topic', 160).strip() for v in b['agenda']]
        state = self._summary_ensure(c, s['id'])
        return self._save(c, s['id'], state, {**state['data'], 'agenda': agenda, 'enabled': b['enabled']})

    def _summary_flush(self, c, s, a, b):
        fields(b)
        self._editor(a); self._active(s)
        require(self.summary_model is not None, 'summary_unavailable', 'The local summariser is not configured.', 409)
        state = self._summary_ensure(c, s['id'])
        return self._save(c, s['id'], state, {**state['data'], 'force': True, 'message': 'Summary update requested.'})

    def _summary_retry(self, c, s, a, b):
        fields(b, ('work_id', 'expected_revision'))
        self._editor(a); self._active(s)
        work = self._get(c, s['id'], b['work_id'], 'summary_work'); self._expected(work, b['expected_revision'])
        require(work['data']['status'] in ('error', 'blocked'), 'summary_work', 'Only failed summary work can be retried.', 409)
        require(work['data']['attempts'] < 4, 'summary_attempts', 'Correct the local model before retrying again.', 409)
        return self._save(c, s['id'], work, {**work['data'], 'status': 'queued', 'error': None})

    def recover_summary_jobs(self):
        with self.db.transaction() as c:
            rows = c.execute("SELECT * FROM records WHERE kind='summary_work'").fetchall()
            for row in rows:
                data = json.loads(row['data'])
                if data['status'] == 'running':
                    work = self._get(c, row['session_id'], row['id'])
                    self._save(c, row['session_id'], work, {**data, 'status': 'error',
                        'error': 'The summariser was interrupted. Retry this batch explicitly.'})
                    self._event(c, row['session_id'], 'system', 'summary.interrupted', {})

    def _summary_queue(self, c, s, state):
        works = self._list(c, s['id'], 'summary_work')
        if sum(w['data']['status'] in ('queued', 'running', 'error', 'blocked') for w in works) >= 24:
            return state
        rows = c.execute("SELECT rowid,id,revision,data FROM records WHERE session_id=? "
            "AND kind='transcript_segment' AND rowid>? ORDER BY rowid", (s['id'], state['data']['cursor'])).fetchall()
        lines, words, cursor, ready = [], 0, state['data']['cursor'], False
        force = state['data']['force']
        for row in rows:
            d = json.loads(row['data']); cursor = row['rowid']
            command = d.get('voice_command') or {}
            if command.get('status') == 'recognised':
                if command.get('intent') == 'summary': force = True
                continue
            if d.get('status') != 'final' or not d.get('text') or d.get('provenance', {}).get('synthetic', True):
                continue
            lines.append({'id': row['id'], 'revision': row['revision'], 'text': d['text'],
                'created_at': d['created_at'], 'speaker': d.get('speaker_name') or 'Unknown speaker'})
            words += len(d['text'].split())
            ready = words >= self.SUMMARY_WORDS and (d['text'].rstrip().rstrip('\"\')').endswith(('.', '?', '!'))
                or words >= self.SUMMARY_WORDS + self.SUMMARY_EXTRA_WORDS)
            if ready or len(lines) >= 24 or sum(len(v['text']) for v in lines) >= 10000:
                ready = True
                break
        ready = ready or force
        if lines and ready:
            self._new(c, s['id'], 'summary_work', {'status': 'queued', 'sources': [
                {'id': l['id'], 'revision': l['revision']} for l in lines],
                'attempts': 0, 'created_at': self.clock(), 'error': None})
            return self._save(c, s['id'], state, {**state['data'], 'cursor': cursor,
                'force': False, 'buffered_words': 0, 'message': 'Summary is catching up.'})
        changes = {**state['data'], 'buffered_words': words, 'force': False}
        if not lines: changes['cursor'] = cursor
        if changes != state['data']: state = self._save(c, s['id'], state, changes)
        return state

    def _summary_request(self, c, sid, state, work):
        lines = []
        for ref in work['data']['sources']:
            r = self._get(c, sid, ref['id'], 'transcript_segment'); self._expected(r, ref['revision'])
            lines.append({'id': r['id'], 'revision': r['revision'], 'text': r['data']['text'],
                'created_at': r['data']['created_at'], 'speaker': r['data'].get('speaker_name') or 'Unknown speaker',
                'speaker_verified': bool(r['data'].get('speaker_name')) and
                    (r['data'].get('input_method') == 'typed' or
                     r['data'].get('attribution') == 'voice_identified' and bool(r['data'].get('speaker_profile_id')))})
        topics = [{'id': r['id'], 'revision': r['revision'], **r['data']} for r in self._list(c, sid, 'summary_topic')]
        require(len(topics) < 60, 'summary_capacity', 'Topic limit reached. Export this meeting and start another.', 429)
        return {'lines': lines, 'topics': topics, 'agenda': state['data']['agenda']}

    def run_one_summary_job(self):
        if self.summary_model is None or not self.summary_lock.acquire(blocking=False): return False
        try: return self._run_summary_job()
        finally: self.summary_lock.release()

    def _run_summary_job(self):
        chosen = None
        with self.db.transaction() as c:
            for row in c.execute("SELECT * FROM sessions WHERE state='active' AND expires>? AND lease>? ORDER BY rowid",
                    (self.clock(), self.clock())).fetchall():
                s = dict(row); existed = self._summary_state(c, s['id']) is not None
                state = self._summary_ensure(c, s['id'])
                if not state['data']['enabled']: continue
                before = state['revision']; state = self._summary_queue(c, s, state)
                if not existed or state['revision'] != before: self._event(c, s['id'], 'system', 'summary.buffered', {})
                works = self._list(c, s['id'], 'summary_work')
                work = next((w for w in works if w['data']['status'] != 'done'), None)
                if not work or work['data']['status'] != 'queued': continue
                actor = c.execute("SELECT * FROM actors WHERE session_id=? AND role='facilitator' AND consent_version=? LIMIT 1",
                    (s['id'], s['policy_version'])).fetchone()
                if actor is None: continue
                work = self._save(c, s['id'], work, {**work['data'], 'status': 'running', 'attempts': work['data']['attempts'] + 1})
                try: request = self._summary_request(c, s['id'], state, work)
                except Problem:
                    self._save(c, s['id'], work, {**work['data'], 'status': 'error', 'error': 'Transcript evidence changed. Review this batch.'})
                    self._event(c, s['id'], 'system', 'summary.failed', {}); return True
                chosen = (s, dict(actor), state, work, request)
                self._event(c, s['id'], 'system', 'summary.started', {})
                break
        if chosen is None: return False
        s, actor, state, work, request = chosen
        try:
            result = validate_result(self.summary_model.process(deepcopy(request)), request)
            error = None
        except Exception:
            result, error = None, ('Local summary failed. Check Ollama and the downloaded model, then retry.' if getattr(self.summary_model,'local',True) else 'Cloud summary failed or timed out. Check the API configuration, then retry explicitly; the previous call may have incurred cost.') + ' No transcript was dropped.'
        with self.db.transaction() as c:
            row = c.execute('SELECT * FROM sessions WHERE id=?', (s['id'],)).fetchone()
            if row is None or row['state'] == 'deleted' or row['expires'] <= self.clock(): return True
            current = dict(row)
            work = self._get(c, s['id'], work['id'], 'summary_work')
            live_actor = c.execute('SELECT * FROM actors WHERE id=? AND session_id=?', (actor['id'], s['id'])).fetchone()
            state = self._summary_state(c, s['id'])
            allowed = current['state'] == 'active' and current['lease'] > self.clock() and current['revision'] == s['revision']
            allowed = allowed and state['data']['enabled'] and live_actor is not None and live_actor['role'] == 'facilitator'
            allowed = allowed and live_actor['consent_version'] == current['policy_version'] == s['policy_version']
            if not allowed: error = 'Capture or agreement changed during summarisation. Resume capture, then retry this batch.'
            if not error:
                try:
                    c.execute('SAVEPOINT summary_commit'); tracked = deepcopy(c.changed)
                    for ref in work['data']['sources']: self._expected(self._get(c, s['id'], ref['id']), ref['revision'])
                    self._summary_commit(c, current, dict(live_actor), state, work, request, result)
                    self._budget(c, s['id'])
                    c.execute('RELEASE summary_commit')
                except Problem:
                    c.execute('ROLLBACK TO summary_commit'); c.execute('RELEASE summary_commit'); c.changed = tracked
                    error = 'Summary could not be saved because its evidence or session capacity changed. Review and retry.'
            if error: self._save(c, s['id'], work, {**work['data'], 'status': 'error', 'error': error})
            self._event(c, s['id'], 'system', 'summary.failed' if error else 'summary.completed', {})
        return True

    def _summary_commit(self, c, s, actor, state, work, request, result):
        topic = next((r for r in self._list(c, s['id'], 'summary_topic')
            if label(r['data']['theme']) == label(result['theme']) and label(r['data']['title']) == label(result['title'])), None)
        entry = {k: deepcopy(result[k]) for k in ('summary', 'decisions', 'action_items', 'open_questions', 'evidence')}
        entry.update(started_at=request['lines'][0]['created_at'], ended_at=request['lines'][-1]['created_at'],
                     work_id=work['id'], source_refs=deepcopy(work['data']['sources']))
        data = deepcopy(topic['data']) if topic else {'theme': result['theme'], 'title': result['title'],
            'description': result['description'], 'entries': [], 'note_id': None, 'source_id': None}
        # Each visit remains timestamped; a continuation shares the visit identifier.
        entry['visit'] = data['entries'][-1]['visit'] if topic and state['data']['last_topic_id'] == topic['id'] else work['id']
        data['entries'].append(entry)
        topic = self._save(c, s['id'], topic, data) if topic else self._new(c, s['id'], 'summary_topic', data)
        detail = self._summary_detail(data)
        provenance = {'producer': self.summary_model.name, 'model_version': self.summary_model.model,
                      'synthetic': bool(getattr(self.summary_model, 'synthetic', False))}
        note = self._get(c, s['id'], data['note_id']) if data['note_id'] else None
        manual_note = note and (note['data'].get('last_editor') or note['data'].get('accepted_by'))
        source_data = {'type': 'summary', 'text': detail, 'refs': deepcopy(work['data']['sources']), 'summary_topic_id': topic['id'],
            'author_id': actor['id'], 'origin': 'model', 'created_at': self.clock(), 'provenance': provenance}
        if data['source_id'] and not manual_note:
            source = self._get(c, s['id'], data['source_id'])
            source = self._save(c, s['id'], source, source_data)
        else: source = self._new(c, s['id'], 'source', source_data)
        extra = {'summary_title': data['title'], 'summary_detail': detail, 'summary_category': data['theme'],
            'summary_topic_id': topic['id'], 'summary_batch_id': work['id'], 'summary_importance': 3,
            'provider': self.summary_model.name, 'model': self.summary_model.model, 'synthetic': provenance['synthetic']}
        if note is None:
            published = self._summary_to_stickies(c, s, actor, {'summary': data['title']})
            proposal = published['proposals'][0]
            note = self._get(c, s['id'], proposal['data']['item_id']) if proposal['data'].get('item_id') else proposal
        # A manual correction or deletion is final for this note. The overview keeps updating.
        if not manual_note and note['data'].get('status') not in ('undone', 'rejected'):
            note = self._save(c, s['id'], note, {**note['data'], **extra,
                'text': data['title'], 'refs': [{'id': source['id'], 'revision': source['revision']}]})
        self._save(c, s['id'], topic, {**data, 'source_id': source['id'], 'note_id': note['id']})
        self._save(c, s['id'], state, {**state['data'], 'last_topic_id': topic['id'], 'message': 'Summary up to date.'})
        self._save(c, s['id'], work, {**work['data'], 'status': 'done', 'topic_id': topic['id'], 'error': None})

    @staticmethod
    def _summary_detail(data):
        lines = [data['theme'] + ' / ' + data['title']]
        for entry in data['entries']:
            lines.append(entry['summary'])
            for key, title in (('decisions', 'Decision'), ('action_items', 'Action'), ('open_questions', 'Open question')):
                for row in entry[key]: lines.append(title + ': ' + row['text'] + (' (' + row['owner'] + ')' if row.get('owner') else ''))
        return '\n'.join(lines)
