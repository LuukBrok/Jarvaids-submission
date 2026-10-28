import unittest

from genai_server.summary_stickies import ideas_from_summary


class SummaryStickyTests(unittest.TestCase):
    def test_important_ideas_lead_and_titles_tell_the_story(self):
        ideas=ideas_from_summary(
            '- We discussed a welcoming landing page with examples.\n'
            '- We decided the prototype must work offline because the room has unreliable Wi-Fi.\n'
            '- Risk: participants may not notice provisional results.\n'
            '- Investigate whether arrows clarify dependencies.')
        self.assertEqual(['Decision','Risk','Open question','Insight'],[idea['category'] for idea in ideas])
        self.assertEqual('the prototype must work offline',ideas[0]['title'])
        self.assertLessEqual(len(ideas[0]['title'].split()),7)

    def test_at_most_six_notes_are_created(self):
        summary='\n'.join(f'- Idea {index}.' for index in range(10))
        self.assertEqual(6,len(ideas_from_summary(summary)))


if __name__=='__main__':unittest.main()
