"""The weather view says whose data it shows, without crowding the view."""

import inspect
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from linecast import _help, _weather_sources, weather
from linecast._graphics import visible_len
from linecast._runtime import WeatherRuntime
from linecast._weather_json import build_payload
from linecast._weather_sources import (
    ATTRIBUTION, alert_attribution, alert_source, _METEOALARM_SLUGS)

FIXTURES = Path(__file__).parent / "fixtures"
FIXED_NOW = datetime(2026, 3, 5, 14, 30)


def plain(text):
    return re.sub(r'\033\[[0-9;]*[a-zA-Z]', '', text)


class TestSources:
    def test_every_routed_country_names_its_service(self):
        # the router's explicit branches and the credit table must agree
        routed = set(re.findall(r'country_code == "([A-Z]{2})"',
                                inspect.getsource(_weather_sources._fetch_alerts_routed)))
        assert routed == set(_weather_sources._ALERT_SOURCES)

    def test_ireland_is_met_eireann(self):
        assert alert_source("IE") == "Met Éireann"
        assert alert_attribution("ie") == "Alerts by Met Éireann"

    def test_the_rest_of_europe_is_meteoalarm(self):
        for code in _METEOALARM_SLUGS:
            assert alert_source(code) == "MeteoAlarm"

    def test_no_feed_means_no_credit(self):
        assert alert_source("AR") is None
        assert alert_attribution("") is None


class TestCreditRow:
    LONG = 'Weather data by Open-Meteo · Alerts by Met Éireann'

    def test_credit_left_and_hint_right(self):
        out = plain(weather.credit_row(120, 'en', 'IE'))
        assert out.startswith(self.LONG)
        assert out.endswith('  ? keys') and visible_len(out) == 119

    def test_a_narrower_window_keeps_the_short_credit(self):
        out = plain(weather.credit_row(50, 'en', 'IE'))
        assert out.startswith('Weather data by Open-Meteo') and 'Alerts' not in out
        assert out.endswith('  ? keys') and visible_len(out) == 49

    def test_a_narrow_window_keeps_the_hint_alone(self):
        out = plain(weather.credit_row(30, 'en', 'IE'))
        assert 'Open-Meteo' not in out and out.strip() == '? keys'

    def test_the_credit_never_shortens_the_hint(self):
        # room for the credit and a clipped hint, but not the whole one
        out = plain(weather.credit_row(34, 'en', ''))
        assert 'Open-Meteo' not in out and out.endswith('? keys')

    def test_the_credit_is_fainter_than_the_prose(self):
        from linecast._weather_style import DIM_RGB, MUTED_RGB
        from linecast import _theme
        assert (_theme.contrast_ratio(DIM_RGB, _theme.theme_bg)
                <= _theme.contrast_ratio(MUTED_RGB, _theme.theme_bg))
        assert weather.DIM in weather.credit_row(120, 'en', 'IE')


class TestPanel:
    def test_credits_follow_the_controls_after_a_spacer(self):
        rows = _help.entries('weather', 'en',
                             credits=(ATTRIBUTION, alert_attribution('IE')))
        assert rows[-3] is None
        assert rows[-2:] == [('', ATTRIBUTION), ('', 'Alerts by Met Éireann')]

    def test_no_alerts_feed_adds_no_row(self):
        rows = _help.entries('weather', 'en', credits=(ATTRIBUTION, alert_attribution('AR')))
        assert rows[-1] == ('', ATTRIBUTION) and rows[-2] is None

    def test_live_weather_panel_shows_the_credits(self):
        app = WeatherApp = weather.WeatherApp
        with patch("time.monotonic", return_value=0.0):
            app = WeatherApp({"v": 1}, [], None, 53.3, -6.3, SimpleNamespace(lang="en"),
                             location_name="Dublin", country="IE")
        panel = plain(app.help_panel().render(160, 50))
        assert ATTRIBUTION in panel and 'Alerts by Met Éireann' in panel


def _render(cols, rows, live=True, country_code="IE"):
    data = json.loads((FIXTURES / "open_meteo_forecast.json").read_text(encoding="utf-8"))
    runtime = WeatherRuntime(live=live, icons="emoji", lang="en", oneline=False,
                             celsius=False, metric=False)
    with patch("linecast.weather.get_terminal_size", return_value=(cols, rows)), \
         patch("linecast.weather._local_now_for_data", return_value=FIXED_NOW), \
         patch("linecast._weather_hourly._local_now_for_data", return_value=FIXED_NOW):
        output, _ = weather.render_from_data(data, alerts=[], runtime=runtime,
                                             location_name="Dublin",
                                             country_code=country_code)
    return plain(output).split("\n")


class TestLiveView:
    def test_the_last_row_credits_the_data_and_offers_help(self):
        lines = _render(160, 40)
        assert lines[-1].startswith('Weather data by Open-Meteo · Alerts by Met Éireann')
        assert lines[-1].endswith('  ? keys') and visible_len(lines[-1]) <= 159
        assert sum('? keys' in line for line in lines) == 1
        assert len(lines) == 40

    def test_no_alerts_feed_credits_the_forecast_alone(self):
        lines = _render(160, 40, country_code="AR")
        assert lines[-1].startswith('Weather data by Open-Meteo  ')
        assert 'Alerts' not in lines[-1]

    def test_a_narrow_window_keeps_only_the_hint(self):
        lines = _render(30, 24)
        assert not any('Open-Meteo' in line for line in lines)
        assert lines[-1].strip() == '? keys' and len(lines) == 24

    def test_print_output_has_no_credit_row(self):
        lines = _render(160, 40, live=False)
        assert not any('Open-Meteo' in line or '? keys' in line for line in lines)


class TestJson:
    def test_sources_name_the_forecast_and_the_alerts_service(self):
        data = json.loads((FIXTURES / "open_meteo_forecast.json").read_text(encoding="utf-8"))
        runtime = WeatherRuntime(live=False, icons="emoji", lang="en", oneline=False,
                                 celsius=False, metric=False, shading=False)
        payload = build_payload(data, "Dublin", "IE", runtime, now=FIXED_NOW)
        assert payload["sources"] == {"forecast": "Open-Meteo", "air_quality": "Open-Meteo",
                                      "alerts": "Met Éireann"}
        payload = build_payload(data, "Buenos Aires", "AR", runtime, now=FIXED_NOW)
        assert payload["sources"]["alerts"] is None
