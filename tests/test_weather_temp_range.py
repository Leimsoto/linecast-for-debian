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


class TestFlash:
    def test_a_note_comes_down_when_its_time_is_up(self, monkeypatch):
        from linecast import _live
        from linecast.weather import WeatherApp
        view = WeatherApp({}, [], None, 43.7, -79.4, _runtime())
        view.flash(["hello"], seconds=0.0)
        monkeypatch.setattr(_live._time, "monotonic", lambda: 10 ** 9)
        assert view.flash_overlay(80, 24) == ""
        assert view._flash is None

    def test_a_note_is_boxed_while_it_is_up(self):
        from linecast.weather import WeatherApp
        view = WeatherApp({}, [], None, 43.7, -79.4, _runtime())
        view.flash(["hello there"], seconds=60.0)
        box = view.flash_overlay(80, 24)
        assert "hello there" in box and "┌" in box


class TestAxisLabels:
    def _blank_rows(self, n_rows, graph_w):
        return [[("\u2800", 0.0)] * graph_w for _ in range(n_rows)]

    def test_labels_the_two_ends_at_the_left_edge(self):
        from linecast._weather_hourly import _compute_axis_overlays
        overlays = {}
        _compute_axis_overlays((-15, 100), self._blank_rows(8, 80), 8, 80, overlays)
        assert overlays == {0: [(1, "100°", overlays[0][0][2])],
                            7: [(1, "-15°", overlays[7][0][2])]}

    def test_forecast_bounds_are_rounded_to_whole_degrees(self):
        from linecast._weather_hourly import _compute_axis_overlays
        overlays = {}
        _compute_axis_overlays((26.4, 63.6), self._blank_rows(2, 40), 2, 40, overlays)
        assert [items[0][1] for _r, items in sorted(overlays.items())] == ["64°", "26°"]

    def test_sits_just_past_the_now_line(self):
        from linecast._weather_hourly import _compute_axis_overlays
        overlays = {}
        _compute_axis_overlays((58.0, 75.0), self._blank_rows(8, 120), 8, 120, overlays,
                               now_col=2)
        assert all(items[0][0] == 3 for items in overlays.values())

    def test_moves_to_the_right_edge_when_the_curve_is_in_the_way(self):
        from linecast._weather_hourly import _compute_axis_overlays
        rows = self._blank_rows(2, 40)
        rows[0][1] = ("\u2847", 20.0)  # dots under the left label's first cell
        overlays = {}
        _compute_axis_overlays((10.0, 20.0), rows, 2, 40, overlays)
        assert overlays[0] == [(40 - 4, "20°", overlays[0][0][2])]

    def test_skips_an_end_whose_edges_are_both_taken(self):
        from linecast._weather_hourly import _compute_axis_overlays
        rows = self._blank_rows(2, 40)
        overlays = {0: [(0, "20°", (1, 2, 3)), (36, "20°", (1, 2, 3))]}
        _compute_axis_overlays((10.0, 20.0), rows, 2, 40, overlays)
        assert len(overlays[0]) == 2 and overlays[1][0][1] == "10°"
