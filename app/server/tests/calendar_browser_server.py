"""Deterministic calendar journey: real HTTP/store, scripted speech and model."""
import struct
import time
from genai_server.adapters import TranscriptionOutput
from genai_server.poll_model import PollOutput
from tests.document_browser_server import main

NOW = 1792411200  # 19 October 2026, 12:00 UTC
PHRASES = {
    141: 'I will prepare the interview questions by tomorrow.',
    142: 'Hey Jarvaids, make a to-do list.',
    143: 'The prototype review is tomorrow at 2 pm.',
    144: 'We will hold a launch party, date undecided.',
    145: 'Hey Jarvaids, make an agenda.',
    146: 'Actually the prototype review is Friday at 3 pm.',
    147: 'Hey Jarvaids, show week view.',
    148: 'Hey Jarvaids, close the agenda.',
    149: 'Hey Jarvaids, accept the agenda.',
    150: 'Hey Jarvaids, reopen the agenda.',
    151: 'The interview questions are due Friday.',
    152: 'We can discuss lunch now.',
    153: 'I have finished preparing the interview questions.',
    154: 'The launch party is on 24 October 2026.',
    155: 'Move that one.',
    156: 'I mean the launch party, move it to 25 October 2026.',
    157: 'Hey Jarvaids, show year view.',
    158: 'Hey Jarvaids, cancel the agenda.',
    159: 'Hey Jarvaids, make a calendar for next week.',
    160: 'The demo is next Friday.',
    162: 'We have no date for the design expo.',
}

class Transcriber:
    name = 'scripted-calendar-browser'
    def transcribe(self, request):
        marker = struct.unpack('<h', request.chunk_bytes[:2])[0]
        return TranscriptionOutput(PHRASES.get(marker, 'Ordinary discussion.'), 1, self.name, 'contract-double-only', False, {})

class Interpreter:
    name = 'scripted-calendar-browser'
    def __init__(self):
        self.failed_expo = set()
    def interpret(self, request):
        result = {'changes': [], 'prompt': '', 'needs_clarification': False, 'resolutions': []}
        calendar = request['document_type'] == 'calendar'
        if calendar: result['focus'] = {'view': '', 'phrase': '', 'source_id': ''}
        tasks = request.get('tasks', []) if calendar else request['entries']
        task = next((e for e in tasks if e['text'] == 'Prepare the interview questions'), None)
        for line in request['lines']:
            phrase = line['text']; evidence = [{'source_id': line['id'], 'quote': phrase}]
            assignment = phrase.startswith('I will prepare')
            deadline = 'tomorrow' if assignment else 'Friday' if 'questions are due' in phrase else None
            completion = 'I have finished' in phrase
            if assignment or deadline or completion:
                if calendar and not task: continue
                if calendar and assignment: continue  # The same canonical task already appears here.
                raw = deadline if deadline else task['deadline'] if task else ''
                done = completion or bool(task and task['done'])
                if calendar:
                    result['changes'].append({'op': 'update', 'entry_id': '', 'task_id': task['id'],
                        'text': task['text'], 'date_phrase': raw, 'date_quote': raw if deadline else '',
                        'time_phrase': '', 'done': done, 'done_quote': phrase if completion else '', 'evidence': evidence})
                else:
                    result['changes'].append({'op': 'update' if task else 'add', 'entry_id': task['id'] if task else '',
                        'text': 'Prepare the interview questions', 'owner': task['owner'] if task else '',
                        'owner_speaker_id': line['speaker_id'] if assignment and not task else '',
                        'owner_quote': phrase if assignment else task['owner'] if task and task['owner'] in phrase else '',
                        'deadline': raw, 'deadline_quote': raw if deadline else '', 'classification': 'agreed',
                        'commitment_quote': phrase if assignment else '', 'done': done,
                        'completion_quote': phrase if completion else '', 'evidence': evidence})
                continue
            if not calendar: continue
            name = 'Prototype review' if 'prototype review' in phrase else 'Launch party' if 'launch party' in phrase else 'Demo' if 'demo is' in phrase else 'Design expo' if 'design expo' in phrase else ''
            if name:
                existing = next((e for e in request['entries'] if e['text'] == name), None)
                raw = 'Friday' if 'Friday at' in phrase else 'next Friday' if 'next Friday' in phrase else 'tomorrow' if 'tomorrow' in phrase else '24 October 2026' if '24 October' in phrase else '25 October 2026' if '25 October' in phrase else ''
                if name == 'Design expo' and line['id'] not in self.failed_expo:
                    self.failed_expo.add(line['id']); raw = 'tomorrow'  # Invalid on purpose: visible failure, explicit retry.
                at = '3 pm' if '3 pm' in phrase else '2 pm' if '2 pm' in phrase else ''
                result['changes'].append({'op': 'update' if existing else 'add', 'entry_id': existing['id'] if existing else '',
                    'task_id': '', 'text': name, 'date_phrase': raw, 'date_quote': raw, 'time_phrase': at,
                    'done': False, 'done_quote': '', 'evidence': evidence})
                if 'I mean' in phrase:
                    result['resolutions'] = [{'work_id': w['work_id'], 'source_id': line['id'], 'quote': phrase} for w in request['unresolved']]
            if phrase == 'Move that one.': result.update(prompt='Which event should move, and to which date?', needs_clarification=True)
        return PollOutput(result, self.name, 'contract-double-only', {'input_tokens': 0, 'output_tokens': 0})

if __name__ == '__main__':
    started = time.monotonic()
    main(Transcriber(), Interpreter(), clock=lambda: NOW+time.monotonic()-started)
