"""How the weather dashboard spends a short or tall window."""
import json
import re
from pathlib import Path
from unittest.mock import patch

from linecast import weather
from linecast._runtime import WeatherRuntime

_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
FIXTURE = Path(__file__).parent / "fixtures" / "open_meteo_forecast.json"


def _rows(rows, cols=100, live=True):
    data = json.loads(FIXTURE.read_text())
    runtime = WeatherRuntime(live=live, icons="nerd", lang="en", oneline=False, metric=False)
    with patch.object(weather, "get_terminal_size", lambda: (cols, rows)), \
            patch.object(weather, "install_banner", lambda: None):
        output, _ = weather.render_from_data(data, [], runtime, "Test")
    return [_ANSI.sub("", line).rstrip() for line in output.split("\n")]


def _blank_positions(lines):
    return [i for i, line in enumerate(lines) if line == ""]


def test_a_tall_window_keeps_every_spacing_row():
    lines = _rows(40)
    assert len(lines) <= 40
    blanks = _blank_positions(lines)
    assert 1 in blanks                       # under the header
    assert len(lines) - 2 in blanks          # above the credit row
    assert len(blanks) >= 3                  # and one before the daily rows


def test_a_short_window_gives_up_the_spacing_rows_first():
    lines = _rows(18)
    assert len(lines) <= 18
    assert _blank_positions(lines) == []
    assert "\u2575" in lines[2]   # the tick row sits right under the day line
    assert any("°" in line and "─" in line for line in lines)   # daily rows survive


def test_the_window_is_never_overrun():
    for rows in (12, 16, 20, 24, 30, 50):
        assert len(_rows(rows)) <= rows


def _rows_with_peak_rain(rows, peak_inches):
    data = json.loads(FIXTURE.read_text())
    amounts = data["hourly"]["precipitation"]
    scale = peak_inches / max(amounts)
    data["hourly"]["precipitation"] = [a * scale for a in amounts]
    runtime = WeatherRuntime(live=True, icons="nerd", lang="en", oneline=False, metric=False)
    with patch.object(weather, "get_terminal_size", lambda: (100, rows)), \
            patch.object(weather, "install_banner", lambda: None):
        output, _ = weather.render_from_data(data, [], runtime, "Test")
    return [_ANSI.sub("", line).rstrip() for line in output.split("\n")]


def _curve_rows(lines):
    return sum(1 for line in lines if any("⠀" <= ch <= "⣿" for ch in line))


def test_a_drizzle_gives_its_bar_rows_to_the_curve():
    downpour = _rows_with_peak_rain(40, 1.0)
    shower = _rows_with_peak_rain(40, 0.1)
    drizzle = _rows_with_peak_rain(40, 0.01)
    assert len(downpour) <= 40 and len(drizzle) <= 40
    assert _curve_rows(shower) == _curve_rows(downpour) + 1
    assert _curve_rows(drizzle) == _curve_rows(downpour) + 2


def test_a_short_window_still_keeps_one_bar_row():
    assert len(_rows_with_peak_rain(14, 1.0)) <= 14
    assert len(_rows_with_peak_rain(14, 0.01)) <= 14
