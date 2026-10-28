"""Scripted speech/voice/document replies for the real HTTP/browser journey only."""
import argparse
import struct
import threading
from pathlib import Path
from genai_server.adapters import TranscriptionOutput
from genai_server.http import LocalServer
from genai_server.poll_model import PollOutput
from genai_server.service import Service
from tests.poll_browser_server import Voices

PHRASES = {
    101: 'Maybe we could interview students.', 102: 'Hey Jarvaids, make a to-do list.',
    103: 'I will prepare the interview questions by Friday.',
    204: 'I will recruit participants by Thursday.',
    105: 'Actually, the interview questions are due Monday.',
    106: 'I have finished preparing the interview questions.',
    999: 'I will contact the museum.', 108: 'Julie will contact the museum.',
    109: 'Hey Jarvaids, close the to-do list.', 110: 'Hey Jarvaids, accept the to-do list.',
    111: 'Hey Jarvaids, reopen the to-do list.', 112: 'Hey Jarvaids, cancel the to-do list.',
    113: 'The weather is nice.',
    116: 'The student interviews are due Tuesday.',
}


class Transcriber:
    name = 'scripted-document-browser-test'
    def transcribe(self, request):
        marker = struct.unpack('<h', request.chunk_bytes[:2])[0]
        return TranscriptionOutput(PHRASES.get(marker, 'Ordinary discussion.'), 1, self.name, 'contract-double-only', False, {})


class Interpreter:
    name = 'scripted-document-browser-test'
    def interpret(self, request):
        data = {'changes': [], 'prompt': '', 'needs_clarification': False, 'resolutions': []}
        for line in request['lines']:
            phrase = line['text']; task = None
            if 'Maybe we could interview' in phrase: task = ('Interview students', '', '', 'suggested', False)
            elif 'student interviews are due' in phrase: task = ('Interview students', '', 'Tuesday', 'suggested', False)
            elif 'I will prepare' in phrase: task = ('Prepare the interview questions', '', 'Friday', 'agreed', False)
            elif 'I will recruit' in phrase: task = ('Recruit participants', '', 'Thursday', 'agreed', False)
            elif 'due Monday' in phrase: task = ('Prepare the interview questions', 'Julie', 'Monday', 'agreed', False)
            elif 'I have finished' in phrase: task = ('Prepare the interview questions', 'Julie', 'Monday', 'agreed', True)
            elif 'contact the museum' in phrase:
                task = ('Contact the museum', 'Julie' if 'Julie will' in phrase else '', '', 'agreed', False)
                if not line['speaker_id']:
                    data.update(needs_clarification=True, prompt='Who will contact the museum?')
            if task is None: continue
            value, owner, deadline, classification, done = task
            entry = next((e for e in request['entries'] if e['text'] == value), None)
            own = line['speaker_id'] if phrase.startswith('I will') and not owner else ''
            data['changes'].append({'op': 'update' if entry else 'add', 'entry_id': entry['id'] if entry else '',
                'text': value, 'owner': owner, 'owner_speaker_id': own or '', 'deadline': deadline,
                'classification': classification, 'done': done,
                'owner_quote': phrase if owner or own else '', 'deadline_quote': deadline,
                'commitment_quote': phrase if classification == 'agreed' else '',
                'completion_quote': phrase if done else '', 'evidence': [{'source_id': line['id'], 'quote': phrase}]})
            if 'Julie will contact' in phrase:
                data['resolutions'] = [{'work_id': w['work_id'], 'source_id': line['id'], 'quote': phrase}
                                       for w in request['unresolved']]
        return PollOutput(data, self.name, 'contract-double-only', {'input_tokens': 0, 'output_tokens': 0})


def main(transcriber=None, interpreter=None, poll_model=None, clock=None, automatic_workspace=False, extractor=None):
    parser = argparse.ArgumentParser(); parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--port', type=int, required=True); parser.add_argument('--origin', required=True)
    args = parser.parse_args()
    service = Service(args.data_dir/'test.sqlite3', transcriber=transcriber or Transcriber(), speaker_identifier=Voices(),
                      document_model=interpreter or Interpreter(), poll_model=poll_model,
                      automatic_workspace=automatic_workspace,extractor=extractor, **({'clock': clock} if clock else {}))
    service.recover_document_jobs()
    server = LocalServer(('127.0.0.1', args.port), service, [args.origin]); stop = threading.Event()
    def worker():
        while not stop.is_set():
            service.run_one_job(); service.run_one_document_job(); service.run_one_poll_job(); stop.wait(.02)
    thread = threading.Thread(target=worker, daemon=True); thread.start()
    try: server.serve_forever(poll_interval=.1)
    finally: stop.set(); server.server_close(); thread.join(1)


if __name__ == '__main__': main()
