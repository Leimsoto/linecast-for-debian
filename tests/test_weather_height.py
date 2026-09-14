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
