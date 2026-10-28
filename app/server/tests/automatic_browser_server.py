"""Offline automatic-workspace journey. All provider output is scripted."""
import struct
from genai_server.adapters import ExtractionOutput, TranscriptionOutput
from tests import document_browser_server as todo
from tests import requirements_browser_server as requirements
from tests import calendar_browser_server as calendar
from tests.poll_browser_server import Interpreter as PollInterpreter

PHRASES={**todo.PHRASES,**requirements.PHRASES,**calendar.PHRASES,
    321:'Hey Jarvaids, close to voting list.'}

class Transcriber:
    name='scripted-automatic-browser'
    def transcribe(self,request):
        marker=struct.unpack('<h',request.chunk_bytes[:2])[0]
        return TranscriptionOutput(PHRASES.get(marker,'Ordinary discussion.'),1,self.name,'contract-double-only',False,{})

class Interpreter:
    def __init__(self):
        self.models={'todo':todo.Interpreter(),'requirements':requirements.Interpreter(),'calendar':calendar.Interpreter()}
    def interpret(self,request): return self.models[request['document_type']].interpret(request)

class WallExtractor:
    name='fixture'
    def extract(self,request):
        assert not request.regions, 'Automatic photo intake must not require marked boxes'
        return ExtractionOutput(tuple({'region_id':f'region_00{i+1}','box':[i*.5,0,.5,1],
            'text':f'FIXTURE ONLY: wall note {i+1}','status':'readable'} for i in range(2)),
            self.name,'contract-double-only',True,{})

if __name__=='__main__':
    todo.main(Transcriber(),Interpreter(),PollInterpreter(),automatic_workspace=True,extractor=WallExtractor())
