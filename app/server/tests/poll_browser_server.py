"""Browser-test doubles only: no microphone, speech model or cloud calls.

PCM markers drive deterministic transcripts/embeddings to exercise the production
HTTP, recognition, polling and sync paths as if their live adapters had answered.
These synthetic contract results are not speech/voice/LLM quality evidence.
"""
import argparse
import struct
import threading
from pathlib import Path
from genai_server.adapters import EmbeddingOutput, TranscriptionOutput
from genai_server.http import LocalServer
from genai_server.poll_model import PollOutput
from genai_server.service import Service


PHRASES = {101: 'Salad, sandwiches or fries for lunch. Hey Jarvaids, make a voting list.',
           102: 'Yes, start voting.', 103: 'Sandwiches for me.', 104: 'Actually change mine to salad.',
           205: 'I vote fries.', 999: 'Fries for me.',
           107: 'Hey Jarvaids, make a poll about ordering lunch with yes or no.'}


class Transcriber:
    name = 'scripted-browser-test'
    def transcribe(self, request):
        marker = struct.unpack('<h', request.chunk_bytes[:2])[0]
        return TranscriptionOutput(PHRASES.get(marker, 'Ordinary discussion.'), 1, self.name,
                                   'contract-double-only', False, {})


class Voices:
    name = 'scripted-browser-test'
    def embed(self, raw, sample_rate):
        marker = struct.unpack('<h', raw[:2])[0] // 100
        return EmbeddingOutput(tuple(float(marker == i) for i in (1, 2, 3)), self.name, 'contract-double-only', False)


class Interpreter:
    name = 'scripted-browser-test'
    def interpret(self, request):
        current = request['current']
        data = {'action': 'ignore', 'question': '', 'options': [], 'option_id': '', 'prompt': '',
                'quote': current['text'], 'source_ids': [current['id']]}
        phrase = current['text']
        if 'make a voting list' in phrase:
            data.update(action='draft', question='What should we have for lunch?', options=['Salad', 'Sandwiches', 'Fries'])
        elif 'make a poll' in phrase:
            data.update(action='draft', question='Should we order lunch?', options=['Yes', 'No'])
        elif phrase == 'Yes, start voting.': data['action'] = 'confirm'
        elif 'salad' in phrase: data.update(action='select', option_id='option_01')
        elif 'Sandwiches' in phrase: data.update(action='select', option_id='option_02')
        elif 'fries' in phrase.casefold(): data.update(action='select', option_id='option_03')
        return PollOutput(data, self.name, 'contract-double-only', {'input_tokens': 0, 'output_tokens': 0})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--origin', required=True)
    args = parser.parse_args()
    service = Service(args.data_dir/'test.sqlite3', transcriber=Transcriber(), speaker_identifier=Voices(), poll_model=Interpreter())
    service.recover_poll_jobs()
    server = LocalServer(('127.0.0.1', args.port), service, [args.origin])
    stop = threading.Event()
    def worker():
        while not stop.is_set():
            service.run_one_poll_job()
            stop.wait(.02)
    thread = threading.Thread(target=worker, daemon=True); thread.start()
    try: server.serve_forever(poll_interval=.1)
    finally: stop.set(); server.server_close(); thread.join(1)


if __name__ == '__main__': main()
