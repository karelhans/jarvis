import unittest
from datetime import datetime, timedelta, timezone

from jarvis import briefing
from jarvis.briefing import BriefingData
from jarvis.config import Config
from jarvis.sources.calendar import Event
from jarvis.sources.gmail import MailSummary
from jarvis.sources.tasks import Todo
from jarvis.sources.weather import Weather

TZ = timezone(timedelta(hours=2))
MORNING = datetime(2026, 8, 31, 7, 5, tzinfo=TZ)  # a Monday


def config() -> Config:
    cfg = Config()
    cfg.owner = "Karel"
    return cfg


class TestCompose(unittest.TestCase):
    def test_full_briefing_reads_naturally(self):
        data = BriefingData(
            now=MORNING,
            events=[
                Event("Recycling pickup", None, all_day=True),
                Event("Standup", MORNING.replace(hour=9, minute=30)),
                Event("Lunch with Anna", MORNING.replace(hour=12, minute=30),
                      location="De Pijp"),
            ],
            todos=[
                Todo("Renew passport", due=MORNING.date() - timedelta(days=1)),
                Todo("Pay water bill", due=MORNING.date()),
                Todo("Fix the shed door"),
            ],
            weather=Weather("partly cloudy", 14.2, 19.0, 11.0, 60, city="Amsterdam"),
            mail=MailSummary(3, [("Anna", "Lunch today?")]),
        )
        text = briefing.compose(config(), data)

        self.assertIn("Good morning, Karel.", text)
        self.assertIn("Monday the 31st of August, 7:05", text)
        self.assertIn("Partly cloudy in Amsterdam", text)
        self.assertIn("60 percent chance of rain", text)
        self.assertIn("three things on the calendar", text)
        self.assertIn("All day: Recycling pickup.", text)
        self.assertIn("At 9:30, Standup.", text)
        self.assertIn("At 12:30, Lunch with Anna, at De Pijp.", text)
        self.assertIn("three open todos", text)
        self.assertIn("One is overdue: Renew passport.", text)
        self.assertIn("Due today: Pay water bill.", text)
        self.assertIn("Three unread emails since yesterday", text)
        self.assertIn("from Anna, about: Lunch today?", text)
        self.assertIn("Have a good morning.", text)

    def test_empty_day_is_calm_not_crashy(self):
        data = BriefingData(now=MORNING, events=[], todos=[], mail=MailSummary(0))
        text = briefing.compose(config(), data)
        self.assertIn("Your calendar is clear today.", text)
        self.assertIn("Your todo list is empty.", text)
        self.assertIn("No new email since yesterday.", text)

    def test_disabled_sources_are_simply_absent(self):
        text = briefing.compose(config(), BriefingData(now=MORNING))
        self.assertNotIn("calendar", text)
        self.assertNotIn("todo", text)
        self.assertNotIn("email", text)

    def test_problems_are_spoken(self):
        data = BriefingData(now=MORNING, problems=["I couldn't reach your calendar."])
        self.assertIn("I couldn't reach your calendar.", briefing.compose(config(), data))

    def test_twelve_hour_times(self):
        cfg = config()
        cfg.time_format = "12h"
        evening = MORNING.replace(hour=19, minute=0)
        self.assertEqual(briefing.speakable_time(evening, "12h"), "7 PM")
        self.assertEqual(briefing.speakable_time(MORNING, "12h"), "7:05 AM")
        self.assertEqual(briefing.speakable_time(evening, "24h"), "19:00")

    def test_afternoon_greeting(self):
        text = briefing.greeting(config(), MORNING.replace(hour=15))
        self.assertIn("Good afternoon, Karel", text)

    def test_demo_gather_needs_no_network_or_auth(self):
        data = briefing.gather(config(), demo=True)
        self.assertTrue(data.events)
        self.assertTrue(data.todos)
        self.assertIsNotNone(data.weather)
        self.assertEqual(data.problems, [])
        text = briefing.compose(config(), data)
        self.assertIn("on the calendar", text)


if __name__ == "__main__":
    unittest.main()
