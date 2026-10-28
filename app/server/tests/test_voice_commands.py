import unittest
import json
from pathlib import Path

from genai_server.voice_commands import recognise_command, recognise_continuation, normalise_activation_phrase
from unittest.mock import patch


class VoiceCommandTests(unittest.TestCase):
    def test_observed_activation_spellings_preserve_the_rest_of_the_sentence(self):
        for name in ("Jarvan's", 'Jarvan’s', 'Jarveds', 'Jarvis', 'Jarvates'):
            original=f"Let's begin. Hey {name}, Make a summary of concept A!"
            correction=normalise_activation_phrase(original)
            self.assertEqual("Let's begin. Hey Jarvaids, Make a summary of concept A!",correction['text'])
            self.assertTrue(correction['corrected'])
            self.assertEqual(f'Hey {name}',correction['original_phrase'])
            self.assertEqual('summary',recognise_command(original)['intent'])

    def test_laptop_mishearings_are_canonical_and_recognise_voting(self):
        for phrase in ('HRFates', 'hate jarfades', 'Hey Jarf Aids', 'Hey Jarfaids'):
            correction = normalise_activation_phrase(phrase + '!')
            self.assertEqual('Hey Jarvaids!', correction['text'])
            self.assertEqual('voting', recognise_command(phrase + ' make a voting list.')['intent'])
            current, previous = self.continuation_pair()
            previous['text'] = phrase + '.'
            current['text'] = 'Make a voting list.'
            self.assertEqual('voting', recognise_continuation(current, previous)['intent'])
            self.assertIsNone(normalise_activation_phrase('We mentioned ' + phrase))

    def test_uncertain_sounds_mentions_and_name_prefixes_are_not_corrected(self):
        for text in ('H-R-8s.', 'hate jar of AIDS.', 'Hey Jarvan, make a summary.',
                     'Hey Jarvedson, make a summary.', "Hey Jarvaids's idea is good.",
                     "We said hey Jarvan's make a summary", 'Hey James, make a summary.'):
            self.assertIsNone(normalise_activation_phrase(text),text)
            self.assertIsNone(recognise_command(text),text)
        for options in ({'synthetic':True},{'status':'gap'}):
            self.assertIsNone(normalise_activation_phrase('Hey Jarveds!',**options))
        self.assertFalse(normalise_activation_phrase('Hey Jarvaids, make a summary.')['corrected'])

    def test_observed_name_only_variant_completes_on_the_next_segment(self):
        current,previous=self.continuation_pair()
        previous['text']="Hey Jarvan's"
        self.assertEqual('summary',recognise_continuation(current,previous)['intent'])
        self.assertEqual("Hey Jarvan's",previous['text'])

    def test_all_approved_phrases_and_polite_forms_in_one_or_two_segments(self):
        cases=json.loads(Path(__file__).with_name('voice-command-phrases.json').read_text())
        self.assertEqual(64,sum(len(phrases) for phrases in cases.values()))
        forms=(('', ''),('please ', ''),('can you ', ''),('could you ', ''),
               ('can you please ', ''),('could you please ', ''),
               ('please could you please ', ' please'),('would you ', ''),
               ('will you ', ''),('we would like you to ', ''),
               ('could you please quickly ', ' please thank you'),
               ('please can you briefly ', ' thanks'))
        for intent,phrases in cases.items():
            for phrase in phrases:
                for prefix,suffix in forms:
                    request=prefix+phrase.rstrip('.?').lower()+suffix
                    with self.subTest(intent=intent,request=request):
                        candidate=recognise_command('Hey Jarvaids, '+request)
                        self.assertEqual('recognised',candidate['status'])
                        self.assertEqual(intent,candidate['intent'])
                        self.assertEqual(request.replace('-', ' ').replace("'", ' '),candidate['command'])
                        current,previous=self.continuation_pair();current['text']=request
                        joined=recognise_continuation(current,previous)
                        self.assertIsNotNone(joined)
                        self.assertEqual(intent,joined['intent'])
                        self.assertIsNone(recognise_command(request))

    def test_approved_wording_still_refuses_negation_and_multiple_requests(self):
        cases=json.loads(Path(__file__).with_name('voice-command-phrases.json').read_text())
        for phrases in cases.values():
            for phrase in phrases:
                for prefix,suffix in [('please do not ', ''),('', ' later')]:
                    request=prefix+phrase.rstrip('.?').lower()+suffix
                    with self.subTest(request=request):
                        candidate=recognise_command('Hey Jarvaids, '+request)
                        self.assertEqual('unsupported',candidate['status'])
                        self.assertIsNone(candidate['intent'])
        for request in ('suggest something and draw a diagram',
                        'summarise this then tell us the main points',
                        'suggest ideas and could you please collect our wishes into a list'):
            self.assertEqual('unsupported',recognise_command('Hey Jarvaids, '+request)['status'])

    def test_related_wording_beyond_the_approved_examples(self):
        cases={
            'summary': ('tell me the key points about the meeting', 'produce a brief recap of this session'),
            'visualisation': ('draw our diagram for the project', 'help me visualize these concepts'),
            'comparison': ('show me the similarities between these designs', 'what are the similarities between these options'),
            'voting': ('help me vote on the concepts', 'organize the poll for our team'),
            'suggestions': ('offer me several ideas for our design', 'prepare some suggestions about the interface'),
            'todo': ('turn these decisions into an action list', 'list our tasks we need to complete'),
            'requirements': ('collect the requirements into one list', 'what wishes have we discussed'),
            'planning': ('organize the next steps into our plan', 'prepare a timeline with milestones'),
        }
        for intent,phrases in cases.items():
            for phrase in phrases:
                with self.subTest(intent=intent,phrase=phrase):
                    self.assertEqual(intent,recognise_command('Hey Jarvaids, could you please '+phrase)['intent'])

    def continuation_pair(self):
        common={'status':'final','capture_id':'microphone_001','speaker_actor_id':'actor_001',
                'provenance':{'synthetic':False}}
        return ({**common,'text':'Make a summary.','captured_at_ms':3000},
                {**common,'text':'Hey, Jarvates.','captured_at_ms':1000})

    def test_adjacent_segments_complete_request_without_changing_words(self):
        current,previous=self.continuation_pair()
        result=recognise_continuation(current,previous)
        self.assertIsNotNone(result)
        self.assertEqual('summary',result['intent'])
        self.assertEqual('Make a summary.',current['text'])
        self.assertEqual('Hey, Jarvates.',previous['text'])

    def test_continuation_requires_same_microphone_run_and_actor(self):
        for key,value in [('capture_id','other_run'),('capture_id',None),('speaker_actor_id','other_actor'),('capture_revision',2)]:
            current,previous=self.continuation_pair();current[key]=value
            with self.subTest(key=key,value=value):
                self.assertIsNone(recognise_continuation(current,previous))

    def test_continuation_window_is_bounded_and_ordered(self):
        for time in (1000,999,6001,None):
            current,previous=self.continuation_pair();current['captured_at_ms']=time
            with self.subTest(time=time):
                self.assertIsNone(recognise_continuation(current,previous))
        current,previous=self.continuation_pair();current['captured_at_ms']=6000
        self.assertEqual('summary',recognise_continuation(current,previous)['intent'])

    def test_continuation_requires_name_only_real_final_segments(self):
        for side,key,value in [('previous','text','Hey Jarvates, compare'),
                               ('previous','text','ordinary conversation'),
                               ('previous','status','gap'),('current','status','gap'),
                               ('previous','provenance',{'synthetic':True}),
                               ('current','provenance',{'synthetic':True})]:
            current,previous=self.continuation_pair()
            (previous if side=='previous' else current)[key]=value
            with self.subTest(side=side,key=key):
                self.assertIsNone(recognise_continuation(current,previous))

    def test_summary_in_one_utterance(self):
        for phrase in ('Hey Jarvaids, make a summary.', 'HEY JARVAIDS: make a summary!',
                       'Hey, Jarvaids, summarise the meeting.'):
            with self.subTest(phrase=phrase):
                self.assertEqual('summary', recognise_command(phrase)['intent'])

    def test_direct_address_after_a_lead_in_sentence(self):
        for phrase in ("Let's go again. Hey, Jarvates, make a voting list.",
                       'Here we go again! Hey Jarvaids, make a voting list.',
                       'Ready? Hey Jarvis, make a voting list.'):
            with self.subTest(phrase=phrase):
                candidate=recognise_command(phrase)
                self.assertIsNotNone(candidate)
                self.assertEqual('voting',candidate['intent'])
                self.assertEqual('make a voting list',candidate['command'])
        for phrase in ('We said hey jarvaids make a summary',
                       'Try saying hey jarvates make a voting list.',
                       'The phrase is: hey jarvates make a voting list.'):
            with self.subTest(phrase=phrase):
                self.assertIsNone(recognise_command(phrase))

    def test_conversation_and_other_names_do_not_activate(self):
        for phrase in ('make a summary', 'We said hey jarvaids make a summary',
                       'Hey Marvin make a summary', 'Hey JarvaidsExtra make a summary',
                       'Hey JarvatesExtra make a summary', 'Jarvates make a summary',
                       'They said hey Jarvates make a summary'):
            with self.subTest(phrase=phrase):
                self.assertIsNone(recognise_command(phrase))

    def test_explicit_name_variations_keep_the_same_command_rules(self):
        for name in ('Jarvaids', 'Jarvates', 'Jarvaides', 'Jarvades', 'Jarvais', 'Jarvis', 'Jarvite'):
            with self.subTest(name=name):
                result = recognise_command(f'Hey, {name}. Make a summary.')
                self.assertIsNotNone(result)
                self.assertEqual('summary', result['intent'])
                self.assertEqual('incomplete', recognise_command(f'Hey, {name}.')['status'])
                self.assertEqual('unsupported', recognise_command(f'Hey {name}, do not compare these ideas')['status'])
                self.assertIsNone(recognise_command(f'Hey {name} summarize', synthetic=True))
                self.assertIsNone(recognise_command(f'Hey {name} summarize', status='gap'))

    def test_unfinished_addressed_request_completes_requirements(self):
        current,previous=self.continuation_pair()
        previous['text']='Hey Jarvite, make a...'
        current['text']='list of requirements.'
        first=recognise_command(previous['text'])
        self.assertEqual('incomplete',first['status'])
        self.assertIsNone(first['intent'])
        joined=recognise_continuation(current,previous)
        self.assertIsNotNone(joined)
        self.assertEqual('requirements',joined['intent'])

    def test_screenshot_ordinary_speech_is_not_a_command(self):
        for phrase in ('also for us for suggesting.', 'professional command.',
                       'generation is...', 'And...', 'list of requirements.', 'Make a voting list.'):
            with self.subTest(phrase=phrase):
                self.assertIsNone(recognise_command(phrase))
        current,previous=self.continuation_pair()
        previous['text']='Hey Jarvite, make a...'
        for phrase in ('also for us for suggesting.', 'professional command.', 'generation is...', 'And...'):
            current['text']=phrase
            with self.subTest(phrase=phrase):
                candidate=recognise_continuation(current,previous)
                self.assertIsNotNone(candidate)
                self.assertEqual('unsupported',candidate['status'])
                self.assertIsNone(candidate['intent'])

    def test_suggestion_builders_and_split_singular_request(self):
        for phrase in ('make a suggestion', 'make some suggestions', 'make a few suggestions',
                       'give us a suggestion for the interface', 'create a suggestion',
                       'could you please make a suggestion'):
            with self.subTest(phrase=phrase):
                candidate=recognise_command('Hey Jarvades, '+phrase)
                self.assertEqual('recognised',candidate['status'])
                self.assertEqual('suggestions',candidate['intent'])
        current,previous=self.continuation_pair()
        previous['text']='Hey, Jarvades.';current['text']='Make a suggestion.'
        joined=recognise_continuation(current,previous)
        self.assertIsNotNone(joined)
        self.assertEqual('suggestions',joined['intent'])
        for phrase in ('make a suggestion', 'How about a new plant?'):
            self.assertIsNone(recognise_command(phrase))
        for phrase in ('do not make a suggestion', 'make a suggestion later',
                       'make a suggestion and make a summary'):
            self.assertEqual('unsupported',recognise_command('Hey Jarvades, '+phrase)['status'])

    def test_synthetic_and_gap_transcripts_cannot_activate(self):
        phrase = 'Hey Jarvaids make a summary'
        self.assertIsNone(recognise_command(phrase, synthetic=True))
        self.assertIsNone(recognise_command(phrase, status='gap'))
        self.assertIsNone(recognise_command(None))

    def test_negation_and_additional_actions_are_not_summary_requests(self):
        for command in ('do not make a summary', 'make a summary and delete the meeting',
                        'make a summary later', 'delete everything'):
            result = recognise_command('Hey Jarvaids ' + command)
            self.assertIsNone(result['intent'])
            self.assertEqual('unsupported', result['status'])

    def test_phrase_alone_does_not_arm_the_next_utterance(self):
        self.assertEqual('incomplete', recognise_command('Hey Jarvaids')['status'])
        self.assertIsNone(recognise_command('make a summary'))

    def test_eight_intents_with_natural_variations(self):
        cases = {
            'summary': ['summarize', 'summarise what we discussed in a few bullet points',
                        'give us a quick rundown of this meeting', 'sum this up',
                        'pull out the main points from our discussion'],
            'visualisation': ['make a visualisation', 'visualize', 'visualise these ideas',
                              'turn our discussion into a diagram', 'show these concepts visually'],
            'comparison': ['make a comparison', 'compare', 'compare these two concepts',
                           'show us the differences between option one and option two'],
            'voting': ['make a voting list', 'we want to vote', "let's vote", 'let us vote on these ideas',
                       'set up a poll for the concepts', 'create a list to vote on'],
            'suggestions': ['give us a few suggestions', 'suggest something', 'suggest ideas for the interface',
                            'do you have any suggestions', 'what would you suggest for the next session'],
            'todo': ['make a to-do list', 'create a task list', 'list our action items', 'what do we need to do next'],
            'requirements': ['make a list of requirements', 'list our wishes', 'create a wish list',
                             'make a list of requirements and wishes'],
            'planning': ['make an agenda', 'make a planning', 'make a schedule', 'prepare our timeline',
                         'plan our next meeting', 'schedule the workshop', 'make a schedule for tomorrow'],
        }
        for intent, phrases in cases.items():
            for phrase in phrases:
                with self.subTest(intent=intent, phrase=phrase):
                    result = recognise_command('Hey Jarvaids, ' + phrase)
                    self.assertEqual('recognised', result['status'])
                    self.assertEqual(intent, result['intent'])

    def test_polite_wrappers_and_context_are_preserved(self):
        for phrase in ('could you please summarize this meeting', 'please make a summary for our team',
                       'we would like you to create a summary', 'can you make a summary please',
                       'quickly summarize the discussion'):
            with self.subTest(phrase=phrase):
                result = recognise_command('Hey Jarvaids ' + phrase)
                self.assertEqual('summary', result['intent'])
                self.assertEqual(phrase, result['command'])

    def test_lets_build_requests_work_for_poll_todo_and_requirements(self):
        for prefix in ("let's make", 'let us create', 'lets make', 'please let’s prepare'):
            for noun, intent in (('a voting list', 'voting'), ('a to-do list', 'todo'),
                                 ('a list of requirements and wishes', 'requirements')):
                phrase = 'Hey Jarvaids, '+prefix+' '+noun
                with self.subTest(phrase=phrase):
                    heard = recognise_command(phrase)
                    self.assertEqual(('recognised', intent), (heard.get('status'), heard.get('intent')))
        self.assertEqual('voting', recognise_command("Hey Jarvaids, let's vote.")['intent'])
        for phrase in ("let's not make a voting list", "let's make a to-do list later",
                       "let's make a poll and let's make a to-do list"):
            self.assertEqual('unsupported', recognise_command('Hey Jarvaids, '+phrase)['status'])
        self.assertIsNone(recognise_command("Let's make a voting list."))

    def test_other_intents_reject_negation_and_multiple_requests(self):
        for phrase in ('do not compare these options', "don't visualize this", 'never suggest something',
                       'make a voting list then make a summary', 'summarize this and compare the concepts',
                       'compare these concepts or make a summary', 'make an agenda later',
                       'suggest something later', 'compare these concepts but not now'):
            with self.subTest(phrase=phrase):
                result = recognise_command('Hey Jarvaids ' + phrase)
                self.assertIsNone(result['intent'])
                self.assertEqual('unsupported', result['status'])

    def test_ambiguous_match_is_not_decided_by_pattern_order(self):
        with patch('genai_server.voice_commands.COMMANDS', {'summary': ('compare',), 'comparison': ('compare',)}):
            self.assertIsNone(recognise_command('Hey Jarvaids compare')['intent'])

    def test_output_noun_alone_does_not_ignore_unmatched_words(self):
        for phrase in ('make a summary maybe', 'make a voting list unrelated', 'make a schedule next month'):
            with self.subTest(phrase=phrase):
                self.assertIsNone(recognise_command('Hey Jarvaids ' + phrase)['intent'])
