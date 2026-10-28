"""Calendar scheduling and revision-checked changes to shared task records."""
from copy import deepcopy
import re
from .calendar_dates import iso_day, local_day, resolve_date, resolve_time, source_instant
from .calendar_model import EVENT_FIELDS
from .validation import fields, require, text

TASK_KEYS = ('text', 'owner', 'deadline', 'classification', 'done')
DATE_KEYS = ('deadline_date', 'deadline_clarification', 'deadline_anchor', 'deadline_timezone')


class CalendarMixin:
    MAX_TASK_CHANGES = 120

    def _calendar_init(self):
        self.handlers.update({'calendar.entry.edit': self._calendar_entry_edit,
            'calendar.task.resolve': self._calendar_task_resolve, 'calendar.view': self._calendar_view})

    def _session_timezone(self, c, sid):
        record = next(iter(self._list(c, sid, 'session_clock')), None)
        return record['data']['timezone'] if record else 'UTC'

    def _calendar_capture_time(self, session, payload):
        if 'captured_at_utc_ms' in payload:
            require(session['created']-300 <= payload['captured_at_utc_ms']/1000 <= self.clock()+300,
                    'calendar_capture_time', 'The capture clock is outside this session. Check the device clock.', 409)

    def _calendar_tasks(self, c, sid, doc):
        ids = set(doc['data'].get('task_ids', []))
        return [r for r in self._list(c, sid, 'command_entry') if r['id'] in ids and r['data'].get('entry_type') == 'task']

    def _task_date_fields(self, task, instant, zone):
        resolved, question = resolve_date(task['deadline'], instant, zone)
        return {'deadline_date': resolved, 'deadline_clarification': question,
                'deadline_anchor': instant, 'deadline_timezone': zone}

    def _calendar_prepare(self, c, s, doc):
        zone = self._session_timezone(c, s['id'])
        task_ids = []
        for parent in self._list(c, s['id'], 'command_document'):
            if parent['data']['document_type'] != 'todo' or parent['data']['state'] == 'cancelled':
                continue
            for entry in self._document_entries(c, s['id'], parent):
                if entry['data']['removed']:
                    continue
                task_ids.append(entry['id'])
                if 'deadline_date' in entry['data']:
                    continue
                anchor = None
                for ref in reversed(entry['data']['source_refs']):
                    if entry['data']['deadline'] and entry['data']['deadline'] in ref['quote']:
                        source = self._get(c, s['id'], ref['id'], 'transcript_segment')
                        if source['revision'] == ref['revision']:
                            anchor = source_instant(source['data'])
                            break
                dates = self._task_date_fields(entry['data'], anchor, zone) if anchor is not None else {
                    'deadline_date': '', 'deadline_clarification': 'Review the date context for this earlier deadline.' if entry['data']['deadline'] else ''}
                self._save(c, s['id'], entry, {**entry['data'], **dates})
        return self._document_save(c, s['id'], doc, timezone=zone, task_ids=list(dict.fromkeys(task_ids)),
            calendar_view='month', calendar_date=local_day(self.clock(), zone).isoformat(), calendar_focus_revision=0, calendar_focus_origin='initial')

    def _task_changes(self, c, sid, doc):
        ids = set(doc['data'].get('task_ids', []) if doc['data']['document_type'] == 'calendar' else doc['data']['entry_ids'])
        return [r for r in self._list(c, sid, 'command_task_change') if r['data']['task_id'] in ids and r['data']['state'] == 'pending']

    def _propose_task_change(self, c, s, doc, entry, values, evidence, provenance):
        values = {key: value for key, value in values.items() if key in (*TASK_KEYS, *DATE_KEYS, 'removed', 'owner_profile_id')}
        if all(entry['data'].get(key) == value for key, value in values.items() if key not in ('deadline_anchor', 'deadline_timezone')):
            return
        changes = self._list(c, s['id'], 'command_task_change')
        def meaning(value):
            return {key: value.get(key, entry['data'].get(key)) for key in
                    (*TASK_KEYS, 'deadline_date', 'deadline_clarification', 'removed', 'owner_profile_id')}
        if any(r['data']['state'] == 'pending' and r['data']['task_id'] == entry['id'] and
               r['data']['base_revision'] == entry['revision'] and meaning(r['data']['values']) == meaning(values) for r in changes):
            return
        require(len(changes) < self.MAX_TASK_CHANGES, 'calendar_capacity', 'Task change limit reached; edit manually.', 429)
        self._new(c, s['id'], 'command_task_change', {'task_id': entry['id'], 'document_id': doc['id'],
            'base_revision': entry['revision'], 'values': values, 'state': 'pending', 'source_refs': evidence,
            'provenance': provenance, 'created_at': self.clock()})

    def _notify_task_change(self, c, s, entry, current_document=None, *, reviewed=False):
        for doc in self._list(c, s['id'], 'command_document'):
            if doc['id'] == current_document or doc['data']['state'] == 'cancelled':
                continue
            calendar = doc['data']['document_type'] == 'calendar'
            ids = doc['data'].get('task_ids', []) if calendar else doc['data']['entry_ids']
            if entry['id'] not in ids:
                if not calendar or doc['data']['state'] != 'collecting' or entry['data'].get('removed'):
                    continue
                ids = [*ids, entry['id']]
            changes = {'epoch': doc['data']['epoch']+1}
            if calendar:
                changes['task_ids'] = ids
            if doc['data']['state'] == 'accepted' and not reviewed:
                changes.update(state='reviewing', prompt='A linked task was explicitly edited. Review the revised details when ready.')
            elif doc['data']['state'] == 'accepted':
                changes['prompt'] = 'A reviewed shared-task update is reflected here.'
            self._document_save(c, s['id'], doc, **changes)

    def _calendar_accept_tasks(self, c, s, a, doc):
        tasks = self._calendar_tasks(c, s['id'], doc)
        snapshot = []
        for entry in tasks:
            if entry['data']['removed']:
                continue
            entry = self._save(c, s['id'], entry, {**entry['data'], 'status': 'accepted', 'accepted_by': a['id'],
                'accepted_fields': {key: entry['data'].get(key) for key in (*TASK_KEYS, 'deadline_date')}})
            snapshot.append({'id': entry['id'], **deepcopy(entry['data'])})
            self._notify_task_change(c, s, entry, doc['id'], reviewed=True)
        return snapshot

    def _calendar_view(self, c, s, a, b):
        fields(b, ('document_id', 'expected_revision', 'view'), ('date',))
        doc = self._document_editable(c, s, a, b, ('collecting', 'reviewing', 'accepted'))
        require(doc['data']['document_type'] == 'calendar' and b['view'] in ('day', 'week', 'month', 'year'),
                'calendar_view', 'Choose a calendar and day, week, month or year view.')
        target = iso_day(b.get('date', doc['data']['calendar_date']), empty=False)
        return self._document_save(c, s['id'], doc, calendar_view=b['view'], calendar_date=target,
            calendar_focus_revision=doc['data']['calendar_focus_revision']+1, calendar_focus_origin='voice',
            focus_request=doc['data']['focus_request']+1)

    def _calendar_entry_edit(self, c, s, a, b):
        fields(b, ('document_id', 'expected_revision', 'entry_id', 'task_id', 'value', 'removed'), ('expected_task_revision', 'expected_entry_revision', 'note_id'))
        doc = self._document_editable(c, s, a, b)
        require(doc['data']['document_type'] == 'calendar', 'calendar_document', 'Choose a calendar.')
        fields(b['value'], ('text', 'date', 'time', 'done'), ('date_changed',))
        require(type(b['value'].get('date_changed', True)) is bool, 'calendar_entry', 'Date change flag must be boolean.')
        text(b['value']['text'], 'text', 800); iso_day(b['value']['date'])
        at, question = resolve_time(b['value']['time'])
        require(not question and type(b['value']['done']) is bool and type(b['removed']) is bool,
                'calendar_entry', 'Use a valid time and boolean completion/removal values.')
        for key in ('entry_id', 'task_id'): text(b[key], key, 80, empty=True)
        require(not b['entry_id'] or not b['task_id'], 'calendar_identity', 'Choose an event or a linked task.')
        # A note link names where a manual event came from, so it is set once,
        # when the event is made, and never moved onto another event or a task.
        note_id = text(b.get('note_id', ''), 'note_id', 80, empty=True)
        require(not note_id or not b['entry_id'] and not b['task_id'], 'calendar_note', 'Only a new event can be linked to a note.')
        if b['task_id']:
            require(b['task_id'] in doc['data']['task_ids'], 'calendar_task', 'Task is not linked to this calendar.')
            entry = self._get(c, s['id'], b['task_id'], 'command_entry')
            self._expected(entry, b.get('expected_task_revision'))
            changed_date = b['value'].get('date_changed', True)
            require(changed_date or b['value']['date'] == entry['data'].get('deadline_date', ''), 'calendar_date', 'The date changed; save it explicitly.')
            phrase = b['value']['date'] if changed_date else entry['data']['deadline']
            values = {**entry['data'], 'text': b['value']['text'], 'deadline': phrase,
                'deadline_date': b['value']['date'], 'deadline_clarification': '' if changed_date else entry['data'].get('deadline_clarification', ''), 'done': b['value']['done'],
                'removed': b['removed'], 'status': 'provisional', 'origin': 'human', 'edited_by': a['id'],
                'manual_after': self._poll_order(c, s['id']), 'deadline_anchor': self.clock() if changed_date else entry['data'].get('deadline_anchor', self.clock()), 'deadline_timezone': doc['data']['timezone']}
            entry = self._save(c, s['id'], entry, values)
            self._notify_task_change(c, s, entry, doc['id'])
        else:
            require(b['entry_id'] or not b['removed'], 'calendar_entry', 'A new event cannot already be removed.')
            values = {**{key: b['value'][key] for key in ('text', 'date', 'time', 'done')}, 'date_phrase': b['value']['date'], 'time': at, 'time_phrase': at,
                'clarification': '', 'removed': b['removed'], 'status': 'provisional', 'origin': 'human',
                'edited_by': a['id'], 'manual_after': self._poll_order(c, s['id'])}
            if b['entry_id']:
                require(b['entry_id'] in doc['data']['entry_ids'], 'calendar_entry', 'Event is not in this calendar.')
                entry = self._get(c, s['id'], b['entry_id'], 'command_entry')
                self._expected(entry, b.get('expected_entry_revision'))
                entry = self._save(c, s['id'], entry, {**entry['data'], **values})
            else:
                require(len(doc['data']['entry_ids']) < self.MAX_DOCUMENT_ENTRIES, 'document_capacity', 'Event limit reached.', 429)
                link = {}
                if note_id:
                    # Only a note on the canvas: an accepted content item, not a
                    # group, an undone note, a canvas object or another record.
                    note = self._get(c, s['id'], note_id)
                    require(note['kind'] == 'item' and note['data'].get('item_kind') == 'content' and note['data'].get('status') == 'accepted',
                            'calendar_note', 'Link the event to a note on the canvas.')
                    link = {'note_id': note['id']}
                entry = self._new(c, s['id'], 'command_entry', {**values, **link, 'entry_type': 'calendar_event', 'source_refs': []})
                doc = self._document_save(c, s['id'], doc, entry_ids=[*doc['data']['entry_ids'], entry['id']])
        self._document_save(c, s['id'], doc, epoch=doc['data']['epoch']+1)
        return entry

    def _calendar_task_resolve(self, c, s, a, b):
        fields(b, ('document_id', 'expected_revision', 'change_id', 'expected_change_revision', 'accept'))
        doc = self._document_editable(c, s, a, b, ('collecting', 'reviewing', 'accepted'))
        require(type(b['accept']) is bool, 'calendar_change', 'Choose accept or dismiss.')
        change = self._get(c, s['id'], b['change_id'], 'command_task_change')
        self._expected(change, b['expected_change_revision'])
        require(change['data']['state'] == 'pending' and any(r['id'] == change['id'] for r in self._task_changes(c, s['id'], doc)),
                'calendar_change', 'This task change is not pending in this document.')
        if b['accept']:
            entry = self._get(c, s['id'], change['data']['task_id'], 'command_entry')
            require(entry['revision'] == change['data']['base_revision'], 'calendar_task_stale',
                    'The task changed after this proposal. Dismiss it and request a fresh interpretation.', 409)
            values = {**entry['data'], **change['data']['values']}
            entry = self._save(c, s['id'], entry, {**values, 'status': 'accepted', 'accepted_by': a['id'],
                'accepted_fields': {key: values.get(key) for key in (*TASK_KEYS, 'deadline_date')},
                'source_refs': [*entry['data']['source_refs'], *change['data']['source_refs']][-80:],
                'manual_after': self._poll_order(c, s['id'])})
            self._notify_task_change(c, s, entry, doc['id'], reviewed=True)
        self._save(c, s['id'], change, {**change['data'], 'state': 'accepted' if b['accept'] else 'dismissed', 'reviewed_by': a['id']})
        return self._document_save(c, s['id'], doc, epoch=doc['data']['epoch']+1,
            prompt='Shared task change reviewed. The same task is shown in both views.')

    def _calendar_apply(self, c, s, doc, wd, result, request, provenance):
        refs = {ref['id']: ref['revision'] for ref in wd['sources']}
        events = {entry['id']: entry for entry in self._document_entries(c, s['id'], doc)}
        tasks = {entry['id']: entry for entry in self._calendar_tasks(c, s['id'], doc)}
        requested = {task['id']: task for task in request['tasks']}
        for patch in result['changes']:
            entry = tasks.get(patch['task_id']) if patch['task_id'] else events.get(patch['entry_id'])
            if entry and entry['data'].get('manual_after', -1) >= wd['source_order']:
                continue
            cited = [line for line in request['lines'] if line['id'] in {ref['source_id'] for ref in patch['evidence']}]
            latest = max(cited, key=lambda line: line.get('captured_at_ms') or 0)
            if entry and latest.get('capture_id') == entry['data'].get('capture_id'):
                older, newer = latest.get('captured_at_ms'), entry['data'].get('captured_at_ms')
                if older is not None and newer is not None and older < newer:
                    continue
            evidence = [{'id': ref['source_id'], 'revision': refs[ref['source_id']], 'quote': ref['quote']} for ref in patch['evidence']]
            if patch['task_id']:
                require(entry['revision'] == requested[entry['id']]['revision'], 'calendar_task_stale', 'Shared task changed during interpretation.', 409)
                values = {**{key: entry['data'][key] for key in TASK_KEYS}, 'text': patch['text'],
                    'deadline': patch['date_phrase'], 'deadline_date': patch['date'], 'deadline_clarification': patch['clarification'],
                    'done': patch['done'], 'removed': patch['op'] == 'remove'}
                if patch['date_phrase'] != entry['data']['deadline'] or patch['date_quote']:
                    dated = next((line for line in reversed(cited) if patch['date_phrase'] in line['text']), latest)
                    values.update(deadline_anchor=dated['instant'], deadline_timezone=request['timezone'])
                if entry['data']['status'] == 'accepted' and not self.automatic_workspace:
                    self._propose_task_change(c, s, doc, entry, values, evidence, provenance)
                    continue
                entry = self._save(c, s['id'], entry, {**entry['data'], **values, 'status': 'provisional',
                    'source_refs': [*entry['data']['source_refs'], *evidence][-80:], 'provenance': provenance, 'origin': 'model',
                    'capture_id': latest.get('capture_id'), 'captured_at_ms': latest.get('captured_at_ms')})
                self._notify_task_change(c, s, entry, doc['id'])
                continue
            if patch['op'] == 'add' and any(' '.join(re.findall(r'\w+', e['data']['text'].casefold())) ==
                    ' '.join(re.findall(r'\w+', patch['text'].casefold())) for e in events.values()):
                continue
            values = {key: patch[key] for key in EVENT_FIELDS}
            values.update(status='provisional', origin='model', removed=patch['op'] == 'remove', provenance=provenance,
                capture_id=latest.get('capture_id'), captured_at_ms=latest.get('captured_at_ms'))
            if entry:
                entry = self._save(c, s['id'], entry, {**entry['data'], **values, 'source_refs': [*entry['data']['source_refs'], *evidence][-80:]})
            else:
                require(len(doc['data']['entry_ids']) < self.MAX_DOCUMENT_ENTRIES, 'document_capacity', 'Event limit reached.', 429)
                entry = self._new(c, s['id'], 'command_entry', {**values, 'entry_type': 'calendar_event', 'manual_after': -1, 'source_refs': evidence})
                doc = self._document_save(c, s['id'], doc, entry_ids=[*doc['data']['entry_ids'], entry['id']])
            events[entry['id']] = entry
        focus = result['focus']
        doc = self._get(c, s['id'], doc['id'], 'command_document')
        if focus['view'] and focus.get('date') and doc['data']['calendar_focus_revision'] == request.get('calendar_focus_revision', 0):
            self._document_save(c, s['id'], doc, calendar_view=focus['view'], calendar_date=focus['date'],
                calendar_focus_revision=doc['data']['calendar_focus_revision']+1, calendar_focus_origin='interpretation')
