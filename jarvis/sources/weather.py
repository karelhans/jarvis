"""Today's weather from Open-Meteo (free, no API key)."""

from __future__ import annotations

from dataclasses import dataclass

from jarvis.config import Location

# WMO weather interpretation codes → speakable words
_CODES = {
    0: "clear skies",
    1: "mostly clear skies",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "fog",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    56: "freezing drizzle",
    57: "freezing drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    66: "freezing rain",
    67: "freezing rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    77: "snow grains",
    80: "rain showers",
    81: "rain showers",
    82: "heavy rain showers",
    85: "snow showers",
    86: "heavy snow showers",
    95: "thunderstorms",
    96: "thunderstorms with hail",
    99: "thunderstorms with hail",
}


@dataclass
class Weather:
    description: str
    temp_now: float | None
    temp_high: float | None
    temp_low: float | None
    precip_prob: int | None  # max chance of precipitation today, percent
    city: str = ""
    units: str = "celsius"


def describe_code(code) -> str:
    try:
        return _CODES.get(int(code), "mixed weather")
    except (TypeError, ValueError):
        return "mixed weather"


def fetch(location: Location) -> Weather:
    import requests

    if location.latitude is None or location.longitude is None:
        raise ValueError("weather needs location.latitude/longitude in the config")

    params = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "current": "temperature_2m,weather_code",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
        "forecast_days": 1,
        "timezone": "auto",
    }
    if location.units == "fahrenheit":
        params["temperature_unit"] = "fahrenheit"

    response = requests.get(
        "https://api.open-meteo.com/v1/forecast", params=params, timeout=8
    )
    response.raise_for_status()
    return parse(response.json(), location)


def parse(payload: dict, location: Location) -> Weather:
    current = payload.get("current") or {}
    daily = payload.get("daily") or {}

    def first(key):
        values = daily.get(key) or [None]
        return values[0]

    code = first("weather_code")
    if code is None:
        code = current.get("weather_code")
    precip = first("precipitation_probability_max")
    return Weather(
        description=describe_code(code),
        temp_now=current.get("temperature_2m"),
        temp_high=first("temperature_2m_max"),
        temp_low=first("temperature_2m_min"),
        precip_prob=None if precip is None else int(precip),
        city=location.city,
        units=location.units,
    )
