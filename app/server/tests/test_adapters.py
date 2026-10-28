import unittest

from genai_server.adapters import _strip_non_speech_tags
from genai_server.adapters import FixtureSpeakerIdentifier, SpeakerIdentificationFailure, match_speaker


class NonSpeechTagStripping(unittest.TestCase):
    """A real user's whisper.cpp run rendered '[BLANK_AUDIO]' on screen as
    if it were transcribed speech. Whisper-family models emit this class of
    bracketed/parenthesised annotation on a chunk with no real speech."""

    def test_a_lone_annotation_is_treated_as_no_speech(self):
        for tag in ('[BLANK_AUDIO]', '[SILENCE]', '(silence)', '[Music]', '  [BLANK_AUDIO]  '):
            self.assertEqual('', _strip_non_speech_tags(tag), tag)

    def test_an_annotation_with_trailing_punctuation_or_repeated_is_still_caught(self):
        """A real user's run still showed '(silence)' rendered as text after
        the first version of this filter shipped; that version only matched
        one bare tag with nothing else in the string."""
        for tag in ('(silence).', '(Silence)', '[silence]', '(silence) (silence)', '(silence). (silence).'):
            self.assertEqual('', _strip_non_speech_tags(tag), tag)

    def test_real_words_pass_through_unchanged(self):
        self.assertEqual('Hello there', _strip_non_speech_tags('Hello there'))

    def test_an_annotation_alongside_real_words_is_kept(self):
        text = '[BLANK_AUDIO] but then someone spoke'
        self.assertEqual(text, _strip_non_speech_tags(text))


class SpeakerMatching(unittest.TestCase):
    """F1.3 opt-in voice-ID: match_speaker is pure arithmetic over injected
    vectors, so this exercises the real matching/threshold decision without
    a real embedding model or any audio, same reasoning
    NonSpeechTagStripping above applies to ASR text."""

    def test_an_identical_vector_matches_with_confidence_one(self):
        profile_id, name, confidence = match_speaker((1.0, 0.0, 0.0), [('p1', 'Alice', (1.0, 0.0, 0.0))])
        self.assertEqual('p1', profile_id)
        self.assertEqual('Alice', name)
        self.assertAlmostEqual(1.0, confidence)

    def test_the_closer_of_two_profiles_wins(self):
        close = (0.9, 0.1, 0.0)
        far = (0.0, 1.0, 0.0)
        profile_id, name, confidence = match_speaker((1.0, 0.0, 0.0),
            [('p_far', 'Bob', far), ('p_close', 'Alice', close)])
        self.assertEqual('p_close', profile_id)
        self.assertEqual('Alice', name)
        self.assertGreater(confidence, 0.0)

    def test_a_score_below_threshold_comes_back_unidentified_not_a_guess(self):
        """The whole point of F6.3: a low-confidence match must not be
        silently promoted to a name. The real best score is still returned,
        so a caller can show 'closest was 12%' rather than nothing at all,
        but the name/id are both None."""
        profile_id, name, confidence = match_speaker((1.0, 0.0), [('p1', 'Alice', (0.0, 1.0))], threshold=0.75)
        self.assertIsNone(profile_id)
        self.assertIsNone(name)
        self.assertAlmostEqual(0.0, confidence)

    def test_clear_short_clip_match_uses_revised_default(self):
        import math
        vector = (1.0, 0.0)
        profiles = [('p1', 'Alice', (0.69, math.sqrt(1 - 0.69 ** 2))),
                    ('p2', 'Bob', (0.48, math.sqrt(1 - 0.48 ** 2)))]
        self.assertEqual('p1', match_speaker(vector, profiles)[0])
        self.assertIsNone(match_speaker(vector, profiles, threshold=0.75)[0])

    def test_close_and_tied_voices_stay_unknown_in_either_order(self):
        import math
        for score in (0.70, 0.74):
            profiles = [('p1', 'Alice', (0.74, math.sqrt(1 - 0.74 ** 2))),
                        ('p2', 'Bob', (score, math.sqrt(1 - score ** 2)))]
            for ordered in (profiles, profiles[::-1]):
                result = match_speaker((1.0, 0.0), ordered)
                self.assertIsNone(result[0])
                self.assertAlmostEqual(0.74, result[2])

    def test_no_enrolled_profiles_is_unidentified_with_zero_confidence(self):
        profile_id, name, confidence = match_speaker((1.0, 0.0, 0.0), [])
        self.assertIsNone(profile_id)
        self.assertIsNone(name)
        self.assertEqual(0.0, confidence)

    def test_a_score_at_or_above_threshold_counts_as_a_match(self):
        # cosine similarity of (1,0) and (1,1) is sqrt(2)/2 ~= 0.7071.
        profile_id, name, confidence = match_speaker((1.0, 0.0), [('p1', 'Alice', (1.0, 1.0))], threshold=0.7)
        self.assertEqual('p1', profile_id)

    def test_an_all_zero_vector_never_matches_anything(self):
        """FixtureSpeakerIdentifier always embeds an all-zero vector, which
        this proves is why: cosine similarity against a zero vector is
        defined here as 0.0 (no direction to compare), never a divide-by-
        zero crash and never an accidental match."""
        profile_id, name, confidence = match_speaker((0.0, 0.0, 0.0), [('p1', 'Alice', (1.0, 0.0, 0.0))])
        self.assertIsNone(profile_id)
        self.assertEqual(0.0, confidence)


class FixtureSpeakerIdentifierTests(unittest.TestCase):
    def test_an_empty_chunk_fails_rather_than_fabricating_an_embedding(self):
        with self.assertRaises(SpeakerIdentificationFailure):
            FixtureSpeakerIdentifier().embed(b'', 16000)

    def test_every_embedding_is_the_same_all_zero_vector(self):
        identifier = FixtureSpeakerIdentifier()
        first = identifier.embed(b'\x00\x01' * 100, 16000)
        second = identifier.embed(b'\xff\x00' * 50, 16000)
        self.assertEqual(first.vector, second.vector)
        self.assertTrue(all(v == 0.0 for v in first.vector))
        self.assertTrue(first.synthetic)


if __name__ == '__main__':
    unittest.main()
