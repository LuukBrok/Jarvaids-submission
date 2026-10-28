"""Shared command documents with independent to-do and requirements collectors."""
from copy import deepcopy
import re
import threading

from .document_model import PATCH_FIELDS, SCHEMA
from .criteria import CRITERION_FIELDS, criterion, validate_criteria
from .calendar_dates import source_instant, resolve_date
from .calendar_model import EVENT_FIELDS, CALENDAR_SCHEMA, validate_calendar
from .calendar_service import CalendarMixin
from .validation import Problem, fields, require, text


OPEN = ('collecting', 'reviewing')
PENDING = ('queued', 'running')
UNRESOLVED = ('error', 'uncertain', 'clarify', 'stale')
TASK_FIELDS = ('text', 'owner', 'deadline', 'classification', 'done')
DOCUMENT_TYPES = ('todo', 'requirements', 'calendar')
TITLES = {'todo': 'To-do list', 'requirements': 'Requirements and wishes', 'calendar': 'Calendar'}


def entry_fields(doc):
    return {'requirements': CRITERION_FIELDS, 'calendar': EVENT_FIELDS}.get(doc['data']['document_type'], TASK_FIELDS)


def normal(value):
    return ' '.join(re.findall(r'\w+', value.casefold()))


class DocumentMixin(CalendarMixin):
    MAX_DOCUMENT_WORK = 120
    MAX_DOCUMENT_QUEUE = 24
    MAX_DOCUMENT_ENTRIES = 60
    DOCUMENT_BATCH_CHARS = 12000
    DOCUMENT_BATCH_LINES = 24

    def _init_documents(self, model, notice):
        self.document_model = model
        self.document_notice = notice or 'Set ANTHROPIC_API_KEY in the repository .env and restart. Manual list controls still work.'
        self.document_lock = threading.Lock()
        self.handlers.update({
            'document.create': self._document_create, 'document.edit': self._document_edit,
            'document.refresh': self._document_refresh, 'document.close': self._document_close,
            'document.accept': self._document_accept, 'document.reopen': self._document_reopen,
            'document.cancel': self._document_cancel, 'document.retry': self._document_retry,
            'document.resolve': self._document_resolve, 'document.entry.edit': self._document_entry_edit,
        })
        self._calendar_init()
        enabled = model is not None
        with self.db.transaction() as c:
            for row in c.execute("SELECT * FROM sessions WHERE state NOT IN ('deleted','closed')").fetchall():
                s = dict(row)
                marker = next(iter(self._list(c, s['id'], 'command_policy')), None)
                if not marker and not enabled:
                    continue
                if marker and marker['data']['whole_meeting_text'] == enabled and marker['data'].get('types') == list(DOCUMENT_TYPES):
                    continue
                if s['state'] == 'active':
                    self._stop_capture(c, s)
                else:
                    c.execute('UPDATE sessions SET revision=revision+1 WHERE id=?', (s['id'],))
                c.execute('UPDATE sessions SET policy_version=policy_version+1 WHERE id=?', (s['id'],))
                if marker:
                    self._save(c, s['id'], marker, {'whole_meeting_text': enabled, 'types': list(DOCUMENT_TYPES)})
                else:
                    self._new(c, s['id'], 'command_policy', {'whole_meeting_text': enabled, 'types': list(DOCUMENT_TYPES)})
                self._event(c, s['id'], 'system', 'policy.documents_changed', {})

    def _document_capability(self):
        return {'available': self.document_model is not None, 'whole_meeting_text': self.document_model is not None,
                'types': list(DOCUMENT_TYPES), 'notice': '' if self.document_model is not None else self.document_notice}

    def _document_work(self, c, sid, did):
        return [r for r in self._list(c, sid, 'command_work') if r['data']['document_id'] == did]

    def _document_entries(self, c, sid, doc):
        ids = set(doc['data']['entry_ids'])
        return [r for r in self._list(c, sid, 'command_entry') if r['id'] in ids]

    def _document_save(self, c, sid, doc, **changes):
        return self._save(c, sid, doc, {**doc['data'], **changes})

    def _document_editor(self, s, a):
        self._editor(a)
        self._active(s)
        require(a['consent_version'] == s['policy_version'], 'agreement_incomplete', 'Current agreement is required.', 409)

    def _document_editable(self, c, s, a, body, states=OPEN):
        self._document_editor(s, a)
        doc = self._get(c, s['id'], body['document_id'], 'command_document')
        self._expected(doc, body['expected_revision'])
        require(doc['data']['state'] in states, 'document_state', 'This list does not allow that action.', 409)
        return doc

    @staticmethod
    def _document_task(value):
        fields(value, TASK_FIELDS)
        for key, limit in (('text', 800), ('owner', 120), ('deadline', 160)):
            text(value[key], key, limit, empty=key != 'text')
        require(value['classification'] in ('suggested', 'agreed') and type(value['done']) is bool,
                'document_entry', 'Choose suggested or agreed, and a boolean completion value.')
        return {key: value[key].strip() if type(value[key]) is str else value[key] for key in TASK_FIELDS}

    def _document_sources(self, c, sid, doc):
        maximum = doc['data']['last_source_order']
        orders = {r['id']: r['rowid'] for r in c.execute(
            "SELECT id,rowid FROM records WHERE session_id=? AND kind='transcript_segment' AND rowid<=?", (sid, maximum))}
        return [(r, orders[r['id']]) for r in self._list(c, sid, 'transcript_segment')
                if r['id'] in orders and r['data']['status'] == 'final'
                and not r['data']['provenance']['synthetic'] and r['data'].get('text')
                and not (r['data'].get('voice_command') or {}).get('document_action')]

    def _document_queue(self, c, s, a, doc, phase):
        works = self._document_work(c, s['id'], doc['id'])
        covered = {ref['id'] for w in works for ref in w['data']['sources']}
        remaining = [(r, order) for r, order in self._document_sources(c, s['id'], doc) if r['id'] not in covered]
        all_work = self._list(c, s['id'], 'command_work')
        slots = min(self.MAX_DOCUMENT_WORK-len(all_work), self.MAX_DOCUMENT_QUEUE-
                    sum(w['data']['status'] in PENDING for w in all_work))
        while remaining and slots > 0:
            batch, size = [], 0
            while remaining and len(batch) < self.DOCUMENT_BATCH_LINES:
                source, order = remaining[0]
                length = len(source['data']['text'])
                if batch and size+length > self.DOCUMENT_BATCH_CHARS:
                    break
                batch.append(remaining.pop(0)); size += length
            self._new(c, s['id'], 'command_work', {
                'document_id': doc['id'], 'phase': phase, 'sources': [{'id': r['id'], 'revision': r['revision']} for r, _ in batch],
                'source_order': batch[-1][1], 'status': 'queued' if self.document_model is not None else 'error',
                'actor_id': a['id'], 'session_revision': s['revision'], 'policy_version': s['policy_version'],
                'created_at': self.clock(), 'attempts': 0,
                'error': None if self.document_model is not None else self.document_notice,
            })
            slots -= 1
        return self._document_save(c, s['id'], doc, uncovered=len(remaining),
            prompt=('Some transcript is not queued. Refresh collection when capacity is available, or review incomplete coverage.'
                    if remaining else 'Collecting relevant additions. Close this list whenever you want to stop collection; acceptance can wait until later.'))

    def _document_new(self, c, s, a, title, order, document_type='todo'):
        self._document_editor(s, a)
        existing = next((r for r in self._list(c, s['id'], 'command_document')
                         if r['data']['document_type'] == document_type and r['data']['state'] in
                         (('collecting',) if self.automatic_workspace else OPEN)), None)
        if existing:
            require(existing['data']['capture_actor_id'] == a['id'], 'document_capture', 'This list uses another room microphone.', 409)
            if existing['data']['state'] != 'collecting':
                return existing
            existing = self._document_save(c, s['id'], existing, last_source_order=order,
                                           focus_request=existing['data'].get('focus_request', 0)+1)
            return self._document_queue(c, s, a, existing, 'history')
        doc = self._new(c, s['id'], 'command_document', {'document_type': document_type, 'title': title,
            'state': 'collecting', 'entry_ids': [], 'epoch': 1, 'created_at': self.clock(),
            'capture_actor_id': a['id'], 'last_source_order': order, 'uncovered': 0,
            'prompt': 'Reading the original meeting transcript for this list.', 'accepted_snapshot': None, 'focus_request': 1})
        if document_type == 'calendar':
            doc = self._calendar_prepare(c, s, doc)
        return self._document_queue(c, s, a, doc, 'history')

    def _document_create(self, c, s, a, b):
        fields(b, ('document_type',), ('title',))
        require(b['document_type'] in DOCUMENT_TYPES, 'document_type', 'Choose todo, requirements or calendar.')
        title = text(b.get('title', TITLES[b['document_type']]), 'title', 160).strip()
        return self._document_new(c, s, a, title, self._poll_order(c, s['id']), b['document_type'])

    def _document_edit(self, c, s, a, b):
        fields(b, ('document_id', 'expected_revision', 'title'))
        doc = self._document_editable(c, s, a, b)
        return self._document_save(c, s['id'], doc, title=text(b['title'], 'title', 160).strip())

    def _document_refresh(self, c, s, a, b):
        fields(b, ('document_id', 'expected_revision'))
        doc = self._document_editable(c, s, a, b, ('collecting',))
        doc = self._document_save(c, s['id'], doc, last_source_order=self._poll_order(c, s['id']))
        return self._document_queue(c, s, a, doc, 'history')

    def _document_close(self, c, s, a, b):
        fields(b, ('document_id', 'expected_revision'))
        doc = self._document_editable(c, s, a, b, ('collecting',))
        return self._document_save(c, s['id'], doc, state='reviewing',
            prompt='Collection stopped. Earlier replies finish processing. Continue your discussion and review this list whenever you are ready.')

    def _document_accept(self, c, s, a, b):
        fields(b, ('document_id', 'expected_revision'), ('acknowledge_incomplete',))
        doc = self._document_editable(c, s, a, b, ('reviewing',))
        works = self._document_work(c, s['id'], doc['id'])
        require(not any(w['data']['status'] in (*PENDING, *UNRESOLVED) for w in works),
                'document_pending', 'Wait for processing and resolve or exclude unclear replies before accepting.', 409)
        incomplete = doc['data']['uncovered'] or any(w['data']['status'] == 'dismissed' for w in works)
        require(not incomplete or b.get('acknowledge_incomplete') is True,
                'document_coverage', 'Some transcript was not interpreted. Explicitly acknowledge incomplete coverage.', 409)
        entries = self._document_entries(c, s['id'], doc)
        require(not self._task_changes(c, s['id'], doc), 'calendar_changes_pending', 'Review or dismiss the proposed shared-task changes first.', 409)
        linked = self._calendar_accept_tasks(c, s, a, doc) if doc['data']['document_type'] == 'calendar' else None
        require(not any(e['data'].get('conflict') for e in entries if not e['data'].get('removed')),
                'document_conflict', 'Review and clear the flagged criterion conflicts before accepting.', 409)
        for entry in entries:
            self._save(c, s['id'], entry, {**entry['data'], 'status': 'accepted', 'accepted_by': a['id'],
                'accepted_fields': {key: entry['data'][key] for key in entry_fields(doc)}})
        return self._document_save(c, s['id'], doc, state='accepted', accepted_by=a['id'], accepted_at=self.clock(),
            accepted_snapshot=[{'id': r['id'], **deepcopy(r['data'])} for r in entries],
            **({'linked_snapshot': linked} if linked is not None else {}),
            prompt='List accepted. Ordinary conversation will not change it. Reopen explicitly to collect more additions.')

    def _document_reopen(self, c, s, a, b):
        fields(b, ('document_id', 'expected_revision'))
        doc = self._document_editable(c, s, a, b, ('accepted', 'reviewing'))
        require(not any(r['id'] != doc['id'] and r['data']['document_type'] == doc['data']['document_type'] and r['data']['state'] in OPEN
                        for r in self._list(c, s['id'], 'command_document')), 'document_exists', 'Another list of this type is already collecting or under review.', 409)
        doc = self._document_save(c, s['id'], doc, state='collecting', epoch=doc['data']['epoch']+1,
                                  last_source_order=self._poll_order(c, s['id']))
        return self._document_queue(c, s, a, doc, 'history')

    def _document_cancel(self, c, s, a, b):
        fields(b, ('document_id', 'expected_revision'))
        doc = self._document_editable(c, s, a, b)
        for work in self._document_work(c, s['id'], doc['id']):
            if work['data']['status'] in (*PENDING, *UNRESOLVED):
                self._save(c, s['id'], work, {**work['data'], 'status': 'cancelled'})
        return self._document_save(c, s['id'], doc, state='cancelled', epoch=doc['data']['epoch']+1,
                                  prompt='List cancelled. Its history is retained.')

    def _document_entry_edit(self, c, s, a, b):
        fields(b, ('document_id', 'expected_revision', 'entry_id', 'task', 'removed'))
        doc = self._document_editable(c, s, a, b)
        require(doc['data']['document_type'] != 'calendar', 'calendar_entry', 'Use the calendar entry editor.')
        task = criterion(b['task']) if doc['data']['document_type'] == 'requirements' else self._document_task(b['task'])
        text(b['entry_id'], 'entry_id', 80, empty=True)
        require(type(b['removed']) is bool, 'document_entry', 'Removal must be boolean.')
        require(bool(b['entry_id']) or not b['removed'], 'document_entry', 'A new task cannot already be removed.')
        order = self._poll_order(c, s['id'])
        resolve_deadline = True
        if b['entry_id']:
            require(b['entry_id'] in doc['data']['entry_ids'], 'document_entry', 'Task is not in this list.')
            entry = self._get(c, s['id'], b['entry_id'], 'command_entry')
            resolve_deadline = task.get('deadline') != entry['data'].get('deadline')
            entry = self._save(c, s['id'], entry, {**entry['data'], **task, 'removed': b['removed'],
                **({'owner_profile_id': entry['data'].get('owner_profile_id') if task['owner'] == entry['data']['owner'] else None} if 'owner' in task else {}),
                'origin': 'human', 'status': 'provisional', 'manual_after': order, 'edited_by': a['id']})
        else:
            require(len(doc['data']['entry_ids']) < self.MAX_DOCUMENT_ENTRIES, 'document_capacity', 'Task limit reached.', 429)
            entry = self._new(c, s['id'], 'command_entry', {**task, 'entry_type': 'criterion' if doc['data']['document_type'] == 'requirements' else 'task', 'removed': False,
                'owner_profile_id': None, 'origin': 'human', 'status': 'provisional', 'manual_after': order,
                'source_refs': [], 'edited_by': a['id']})
            doc = self._document_save(c, s['id'], doc, entry_ids=[*doc['data']['entry_ids'], entry['id']])
        if entry['data']['entry_type'] == 'task':
            # A completion/text edit must not re-anchor an existing "tomorrow".
            if resolve_deadline:
                dates = self._task_date_fields(task, self.clock(), self._session_timezone(c, s['id']))
                entry = self._save(c, s['id'], entry, {**entry['data'], **dates})
            self._notify_task_change(c, s, entry, doc['id'])
        self._document_save(c, s['id'], doc, epoch=doc['data']['epoch']+1,
                            prompt='Manual correction saved. Earlier queued interpretations cannot replace it.')
        return entry

    def _document_resolve(self, c, s, a, b):
        fields(b, ('document_id', 'expected_revision', 'work_id'))
        doc = self._document_editable(c, s, a, b)
        work = self._get(c, s['id'], b['work_id'], 'command_work')
        require(work['data']['document_id'] == doc['id'] and work['data']['status'] in UNRESOLVED,
                'document_work', 'Only an unresolved interpretation from this list can be excluded.', 409)
        self._save(c, s['id'], work, {**work['data'], 'status': 'dismissed', 'resolved_by': a['id']})
        return self._document_save(c, s['id'], doc, prompt='Reply excluded. Its evidence and history are retained; coverage is incomplete.')

    def _document_retry(self, c, s, a, b):
        fields(b, ('document_id', 'expected_revision', 'work_id', 'acknowledge_unknown_cost'))
        doc = self._document_editable(c, s, a, b)
        require(self.document_model is not None, 'document_ai_unavailable', self.document_notice, 409)
        require(b['acknowledge_unknown_cost'] is True, 'document_retry_ack', 'A retry may incur additional API cost.')
        work = self._get(c, s['id'], b['work_id'], 'command_work')
        require(work['data']['document_id'] == doc['id'] and work['data']['status'] in UNRESOLVED,
                'document_work', 'Only an unresolved interpretation from this list can be retried.', 409)
        require(work['data']['attempts'] < 3, 'document_retry_limit', 'Retry limit reached; correct manually.', 409)
        self._save(c, s['id'], work, {**work['data'], 'status': 'queued', 'error': None,
            'session_revision': s['revision'], 'policy_version': s['policy_version'], 'retried_by': a['id']})
        return self._document_save(c, s['id'], doc, prompt='Retry queued with the current task list.')

    def _document_heard(self, c, s, a, source):
        data, heard = source['data'], source['data'].get('voice_command') or {}
        if data['status'] != 'final' or data['provenance']['synthetic']:
            return
        intent = 'calendar' if heard.get('intent') == 'planning' else heard.get('intent')
        creating = heard.get('status') == 'recognised' and intent in DOCUMENT_TYPES and not heard.get('document_action')
        order = self._poll_order(c, s['id'])
        if creating:
            doc = self._document_new(c, s, a, TITLES[intent], order, intent)
            if intent == 'calendar':
                period = re.search(r'\bfor (.+?)[.!?]?$', data['text'], re.I)
                if period:
                    resolved, question = resolve_date(period[1], source_instant(data), doc['data']['timezone'], period=True)
                    if resolved:
                        phrase = period[1].lower()
                        unit = next((unit for unit in ('week', 'year', 'day') if unit in phrase),
                            'day' if phrase in ('today', 'tomorrow') or re.fullmatch(r'\d{4}-\d{2}-\d{2}', phrase) else 'year' if re.fullmatch(r'\d{4}', phrase) else 'month')
                        self._calendar_view(c, s, a, {'document_id': doc['id'], 'expected_revision': doc['revision'], 'view': unit, 'date': resolved})
            return
        action = heard.get('document_action') if heard.get('status') == 'recognised' else None
        docs = [r for r in self._list(c, s['id'], 'command_document')
                if not action or r['data']['document_type'] == intent]
        if action:
            doc = next((r for r in reversed(docs) if r['data']['state'] in OPEN), None)
            if action in ('reopen', 'view') and doc is None:
                doc = next((r for r in reversed(docs) if r['data']['state'] == 'accepted'), None)
            if doc is not None and a['id'] == doc['data']['capture_actor_id']:
                try:
                    payload = {'document_id': doc['id'], 'expected_revision': doc['revision']}
                    if action == 'view' and intent == 'calendar':
                        payload['view'] = heard['calendar_view']
                        phrase = heard.get('calendar_period', '')
                        if phrase:
                            resolved, question = resolve_date(phrase, source_instant(data), doc['data']['timezone'], period=True)
                            if resolved: payload['date'] = resolved
                        self._calendar_view(c, s, a, payload)
                    else:
                        self.handlers['document.'+action](c, s, a, payload)
                except Problem as error:
                    self._document_save(c, s['id'], doc, prompt=error.message)
            return
        # Each collecting type interprets ordinary speech independently. Addressed
        # commands belong to their own handler and are not criterion/task evidence.
        if heard.get('status') == 'recognised':
            return
        for doc in docs:
            if doc['data']['state'] == 'collecting' and a['id'] == doc['data']['capture_actor_id']:
                doc = self._document_save(c, s['id'], doc, last_source_order=order)
                self._document_queue(c, s, a, doc, 'live')

    def _document_request(self, c, sid, doc, work):
        lines = []
        for ref in work['data']['sources']:
            source = self._get(c, sid, ref['id'], 'transcript_segment')
            require(source['revision'] == ref['revision'], 'document_source', 'Transcript evidence changed.', 409)
            data = source['data']
            speaker = (data.get('speaker_profile_id') if data.get('attribution') == 'voice_identified'
                       and not data['provenance'].get('speaker', {}).get('synthetic', True) else None)
            lines.append({'id': source['id'], 'text': data['text'], 'speaker_id': speaker, 'created_at': data['created_at'],
                          'capture_id': data.get('capture_id'), 'captured_at_ms': data.get('captured_at_ms'), 'instant': source_instant(data)})
        require(sum(len(line['text']) for line in lines) <= self.DOCUMENT_BATCH_CHARS and len(lines) <= self.DOCUMENT_BATCH_LINES,
                'document_batch', 'Transcript batch is too large; review manually or exclude it.', 409)
        return {'calendar_focus_revision': doc['data'].get('calendar_focus_revision', 0),
                'timezone': doc['data'].get('timezone', self._session_timezone(c, sid)),
                'tasks': [{'id': task['id'], 'revision': task['revision'], **task['data']} for task in self._calendar_tasks(c, sid, doc)] if doc['data']['document_type'] == 'calendar' else [],
                'document_type': doc['data']['document_type'], 'phase': work['data']['phase'], 'batch_order': work['data']['source_order'],
                'lines': lines, 'context': [{'id': r['id'], 'text': r['data']['text'][:2000]}
                    for r, order in self._document_sources(c, sid, doc)
                    if order < work['data']['source_order'] and r['id'] not in {line['id'] for line in lines}][-4:],
                'unresolved': [{'work_id': r['id'], 'prompt': r['data'].get('prompt', '')}
                    for r in self._document_work(c, sid, doc['id']) if r['data']['status'] == 'clarify'][-10:],
                'entries': [{'id': r['id'], **{k: r['data'].get(k) for k in
                    (*entry_fields(doc), 'removed', 'manual_after')}} for r in self._document_entries(c, sid, doc)]}

    def _document_validate(self, output, request):
        data = output.data
        fields(data, CALENDAR_SCHEMA['required'] if request.get('document_type') == 'calendar' else SCHEMA['required'])
        require(type(data['needs_clarification']) is bool and type(data['changes']) is list and len(data['changes']) <= 20,
                'document_model', 'Invalid document interpretation.')
        text(data['prompt'], 'prompt', 1000, empty=True)
        sources = {r['id']: r for r in request['lines']}
        unresolved = {r['work_id'] for r in request['unresolved']}
        require(type(data['resolutions']) is list and len(data['resolutions']) <= 10,
                'document_resolution', 'Invalid clarification resolutions.')
        for resolution in data['resolutions']:
            fields(resolution, ('work_id', 'source_id', 'quote'))
            text(resolution['quote'], 'quote', 4000)
            require(resolution['work_id'] in unresolved and resolution['source_id'] in sources
                    and resolution['quote'] in sources[resolution['source_id']]['text'],
                    'document_resolution', 'A clarification resolution needs current quoted evidence.')
        if request.get('document_type') == 'calendar':
            require(not output.synthetic, 'calendar_synthetic', 'Synthetic interpretation cannot become live events.')
            return validate_calendar(data, request)
        if request.get('document_type', 'todo') == 'requirements':
            validate_criteria(data, request)
            require(not output.synthetic, 'document_synthetic', 'Synthetic interpretations cannot become live criteria.')
            return data
        entries = {r['id']: r for r in request['entries']}
        changed = set()
        for patch in data['changes']:
            fields(patch, PATCH_FIELDS)
            require(patch['op'] in ('add', 'update', 'remove'), 'document_model', 'Unknown task operation.')
            self._document_task({k: patch[k] for k in TASK_FIELDS})
            for key in ('entry_id', 'owner_speaker_id', 'owner_quote', 'deadline_quote', 'commitment_quote', 'completion_quote'):
                text(patch[key], key, 1000, empty=True)
            require(patch['op'] == 'add' and not patch['entry_id'] or patch['op'] != 'add' and patch['entry_id'] in entries,
                    'document_model', 'AI referenced an unknown task.')
            require(not patch['entry_id'] or patch['entry_id'] not in changed, 'document_model', 'AI changed a task twice.')
            changed.add(patch['entry_id'])
            require(type(patch['evidence']) is list and 1 <= len(patch['evidence']) <= self.DOCUMENT_BATCH_LINES,
                    'document_evidence', 'Task changes need source evidence.')
            for ref in patch['evidence']:
                fields(ref, ('source_id', 'quote'))
                text(ref['quote'], 'quote', 4000)
                require(ref['source_id'] in sources and ref['quote'] in sources[ref['source_id']]['text'],
                        'document_evidence', 'AI cited unknown or invented transcript evidence.')
            quotes = [r['quote'] for r in patch['evidence']]
            old = entries.get(patch['entry_id'], {})
            def grounded(quote):
                return bool(quote.strip()) and any(quote in q for q in quotes)
            for key in ('owner', 'deadline'):
                if patch[key] and patch[key] != old.get(key):
                    require(grounded(patch[key+'_quote']) and normal(patch[key]) in normal(patch[key+'_quote']),
                            'document_field', 'An owner or deadline was not stated in the evidence.')
            if patch['owner_speaker_id']:
                require(any(sources[r['source_id']]['speaker_id'] == patch['owner_speaker_id'] and
                            patch['owner_quote'] in r['quote'] and bool(re.search(r'\b(i|ik|my|mijn)\b', patch['owner_quote'], re.I))
                            for r in patch['evidence']), 'document_speaker', 'A first-person assignment needs the actual identified speaker.')
            if patch['classification'] == 'agreed' and old.get('classification') != 'agreed':
                require(grounded(patch['commitment_quote']), 'document_commitment', 'An agreed action needs a stated commitment.')
            if patch['done'] and not old.get('done'):
                require(grounded(patch['completion_quote']), 'document_completion', 'Completion needs a stated completion.')
        require(not output.synthetic, 'document_synthetic', 'Synthetic interpretations cannot become live tasks.')
        return data

    def _document_authority(self, c, s, work):
        return self._poll_authority(c, s, work)

    def recover_document_jobs(self):
        with self.db.transaction() as c:
            for row in c.execute("SELECT session_id,id FROM records WHERE kind='command_work'").fetchall():
                work = self._get(c, row['session_id'], row['id'], 'command_work')
                if work['data']['status'] == 'running' or self.document_model is None and work['data']['status'] == 'queued':
                    self._save(c, row['session_id'], work, {**work['data'], 'status': 'uncertain',
                        'error': 'Interrupted interpretation; review or explicitly retry with possible additional cost.'})
                    self._event(c, row['session_id'], 'system', 'document.recovered', {})

    def run_one_document_job(self):
        if self.document_model is None or not self.document_lock.acquire(blocking=False):
            return False
        try:
            return self._run_document_job()
        finally:
            self.document_lock.release()

    def _run_document_job(self):
        with self.db.transaction() as c:
            row = c.execute("SELECT session_id,id FROM records WHERE kind='command_work' AND json_extract(data,'$.status')='queued' ORDER BY rowid LIMIT 1").fetchone()
            if row is None:
                return False
            sid = row['session_id']
            s = dict(c.execute('SELECT * FROM sessions WHERE id=?', (sid,)).fetchone())
            work = self._get(c, sid, row['id'], 'command_work')
            doc = self._get(c, sid, work['data']['document_id'], 'command_document')
            if not self._document_authority(c, s, work) or doc['data']['state'] not in OPEN:
                self._save(c, sid, work, {**work['data'], 'status': 'stale', 'error': 'Capture authority changed. Review or retry explicitly.'})
                self._event(c, sid, 'system', 'document.stale', {})
                return True
            try:
                request = self._document_request(c, sid, doc, work)
            except Problem:
                self._save(c, sid, work, {**work['data'], 'status': 'stale', 'error': 'Transcript changed or exceeds the batch limit. Review or exclude this batch.'})
                self._event(c, sid, 'system', 'document.source_changed', {})
                return True
            epoch = doc['data']['epoch']
            work = self._save(c, sid, work, {**work['data'], 'status': 'running', 'attempts': work['data']['attempts']+1,
                                            'started_at': self.clock()})
            self._event(c, sid, 'system', 'document.processing', {})
        output, error = None, None
        try:
            output = self.document_model.interpret(request)
            result = self._document_validate(output, request)
        except Exception:
            error = 'AI interpretation failed or could not be validated. Review or retry explicitly; usage may be unknown.'
        try:
            with self.db.transaction() as c:
                row = c.execute('SELECT * FROM sessions WHERE id=?', (sid,)).fetchone()
                if row is None or row['state'] == 'deleted':
                    return True
                s = dict(row)
                work = self._get(c, sid, work['id'], 'command_work')
                doc = self._get(c, sid, doc['id'], 'command_document')
                wd = {**work['data'], 'completed_at': self.clock()}
                provenance = None if output is None else {'producer': output.provider, 'model_version': output.model,
                    'usage': output.usage, 'synthetic': output.synthetic}
                if wd['status'] != 'running' or not self._document_authority(c, s, work) or doc['data']['state'] not in OPEN or doc['data']['epoch'] != epoch:
                    self._save(c, sid, work, {**wd, 'status': 'stale', 'provenance': provenance,
                        'error': 'The list or capture changed during interpretation. Review or retry; manual edits were preserved.'})
                elif error:
                    self._save(c, sid, work, {**wd, 'status': 'error', 'provenance': provenance, 'error': error})
                else:
                    self._apply_document_output(c, s, doc, wd, work, result, request, provenance)
                self._event(c, sid, 'system', 'document.interpreted', {})
                self._budget(c, sid)
        except Exception:
            with self.db.transaction() as c:
                row = c.execute('SELECT state FROM sessions WHERE id=?', (sid,)).fetchone()
                if row and row['state'] != 'deleted':
                    current = self._get(c, sid, work['id'], 'command_work')
                    if current['data']['status'] == 'running':
                        self._save(c, sid, current, {**current['data'], 'status': 'uncertain',
                            'error': 'Interpretation could not be committed. Review or explicitly retry with possible additional cost.'})
                        self._event(c, sid, 'system', 'document.uncertain', {})
        return True

    def _apply_document_output(self, c, s, doc, wd, work, result, request, provenance):
        entries = {r['id']: r for r in self._document_entries(c, s['id'], doc)}
        source_refs = {r['id']: r['revision'] for r in wd['sources']}
        for ref in wd['sources']:
            current = self._get(c, s['id'], ref['id'], 'transcript_segment')
            require(current['revision'] == ref['revision'], 'document_source', 'Transcript changed during interpretation.', 409)
        if doc['data']['document_type'] == 'calendar':
            self._calendar_apply(c, s, doc, wd, result, request, provenance)
            self._document_finish(c, s, doc, wd, work, result, provenance)
            return
        for patch in result['changes']:
            entry = entries.get(patch['entry_id'])
            if entry and entry['data'].get('manual_after', -1) >= wd['source_order']:
                continue
            if patch['op'] == 'add' and any(normal(r['data']['text']) == normal(patch['text']) for r in entries.values()):
                continue
            task = {key: patch[key] for key in entry_fields(doc)}
            cited = [line for line in request['lines'] if line['id'] in {r['source_id'] for r in patch['evidence']}]
            latest = max(cited, key=lambda line: line.get('captured_at_ms') or 0)
            if entry and latest.get('capture_id') == entry['data'].get('capture_id'):
                earlier, later = latest.get('captured_at_ms'), entry['data'].get('captured_at_ms')
                if earlier is not None and later is not None and earlier < later:
                    continue
            profile = patch.get('owner_speaker_id', '')
            if profile:
                speaker = self._get(c, s['id'], profile, 'speaker_profile')
                require(not speaker['data'].get('provenance', {}).get('synthetic', True), 'document_speaker', 'Synthetic profiles cannot own a real task.')
                task['owner'] = speaker['data']['name']
            evidence = [{'id': r['source_id'], 'revision': source_refs[r['source_id']], 'quote': r['quote']} for r in patch['evidence']]
            changes = {**task, **({'owner_profile_id': profile or (entry['data'].get('owner_profile_id') if entry and task.get('owner') == entry['data'].get('owner') else None)} if 'owner' in task else {}), 'status': 'provisional', 'origin': 'model',
                'provenance': provenance, 'source_order': wd['source_order'], 'removed': patch['op'] == 'remove',
                'capture_id': latest.get('capture_id'), 'captured_at_ms': latest.get('captured_at_ms')}
            if doc['data']['document_type'] == 'todo':
                if not entry or task['deadline'] != entry['data']['deadline'] or patch['deadline_quote']:
                    changes.update(self._task_date_fields(task, latest['instant'], request['timezone']))
                if entry and entry['data']['status'] == 'accepted' and not self.automatic_workspace:
                    self._propose_task_change(c, s, doc, entry, changes, evidence, provenance)
                    continue
            if entry:
                changes['source_refs'] = [*entry['data']['source_refs'], *evidence][-80:]
                entry = self._save(c, s['id'], entry, {**entry['data'], **changes})
            else:
                require(len(doc['data']['entry_ids']) < self.MAX_DOCUMENT_ENTRIES, 'document_capacity', 'Task limit reached.', 429)
                entry = self._new(c, s['id'], 'command_entry', {**changes, 'entry_type': 'criterion' if doc['data']['document_type'] == 'requirements' else 'task', 'source_refs': evidence, 'manual_after': -1})
                doc = self._document_save(c, s['id'], doc, entry_ids=[*doc['data']['entry_ids'], entry['id']])
            entries[entry['id']] = entry
            if doc['data']['document_type'] == 'todo':
                self._notify_task_change(c, s, entry, doc['id'])
        self._document_finish(c, s, doc, wd, work, result, provenance)

    def _document_finish(self, c, s, doc, wd, work, result, provenance):
        doc = self._get(c, s['id'], doc['id'], 'command_document')
        self._save(c, s['id'], work, {**wd, 'status': 'clarify' if result['needs_clarification'] else 'done',
            'interpretation': result, 'prompt': result['prompt'], 'provenance': provenance, 'error': None})
        for resolution in result['resolutions']:
            prior = self._get(c, s['id'], resolution['work_id'], 'command_work')
            if prior['data']['document_id'] == doc['id'] and prior['data']['status'] == 'clarify':
                self._save(c, s['id'], prior, {**prior['data'], 'status': 'resolved',
                    'resolved_by_source': resolution['source_id'], 'resolution_quote': resolution['quote']})
        if result['needs_clarification']:
            self._document_save(c, s['id'], doc, prompt=result['prompt'] or 'Which task or assignment did you mean?')
