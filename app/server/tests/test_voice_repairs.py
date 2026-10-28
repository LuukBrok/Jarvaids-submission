import base64
import secrets
import struct
import unittest
from genai_server.adapters import ResemblyzerSpeakerIdentifier, EmbeddingOutput, TranscriptionOutput, SpeakerIdentificationFailure
import test_service as service_tests
from genai_server.voice_commands import recognise_command

class WordTranscriber:
    name='scripted-turn-test'
    def __init__(self):self.calls=0
    def transcribe(self,request):
        self.calls+=1
        return TranscriptionOutput('First. Second.',1,self.name,'fixture',False,{'words':[
            {'start':.1,'end':.7,'word':'First.'},{'start':2.4,'end':2.8,'word':' Second.'}]})

class VoiceRepairs(unittest.TestCase):
    setUp=service_tests.ServiceTests.setUp
    cmd=service_tests.ServiceTests.cmd
    active=service_tests.ServiceTests.active

    def test_spelled_name_is_not_split_at_a_short_unidentified_prefix(self):
        encoder=ResemblyzerSpeakerIdentifier.__new__(ResemblyzerSpeakerIdentifier)
        calls=[]
        def embed(raw,rate):
            calls.append(1)
            if len(calls)==1:raise SpeakerIdentificationFailure('short_prefix')
            return EmbeddingOutput((1.,0.),'scripted-voice','fixture',False)
        encoder.embed=embed
        words=[{'word':'H-R','start':.1,'end':.4},
               {'word':"-V-D's, make a requirements list.",'start':.8,'end':1.4}]
        turns=encoder.identify_words(bytes(96000),16000,words,[('luuk','Luuk',(1.,0.)),('other','Other',(0.,1.))],.65)
        self.assertEqual(1,len(turns));self.assertEqual('Luuk',turns[0]['speaker_match']['name'])
        self.assertEqual("H-R-V-D's, make a requirements list.",turns[0]['text'])

    def test_observed_mp3_name_spellings_require_direct_address_and_action(self):
        for phrase in ('Hey RVDs', "H.R.V.D.'s", "H-R-V-D's", 'Hey Jarvedes', "Hey Jarvade's"):
            with self.subTest(phrase=phrase):
                result=recognise_command(phrase+', make a requirements list.')
                self.assertEqual('requirements',result['intent'])
                self.assertEqual('recognised',result['status'])
                self.assertIsNone(recognise_command('We discussed '+phrase+' yesterday.'))
                denied=recognise_command(phrase+', do not make a requirements list.')
                self.assertEqual('unsupported',denied['status'])
                self.assertIsNone(denied['intent'])
        self.assertIsNone(recognise_command('Hey Pieter, make a requirements list.'))
        self.assertEqual('cancel',recognise_command('Hey Jarvaids, abandon our pole.')['poll_action'])
        self.assertEqual('cancel',recognise_command('Hey Jarvaids, abandon our pool.')['poll_action'])
        self.assertIsNone(recognise_command('We said abandon our pole.'))

    def test_poll_control_uses_recognised_wake_continuation(self):
        self.active();body={'mime':'audio/pcm16','base64':base64.b64encode(bytes(32000)).decode(),
            'ended_reason':'silence','capture_id':'continued_poll_control'}
        class Speech:
            name='scripted-command-test'
            value=''
            def transcribe(self,request):return TranscriptionOutput(self.value,1,self.name,'fixture',False,{})
        speech=Speech();self.service.transcriber=speech
        for tick,phrase in enumerate(('Hey Jarvaids, create a poll.','Hey Jarvaids,','Abandon our poll.'),1):
            speech.value=phrase;self.cmd('source.audio',{**body,'captured_at_ms':tick*1000})
        records=self.service.snapshot(self.sid,self.token)['records']
        self.assertEqual('cancelled',next(r for r in records if r['kind']=='poll')['data']['state'])
        self.assertIn('activation_segment_id',[r for r in records if r['kind']=='transcript_segment'][-1]['data']['voice_command'])

    def test_reenrollment_replaces_same_named_profile_instead_of_competing(self):
        self.active();body={'name':'Hazel','mime':'audio/pcm16','base64':base64.b64encode(bytes(64000)).decode(),'ended_reason':'silence'}
        first=self.cmd('speaker.enroll',body)['profile'];second=self.cmd('speaker.enroll',{**body,'name':'hazel'})['profile']
        self.assertEqual(first['id'],second['id']);self.assertEqual(2,second['revision'])
        self.assertEqual(1,sum(r['kind']=='speaker_profile' for r in self.service.snapshot(self.sid,self.token)['records']))

    def test_two_voices_in_one_audio_chunk_keep_separate_transcript_names(self):
        self.active();encoder=ResemblyzerSpeakerIdentifier.__new__(ResemblyzerSpeakerIdentifier)
        def embed(raw,rate):
            values=struct.unpack('<'+'h'*(len(raw)//2),raw)
            vector=(1.,0.) if sum(values)/len(values)<150 else (0.,1.)
            return EmbeddingOutput(vector,'scripted-voice','fixture',False)
        encoder.embed=embed;self.service.speaker_identifier=encoder
        self.service.transcriber=WordTranscriber()
        with self.service.db.transaction() as c:
            for name,vector in [('Hazel',[1.,0.]),('David',[0.,1.])]:
                self.service._new(c,self.sid,'speaker_profile',{'name':name,'embedding':vector,'provenance':{'synthetic':False}})
        raw=struct.pack('<h',100)*25600+struct.pack('<h',200)*25600
        body={'mime':'audio/pcm16','base64':base64.b64encode(raw).decode(),'ended_reason':'silence',
              'capture_id':'turn_test','captured_at_ms':3200}
        request=secrets.token_hex(16)
        first=self.cmd('source.audio',body,key=request);second=self.cmd('source.audio',body,key=request)
        rows=[r for r in self.service.snapshot(self.sid,self.token)['records'] if r['kind']=='transcript_segment']
        self.assertEqual(['Hazel','David'],[r['data']['speaker_name'] for r in rows])
        self.assertEqual(['First.','Second.'],[r['data']['text'] for r in rows])
        self.assertEqual(1,self.service.transcriber.calls);self.assertEqual(first,second)
