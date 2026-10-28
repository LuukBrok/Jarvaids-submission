"""Scripted requirement replies for HTTP/browser contracts, never live AI evidence."""
import struct
from genai_server.adapters import TranscriptionOutput
from genai_server.poll_model import PollOutput
from tests.document_browser_server import main
from tests.poll_browser_server import Interpreter as PollInterpreter

PHRASES = {
    301: 'It must work offline.', 302: 'We would prefer a green case.',
    303: 'Hey Jarvaids, make a list of requirements and wishes.',
    304: 'Users struggle to read the screen.', 305: 'It must always use the cloud.',
    306: 'Actually a green case is a requirement.',
    307: 'Hey Jarvaids, close the requirements and wishes.',
    308: 'Hey Jarvaids, accept the requirements and wishes.',
    309: 'Hey Jarvaids, reopen the requirements and wishes.',
    310: 'Hey Jarvaids, cancel the requirements and wishes.',
    311: 'The weather is nice.', 312: 'Remove the green case criterion.',
    313: 'Change that one.', 314: 'I meant the offline criterion, keep it as a wish.',
    316: 'It should be quick.', 317: "Hey Jarvaids, let's make a to-do list.",
    318: "Salad, sandwiches or fries for lunch. Hey Jarvaids, let's make a voting list.",
    319: 'Yes, start voting.', 320: 'Sandwiches for me.',
}


class Transcriber:
    name = 'scripted-requirements-browser-test'
    def transcribe(self, request):
        marker = struct.unpack('<h', request.chunk_bytes[:2])[0]
        return TranscriptionOutput(PHRASES.get(marker, 'Ordinary discussion.'), 1,
            self.name, 'contract-double-only', False, {})


class Interpreter:
    name = 'scripted-requirements-browser-test'
    def __init__(self):
        self.attempted = set()

    def interpret(self, request):
        data = {'changes': [], 'prompt': '', 'needs_clarification': False, 'resolutions': []}
        if request['document_type'] != 'requirements':
            return PollOutput(data, self.name, 'contract-double-only', {})
        for line in request['lines']:
            phrase = line['text']; patch = None
            if phrase == PHRASES[301]: patch = ('Work offline', 'requirement', 'stated', '')
            elif phrase == PHRASES[302]: patch = ('Green case', 'wish', 'stated', '')
            elif phrase == PHRASES[304]: patch = ('Readable display', 'clarification', 'inferred', '')
            elif phrase == PHRASES[305]: patch = ('Always use the cloud', 'clarification', 'stated', 'Conflicts with Work offline.')
            elif phrase == PHRASES[306]: patch = ('Green case', 'requirement', 'stated', '')
            elif phrase == PHRASES[312]: patch = ('Green case', 'requirement', 'stated', '')
            elif phrase == PHRASES[314]:
                patch = ('Work offline', 'wish', 'stated', '')
                data['resolutions'] = [{'work_id': w['work_id'], 'source_id': line['id'], 'quote': phrase}
                                       for w in request['unresolved']]
            elif phrase == PHRASES[313]: data.update(needs_clarification=True, prompt='Which criterion should change?')
            elif phrase == PHRASES[316] and line['id'] not in self.attempted:
                self.attempted.add(line['id']); patch = ('Respond within 2 seconds', 'wish', 'stated', '')
            if patch:
                value, category, basis, conflict = patch
                entry = next((e for e in request['entries'] if e['text'] == value), None)
                data['changes'].append({'op': 'remove' if phrase == PHRASES[312] else 'update' if entry else 'add',
                    'entry_id': entry['id'] if entry else '', 'text': value, 'category': category,
                    'basis': basis, 'conflict': conflict, 'stated_quote': phrase if basis == 'stated' else '',
                    'evidence': [{'source_id': line['id'], 'quote': phrase}]})
        return PollOutput(data, self.name, 'contract-double-only', {'input_tokens': 0, 'output_tokens': 0})


if __name__ == '__main__':
    main(Transcriber(), Interpreter(), PollInterpreter())
