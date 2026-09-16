"""The temperature graphs' scale under --temp-range."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from linecast._runtime import WeatherRuntime, weather_parser
from linecast._weather_historical import HistoricalAverages, temperature_scale


def _archive(year_high, year_low):
    return HistoricalAverages(avg_high=60.0, avg_low=40.0, avg_precip=0.1, years=10,
                              year_high=year_high, year_low=year_low)


def _runtime(argv=(), environ=None):
    namespace = weather_parser().parse_args(["--print", *argv])
    return WeatherRuntime.from_sources(namespace, environ=environ or {})


class TestTemperatureScale:
    def test_forecast_is_the_forecast(self):
        rt = _runtime(["--temp-range", "forecast"])
        assert temperature_scale(rt, _archive(91.3, -3.6), (52.0, 75.0)) == (52.0, 75.0)

    def test_climate_is_the_typical_years_extremes_unpadded(self):
        assert temperature_scale(_runtime(), _archive(91.3, -3.6), (52.0, 75.0)) == (-3.6, 91.3)

    def test_climate_widens_to_a_forecast_past_the_usual_year(self):
        # A heat wave beyond the usual year touches the top, not the ceiling
        assert temperature_scale(_runtime(), _archive(91.3, -3.6), (70.0, 103.4)) == (-3.6, 103.4)
        assert temperature_scale(_runtime(), _archive(91.3, -3.6), (-21.0, 10.0)) == (-21.0, 91.3)

    def test_climate_without_an_archive_is_the_forecast(self):
        assert temperature_scale(_runtime(), None, (52.0, 75.0)) == (52.0, 75.0)
        assert temperature_scale(_runtime(), _archive(None, None), (52.0, 75.0)) == (52.0, 75.0)

    def test_world_is_the_same_everywhere(self):
        assert temperature_scale(_runtime(["--temp-range", "world", "--fahrenheit"]),
                                 _archive(91.3, -3.6), (52.0, 75.0)) == (-40, 122)
        assert temperature_scale(_runtime(["--temp-range", "world", "--celsius"]),
                                 None, (10.0, 20.0)) == (-40, 50)

    def test_world_widens_to_a_forecast_past_its_ends(self):
        rt = _runtime(["--temp-range", "world", "--celsius"])
        assert temperature_scale(rt, None, (30.0, 52.0)) == (-40, 52.0)


class TestTempRangeFlag:
    def test_climate_by_default(self):
        assert _runtime().temp_range == "climate"

    def test_flag_picks_a_scale(self):
        assert _runtime(["--temp-range", "climate"]).temp_range == "climate"
        assert _runtime(["--temp-range=world"]).temp_range == "world"
