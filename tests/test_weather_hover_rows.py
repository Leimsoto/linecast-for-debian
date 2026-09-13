"""The cloud strip, the time lines through the lower hourly rows, and the
hover chips on the hourly chart and the daily rows."""
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from linecast import _color, _theme
from linecast._graphics import visible_len
from linecast._runtime import WeatherRuntime
from linecast._weather_daily import render_daily_mapped
from linecast._weather_hourly import (
    _build_precip_blocks, _indicator_row, _render_cloud_row, render_hourly,
)
from linecast._weather_style import CLOUD_RGB, PRECIP_RAIN_RGB
from linecast.weather import _build_daily_tooltip, _build_hover_tooltip

_FG = re.compile(r"\x1b\[38;2;(\d+);(\d+);(\d+)m")
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
FIXTURE = Path(__file__).parent / "fixtures" / "open_meteo_forecast.json"


def _runtime(metric=False):
    return WeatherRuntime(live=False, icons="nerd", lang="en", oneline=False, metric=metric,
                          use_24h=True)


def _plain(text):
    return _ANSI.sub("", text)


def _colors(line):
    return [tuple(int(v) for v in m.groups()) for m in _FG.finditer(line)]


def _distance(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b))


def test_cloud_strip_fades_with_cover():
    with patch.object(_color, "_COLOR_MODE", "truecolor"):
        line = _render_cloud_row([0, 50, 100], 3)
    assert _plain(line) == " ▄▄"
    half, full = _colors(line)
    assert full == tuple(CLOUD_RGB)
    assert _distance(half, _theme.theme_bg) < _distance(full, _theme.theme_bg)


def test_cloud_strip_carries_the_time_line():
    with patch.object(_color, "_COLOR_MODE", "truecolor"):
        line = _render_cloud_row([0, 100, 100], 3, indicator_cols={0: (255, 0, 0), 2: (255, 0, 0)})
    assert _plain(line) == "│▄▄"
    hair, plain_cell, tinted = _colors(line)
    assert hair == (255, 0, 0)
    assert plain_cell == tuple(CLOUD_RGB)
    assert tinted != plain_cell
    assert _distance(tinted, (255, 0, 0)) < _distance(plain_cell, (255, 0, 0))


def test_time_line_tints_its_way_through_the_bar():
    with patch.object(_color, "_COLOR_MODE", "truecolor"):
        lines = _build_precip_blocks([5.0] * 3, [100] * 3, [61] * 3, 3, n_rows=1,
                                     indicator_cols={1: (255, 255, 255)}, full=5.0)
    assert _plain(lines[0]) == "███"
    left, middle, right = _colors(lines[0])
    assert left == right == tuple(PRECIP_RAIN_RGB)
    assert _distance(middle, (255, 255, 255)) < _distance(left, (255, 255, 255))


def test_indicator_row_is_only_the_lines():
    assert _indicator_row(5, {}) == ""
    row = _indicator_row(5, {1: (1, 2, 3), 4: (4, 5, 6)})
    assert _plain(row) == " │  │"


def _hourly_data(hours=72, wind=0.0, uv=0.0):
    start = datetime.now().replace(minute=0, second=0, microsecond=0) - timedelta(hours=24)
    times = [(start + timedelta(hours=i)).isoformat(timespec="minutes") for i in range(hours)]
    return {
        "hourly_units": {"precipitation": "inch"},
        "hourly": {
            "time": times,
            "temperature_2m": [70.0] * hours,
            "apparent_temperature": [70.0] * hours,
            "precipitation": [0.05] * hours,
            "precipitation_probability": [40] * hours,
            "weather_code": [61] * hours,
            "wind_speed_10m": [wind] * hours,
            "wind_direction_10m": [90] * hours,
            "relative_humidity_2m": [50] * hours,
            "dew_point_2m": [50.0] * hours,
            "uv_index": [uv] * hours,
            "cloud_cover": [80] * hours,
        },
        "daily": {"time": [], "sunrise": [], "sunset": []},
    }


def test_reserved_rows_carry_the_time_lines():
    """A wind row reserved for a gale later in the week, with none in
    this window, still shows the now line and midnight dividers."""
    data = _hourly_data(wind=0.0)
    data["hourly"]["wind_speed_10m"][-1] = 40.0
    now = datetime.fromisoformat(data["hourly"]["time"][24])
    with patch.object(_color, "_COLOR_MODE", "truecolor"):
        lines = render_hourly(data, 60, n_braille_rows=2, n_precip_rows=1, now=now,
                              runtime=_runtime())
    plain = [_plain(line) for line in lines]
    wind_row = plain[-3]  # wind, cloud, precip at the bottom
    assert set(wind_row) <= {" ", "│"}
    assert "│" in wind_row
    assert "▄" in plain[-2]


def test_hourly_chip_names_the_rain_and_the_cloud():
    data = _hourly_data()
    with patch.object(_color, "_COLOR_MODE", "truecolor"):
        chip = _build_hover_tooltip(data, 30, 5, 2, 12, 100, 40, _runtime())
    text = _plain(chip)
    assert "0.05″" in text
    assert "40% chance" in text
    assert "Cloud 80%" in text


def test_hourly_chip_shades_the_chance_like_the_bar():
    data = _hourly_data()
    with patch.object(_color, "_COLOR_MODE", "truecolor"):
        chip = _build_hover_tooltip(data, 30, 5, 2, 12, 100, 40, _runtime())
    expected = _theme.lerp_rgb(_theme.theme_bg, PRECIP_RAIN_RGB, 0.4)
    assert tuple(expected) in _colors(chip)


def test_daily_spans_cover_the_parts_they_name():
    data = json.loads(FIXTURE.read_text())
    lines, spans = render_daily_mapped(data, 100, _runtime())
    assert len(lines) == len(spans)
    assert all(0 < s["index"] < len(data["daily"]["time"]) for s in spans)
    for line, span in zip(lines, spans):
        plain = _plain(line)
        if "prob" in span["cols"]:
            col = visible_len(plain[:plain.index("%")])
            a, b = span["cols"]["prob"]
            assert a <= col < b
        if "precip" in span["cols"]:
            col = visible_len(plain[:plain.rindex("″")])
            a, b = span["cols"]["precip"]
            assert a <= col < b
        a, b = span["cols"]["bar"]
        assert visible_len(plain[:plain.index("°")]) >= a


def test_daily_chips_answer_for_each_part():
    data = json.loads(FIXTURE.read_text())
    runtime = _runtime()
    lines, spans = render_daily_mapped(data, 100, runtime)
    wet = next((k for k, s in enumerate(spans) if "precip" in s["cols"]), None)
    assert wet is not None, "the fixture should have a rainy day"
    daily_start = 20
    row = daily_start + wet + 1
    span = spans[wet]

    texts = {}
    with patch.object(_color, "_COLOR_MODE", "truecolor"):
        for field, (a, _b) in span["cols"].items():
            texts[field] = _plain(_build_daily_tooltip(data, a + 1, row, daily_start, spans,
                                                       100, 40, runtime))
        off_row = _build_daily_tooltip(data, 1, daily_start + len(spans) + 1, daily_start, spans,
                                       100, 40, runtime)
    assert off_row == ""
    assert re.search(r"chance of (rain|snow)", texts["prob"])
    assert re.search(r"(Rain|Snow) \d", texts["precip"])
    assert "heaviest around" in texts["precip"]
    assert texts["bar"].count("°") == 2
    assert "around" in texts["bar"]
    day = data["daily"]["time"][span["index"]]
    assert datetime.fromisoformat(day).strftime("%A") in texts["day"]
