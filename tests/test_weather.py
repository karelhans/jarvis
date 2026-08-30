import unittest

from jarvis.config import Location
from jarvis.sources.weather import describe_code, parse

OPEN_METEO_PAYLOAD = {
    "current": {"temperature_2m": 14.2, "weather_code": 2},
    "daily": {
        "temperature_2m_max": [19.0],
        "temperature_2m_min": [11.0],
        "precipitation_probability_max": [60],
        "weather_code": [61],
    },
}


class TestWeather(unittest.TestCase):
    def test_parse_open_meteo_payload(self):
        weather = parse(OPEN_METEO_PAYLOAD, Location(city="Amsterdam"))
        self.assertEqual(weather.description, "light rain")
        self.assertEqual(weather.temp_now, 14.2)
        self.assertEqual(weather.temp_high, 19.0)
        self.assertEqual(weather.temp_low, 11.0)
        self.assertEqual(weather.precip_prob, 60)
        self.assertEqual(weather.city, "Amsterdam")

    def test_parse_survives_missing_fields(self):
        weather = parse({}, Location())
        self.assertIsNone(weather.temp_now)
        self.assertIsNone(weather.precip_prob)
        self.assertEqual(weather.description, "mixed weather")

    def test_code_words(self):
        self.assertEqual(describe_code(0), "clear skies")
        self.assertEqual(describe_code(95), "thunderstorms")
        self.assertEqual(describe_code(None), "mixed weather")
        self.assertEqual(describe_code(12345), "mixed weather")


if __name__ == "__main__":
    unittest.main()
