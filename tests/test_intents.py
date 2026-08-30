import unittest

from jarvis.intents import Intent, detect


class TestIntents(unittest.TestCase):
    def test_the_canonical_morning_sentence(self):
        self.assertIs(
            detect(
                "Morning Jarvis, what's on the schedule for today? "
                "And anything else I need to know?"
            ),
            Intent.BRIEF,
        )

    def test_briefing_variants(self):
        for phrase in (
            "good morning jarvis",
            "give me the briefing",
            "what's on my calendar",
            "what's the plan for today",
            "any updates?",
            "anything else I need to know",
            "what meetings do I have",
        ):
            self.assertIs(detect(phrase), Intent.BRIEF, phrase)

    def test_specific_intents_win_over_briefing(self):
        self.assertIs(detect("what's on my todo list today"), Intent.TODOS)
        self.assertIs(detect("will it rain today"), Intent.WEATHER)
        self.assertIs(detect("what's the weather this morning"), Intent.WEATHER)
        self.assertIs(detect("any new email today"), Intent.MAIL)
        self.assertIs(detect("what time is it"), Intent.TIME)

    def test_social(self):
        self.assertIs(detect("thank you jarvis"), Intent.THANKS)
        self.assertIs(detect("never mind"), Intent.STOP)

    def test_unknown(self):
        self.assertIs(detect("open the pod bay doors"), Intent.UNKNOWN)


if __name__ == "__main__":
    unittest.main()
