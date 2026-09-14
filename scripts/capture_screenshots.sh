#!/usr/bin/env bash
# Refresh linecast's README screenshots with Andrew's offscreen termshot tool.
#
# Usage:
#   scripts/capture_screenshots.sh all
#   scripts/capture_screenshots.sh weather moon maps hero
#
# The individual targets are weather, sunshine, year, moon, sky, tides, radar,
# maps, globe, and hero. "all" captures every app but NOT the hero: the shipped hero is a
# hand-composed whole-screen screenshot, and the hero target — a live
# auto-capture of four apps tiled on one offscreen desktop — would overwrite
# it, so it only runs when named explicitly. The app captures use live
# terminal mode so the header, footer, hidden cursor, and full-screen layout
# match what users actually see.
#
# termshot runs each shot in a private headless sway, so nothing here touches
# the desktop it runs from. Every frame is set in LINECAST_CAPTURE_FONT so the
# gallery stays in one typeface whatever the desktop terminal is using.

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_DIR=$(cd -- "$SCRIPT_DIR/.." && pwd)
SHOT_DIR="$REPO_DIR/screenshots"
GALLERY_DIR="$SHOT_DIR/gallery"
CAPTURE_TOOL=${LINECAST_CAPTURE_TOOL:-termshot}
CAPTURE_FONT=${LINECAST_CAPTURE_FONT:-MonaspiceNe Nerd Font:size=11}

WEATHER_PLACE=${LINECAST_CAPTURE_WEATHER_PLACE:-Dublin, Ireland}
YEAR_PLACE=${LINECAST_CAPTURE_YEAR_PLACE:-Reykjavík}
RADAR_PLACE=${LINECAST_CAPTURE_RADAR_PLACE:-auto}
RADAR_LANG=${LINECAST_CAPTURE_RADAR_LANG:-}
STREET_PLACE=${LINECAST_CAPTURE_STREET_PLACE:-Portland, Maine}
TERRAIN_PLACE=${LINECAST_CAPTURE_TERRAIN_PLACE:-Innsbruck}
GLOBE_PLACE=${LINECAST_CAPTURE_GLOBE_PLACE:-auto}
TIDE_STATION=${LINECAST_CAPTURE_TIDE_STATION:-8418150}
ASTRO_LOCATION=${LINECAST_CAPTURE_ASTRO_LOCATION:-43.676,-70.371}
ARCTIC_PLACE=${LINECAST_CAPTURE_ARCTIC_PLACE:-Longyearbyen}
ANTARCTIC_PLACE=${LINECAST_CAPTURE_ANTARCTIC_PLACE:-Vostok Station}
OKINAWA_LOCATION=${LINECAST_CAPTURE_OKINAWA_LOCATION:-26.2124,127.6809}

usage() {
    cat <<'EOF'
Usage: scripts/capture_screenshots.sh [TARGET...]

Targets:
  all        capture every app (default; leaves the hand-made hero alone)
  weather    weather.png, plus weather-reykjavik.png in Icelandic and
             weather-kyoto.png in Japanese, both metric
  sunshine   sunshine-day.png and sunshine-dusk.png
  year       sunshine-year.png for Reykjavík in Icelandic, plus -arctic and
             -antarctic at 78° either side
  moon       moon.png, plus moon-okinawa.png in Japanese and moon-calendar.png
  sky        sky.png on Orion, sky-allsky.png the whole sky at once, and
             sky-hawaiian.png the same winter sky in the Hawaiian tradition
  tides      tides.png
  radar      radar.png and radar.gif, wherever the scout finds weather
  maps       maps-street.png and maps-terrain.png
  globe      maps-globe.png, the planet in this hour's daylight, and
             maps-globe-clouds.png with this hour's clouds (differ every run)
  gallery    the frames GALLERY.md shows and the README does not, into
             screenshots/gallery: the radar in its fixed themes and its
             other layers, the sky in more traditions, the weather in a
             short window, the moon's month grid, a walking route
  hero       hero.png — the four apps tiled live on one offscreen desktop

Environment overrides:
  LINECAST_CAPTURE_TOOL
  LINECAST_CAPTURE_FONT      fontconfig pattern for every frame but the hero
  LINECAST_CAPTURE_WEATHER_PLACE
  LINECAST_CAPTURE_YEAR_PLACE
  LINECAST_CAPTURE_RADAR_PLACE   a place, or "auto" to let scout_radar.py pick
  LINECAST_CAPTURE_RADAR_LANG    language for a named radar place (auto brings its own)
  LINECAST_CAPTURE_STREET_PLACE
  LINECAST_CAPTURE_TERRAIN_PLACE
  LINECAST_CAPTURE_GLOBE_PLACE   LAT,LNG, or "auto" to centre on this hour's afternoon
  LINECAST_CAPTURE_TIDE_STATION
  LINECAST_CAPTURE_ASTRO_LOCATION
  LINECAST_CAPTURE_ARCTIC_PLACE
  LINECAST_CAPTURE_ANTARCTIC_PLACE
  LINECAST_CAPTURE_OKINAWA_LOCATION
EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    usage
    exit 0
fi

cd "$REPO_DIR"
mkdir -p "$SHOT_DIR" "$GALLERY_DIR"

exec 9>/tmp/linecast-capture-screenshots.lock
if ! flock -n 9; then
    printf 'capture_screenshots: another capture run is already active\n' >&2
    exit 1
fi

require() {
    command -v "$1" >/dev/null 2>&1 || {
        printf 'capture_screenshots: missing required command: %s\n' "$1" >&2
        exit 1
    }
}

require "$CAPTURE_TOOL"
require magick
require uv

# Every app is run as "linecast weather" and so on rather than by its bare
# name: the project declares only the linecast entry point, so a bare
# "uv run weather" falls through to whatever weather is on PATH, which on a
# machine with linecast installed is the released version, not this tree.

weather() {
    # The dashboard looks its best in a smallish window, where the chart
    # stays dense. The home frame is Dublin; two smaller ones show it in
    # other languages, metric, without making a thing of it.
    printf 'Capturing weather…\n'
    "$CAPTURE_TOOL" -s 110x34 -w 10 --font "$CAPTURE_FONT" -o "$SHOT_DIR/weather.png" \
        uv --directory "$REPO_DIR" run linecast weather --location "$WEATHER_PLACE"
    "$CAPTURE_TOOL" -s 100x30 -w 10 --font "$CAPTURE_FONT" -o "$SHOT_DIR/weather-reykjavik.png" \
        uv --directory "$REPO_DIR" run linecast weather --location "Reykjavík" --lang is --metric
    "$CAPTURE_TOOL" -s 100x30 -w 10 --font "$CAPTURE_FONT" -o "$SHOT_DIR/weather-kyoto.png" \
        uv --directory "$REPO_DIR" run linecast weather --location "Kyoto, Japan" --lang ja --metric
}

sunshine() {
    printf 'Capturing sunshine at midday…\n'
    "$CAPTURE_TOOL" -s 120x36 -w 4 --font "$CAPTURE_FONT" -o "$SHOT_DIR/sunshine-day.png" \
        uv --directory "$REPO_DIR" run python \
        "$REPO_DIR/scripts/capture_moment.py" \
        --at 2026-06-21T13:30 --location "$ASTRO_LOCATION" sunshine

    printf 'Capturing sunshine at dusk…\n'
    "$CAPTURE_TOOL" -s 120x36 -w 4 --font "$CAPTURE_FONT" -o "$SHOT_DIR/sunshine-dusk.png" \
        uv --directory "$REPO_DIR" run python \
        "$REPO_DIR/scripts/capture_moment.py" \
        --at 2026-06-21T20:15 --location "$ASTRO_LOCATION" sunshine
}

year() {
    # The year view for Reykjavík, in Icelandic, and at two places near the
    # poles, each with the pointer on the December solstice so the hover
    # tooltip is in frame. On a 120x36 terminal that is column 117, row 19 (noon). The
    # first hover only carries the pointer onto the window: a single warp
    # from outside arrives as a pointer enter, not the motion the app
    # listens for, so the second, real move is what raises the tooltip.
    #
    # "Today" is the June solstice, as in the day captures. capture_moment
    # reads --at in this machine's zone, so each is 13:30 local time in
    # Reykjavík, Svalbard, and at Vostok as seen from US Eastern; if that
    # drifts only the sun glyph's row moves.
    local place at name extra spec
    for spec in "$YEAR_PLACE|2026-06-21T09:30|sunshine-year.png|--lang is" \
                "$ARCTIC_PLACE|2026-06-21T07:30|sunshine-year-arctic.png|" \
                "$ANTARCTIC_PLACE|2026-06-21T04:30|sunshine-year-antarctic.png|"; do
        IFS='|' read -r place at name extra <<<"$spec"
        printf 'Capturing sunshine year view for %s…\n' "$place"
        "$CAPTURE_TOOL" -s 120x36 -w 6 --font "$CAPTURE_FONT" \
            --hover 100x12 --sleep 0.5 --hover 117x19 --sleep 1 \
            -o "$SHOT_DIR/$name" \
            uv --directory "$REPO_DIR" run python \
            "$REPO_DIR/scripts/capture_moment.py" \
            --at "$at" --location "$ASTRO_LOCATION" sunshine -- \
            --year --location "$place" $extra
    done
}

moon() {
    printf 'Capturing Moon…\n'
    "$CAPTURE_TOOL" -s 120x40 -w 4 --font "$CAPTURE_FONT" -o "$SHOT_DIR/moon.png" \
        uv --directory "$REPO_DIR" run python \
        "$REPO_DIR/scripts/capture_moment.py" \
        --at 2026-08-22T21:30 --location "$ASTRO_LOCATION" moon
    # Okinawa in Japanese, the evening after the mid-autumn full moon of
    # 2026, so the headline names the night 十六夜 and the calendar's
    # September carries 十五夜 on the 25th. capture_moment's --at lands as
    # the place's local time here. The calendar frame presses v and hovers
    # the 25th (column 84, row 27 on 120x40; the first hover only carries
    # the pointer onto the window, the second raises the chip).
    "$CAPTURE_TOOL" -s 120x40 -w 6 --font "$CAPTURE_FONT" -o "$SHOT_DIR/moon-okinawa.png" \
        uv --directory "$REPO_DIR" run python \
        "$REPO_DIR/scripts/capture_moment.py" \
        --at 2026-09-26T21:30 --location "$OKINAWA_LOCATION" moon -- \
        --lang ja --24h
    "$CAPTURE_TOOL" -s 120x40 -w 6 --font "$CAPTURE_FONT" --press v --sleep 2 \
        --hover 84x27 --sleep 1 --hover 85x27 --sleep 2 \
        -o "$SHOT_DIR/moon-calendar.png" \
        uv --directory "$REPO_DIR" run python \
        "$REPO_DIR/scripts/capture_moment.py" \
        --at 2026-09-26T21:30 --location "$OKINAWA_LOCATION" moon -- \
        --lang ja --24h
}

sky() {
    # Three fixed nights over Westbrook. Orion on a January evening, framed
    # by --at; the whole August sky at once, the way the almanacs print it;
    # and the same January sky drawn in the Hawaiian tradition, with the
    # navigators' star compass along the horizon. sky resolves its own
    # location, so it gets --location on its side of the -- as well.
    local at name spec
    for spec in "2026-01-15T21:00|sky.png|--at Orion" \
                "2026-08-15T22:30|sky-allsky.png|--facing S --fov 236" \
                "2026-01-15T21:00|sky-hawaiian.png|--facing S --culture hawaiian"; do
        IFS='|' read -r at name extra <<<"$spec"
        printf 'Capturing sky %s…\n' "$name"
        # shellcheck disable=SC2086
        "$CAPTURE_TOOL" -s 120x40 -w 6 --font "$CAPTURE_FONT" -o "$SHOT_DIR/$name" \
            uv --directory "$REPO_DIR" run python \
            "$REPO_DIR/scripts/capture_moment.py" \
            --at "$at" --location "$ASTRO_LOCATION" sky -- \
            --location "$ASTRO_LOCATION" $extra
    done
}

tides() {
    printf 'Capturing tides…\n'
    "$CAPTURE_TOOL" -s 120x36 -w 12 --font "$CAPTURE_FONT" -o "$SHOT_DIR/tides.png" \
        uv --directory "$REPO_DIR" run linecast tides --station "$TIDE_STATION"
}

# A radar frame is only worth taking where something is happening, and
# that moves: "auto" asks scout_radar.py which candidate city has the most
# weather on it right now, inside real radar coverage, and the frame then
# speaks that city's language. Resolved once; the radar and gallery targets
# share the answer.
RADAR_LANG_ARGS=()
resolve_radar_place() {
    [ -n "$RADAR_LANG" ] && RADAR_LANG_ARGS=(--lang "$RADAR_LANG")
    if [ "$RADAR_PLACE" = auto ]; then
        printf 'Scouting for weather…\n'
        local pick
        pick=$(uv --directory "$REPO_DIR" run python \
            "$REPO_DIR/scripts/scout_radar.py" --best)
        RADAR_PLACE=${pick%%$'\t'*}
        RADAR_LANG_ARGS=(--lang "${pick##*$'\t'}")
        printf 'Radar over %s, in %s\n' "$RADAR_PLACE" "${RADAR_LANG_ARGS[1]}"
    fi
}

radar() {
    require ffmpeg
    resolve_radar_place
    local radar_lang=("${RADAR_LANG_ARGS[@]}")
    printf 'Capturing radar still…\n'
    # No window padding: the radar frame is shot without the border.
    "$CAPTURE_TOOL" -s 120x36 -w 15 --pad 0 --font "$CAPTURE_FONT" \
        -o "$SHOT_DIR/radar.png" \
        uv --directory "$REPO_DIR" run linecast radar --location "$RADAR_PLACE" "${radar_lang[@]}"

    printf 'Capturing radar animation…\n'
    # Slow playback in the capture-only wrapper to a frame every half second,
    # record for longer than the 18 LibreWXR frames take so none is skipped,
    # collapse repeated screen states, then encode one complete loop at the
    # app's observed cadence.
    local radar_tmp_dir frame previous diff selected picked=0
    radar_tmp_dir=$(mktemp -d /tmp/linecast-radar-gif.XXXXXX)
    "$CAPTURE_TOOL" -s 120x36 -w 15 --pad 0 --font "$CAPTURE_FONT" \
        --gif 12 --fps 8 --gif-width 800 -o "$radar_tmp_dir/raw.gif" \
        uv --directory "$REPO_DIR" run python \
        "$REPO_DIR/scripts/capture_radar.py" --location "$RADAR_PLACE" "${radar_lang[@]}"

    magick "$radar_tmp_dir/raw.gif" -coalesce \
        "$radar_tmp_dir/raw-%03d.png"
    previous=""
    for frame in "$radar_tmp_dir"/raw-*.png; do
        if [ -n "$previous" ]; then
            diff=$(magick compare -metric AE "$previous" "$frame" null: \
                2>&1 || true)
            [ "${diff%% *}" = "0" ] && continue
        fi
        printf -v selected '%s/selected-%03d.png' "$radar_tmp_dir" "$picked"
        cp -- "$frame" "$selected"
        previous=$frame
        picked=$((picked + 1))
        [ "$picked" -eq 18 ] && break
    done
    if [ "$picked" -ne 18 ]; then
        printf 'capture_screenshots: radar recorded only %s/18 frames\n' \
            "$picked" >&2
        rm -rf -- "$radar_tmp_dir"
        return 1
    fi
    ffmpeg -y -loglevel error -framerate 2 \
        -i "$radar_tmp_dir/selected-%03d.png" \
        -vf "format=rgb24,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3" \
        -loop 0 "$SHOT_DIR/radar.gif"
    rm -rf -- "$radar_tmp_dir"
}

maps() {
    printf 'Capturing street map…\n'
    "$CAPTURE_TOOL" -s 120x38 -w 15 --font "$CAPTURE_FONT" -o "$SHOT_DIR/maps-street.png" \
        uv --directory "$REPO_DIR" run linecast maps --location "$STREET_PLACE" \
        --zoom 0.015

    printf 'Capturing terrain map…\n'
    "$CAPTURE_TOOL" -s 120x38 -w 15 --font "$CAPTURE_FONT" -o "$SHOT_DIR/maps-terrain.png" \
        uv --directory "$REPO_DIR" run linecast maps --view terrain \
        --location "$TERRAIN_PLACE" --zoom 1.5
}

globe() {
    # The globe is only worth looking at with the terminator across the
    # disk. "auto" centres the view 45° east of where the sun is overhead
    # right now, so the left of the disk is afternoon, the sunset line
    # crosses the right half, and the city lights are coming on beyond it,
    # whatever the hour here.
    if [ "$GLOBE_PLACE" = auto ]; then
        GLOBE_PLACE=$(python3 -c '
import datetime
now = datetime.datetime.now(datetime.timezone.utc)
subsolar = -15 * (now.hour + now.minute / 60 - 12)
lon = (subsolar + 45 + 180) % 360 - 180
print(f"20,{lon:.0f}")')
        printf 'Globe centred on %s\n' "$GLOBE_PLACE"
    fi
    printf 'Capturing globe…\n'
    # First the plain terrain planet with this hour's daylight, then --view
    # now with this hour's clouds as well: the daylight-only frame reads at
    # a glance, the cloudy one is the planet as it is. The clouds take a
    # while to arrive at this size, hence the longer settle.
    "$CAPTURE_TOOL" -s 120x38 -w 45 --font "$CAPTURE_FONT" \
        -o "$SHOT_DIR/maps-globe-clouds.png" \
        uv --directory "$REPO_DIR" run linecast maps --view now --zoom 130 \
        --location "$GLOBE_PLACE"
    # The frame is this hour's terminator and city lights — honestly
    # different every run — but *not* this hour's clouds: daylight alone
    # reads instantly, where the cloud layer makes a first-glance reader
    # work out what they are looking at.  So the capture opens the plain
    # terrain planet and presses S once the canvas is warm.
    "$CAPTURE_TOOL" -s 120x38 -w 25 --font "$CAPTURE_FONT" --key S --sleep 4 \
        -o "$SHOT_DIR/maps-globe.png" \
        uv --directory "$REPO_DIR" run linecast maps --view terrain --zoom 130 \
        --location "$GLOBE_PLACE"
}

gallery() {
    # The states the README leaves out. Smaller windows than the README
    # frames: these sit three abreast on the gallery page.
    resolve_radar_place
    local theme
    for theme in dusk ember ink marangai; do
        printf 'Capturing radar in %s…\n' "$theme"
        "$CAPTURE_TOOL" -s 100x30 -w 15 --pad 0 --font "$CAPTURE_FONT" \
            -o "$GALLERY_DIR/radar-$theme.png" \
            uv --directory "$REPO_DIR" run linecast radar --location "$RADAR_PLACE" \
            --theme "$theme" "${RADAR_LANG_ARGS[@]}"
    done
    printf 'Capturing radar satellite layer…\n'
    "$CAPTURE_TOOL" -s 100x30 -w 20 --pad 0 --font "$CAPTURE_FONT" \
        -o "$GALLERY_DIR/radar-satellite.png" \
        uv --directory "$REPO_DIR" run linecast radar --location "$RADAR_PLACE" \
        --layer satellite "${RADAR_LANG_ARGS[@]}"
    printf 'Capturing radar with temperature and wind…\n'
    "$CAPTURE_TOOL" -s 100x30 -w 20 --pad 0 --font "$CAPTURE_FONT" \
        -o "$GALLERY_DIR/radar-layers.png" \
        uv --directory "$REPO_DIR" run linecast radar --location "$RADAR_PLACE" \
        --layers temp,wind "${RADAR_LANG_ARGS[@]}"

    # The same January sky as the README's, in three more traditions.
    local culture
    for culture in chinese norse rey; do
        printf 'Capturing sky in the %s tradition…\n' "$culture"
        "$CAPTURE_TOOL" -s 120x40 -w 6 --font "$CAPTURE_FONT" \
            -o "$GALLERY_DIR/sky-$culture.png" \
            uv --directory "$REPO_DIR" run python \
            "$REPO_DIR/scripts/capture_moment.py" \
            --at 2026-01-15T21:00 --location "$ASTRO_LOCATION" sky -- \
            --location "$ASTRO_LOCATION" --facing S --culture "$culture"
    done

    printf 'Capturing weather in a short window…\n'
    "$CAPTURE_TOOL" -s 90x22 -w 10 --font "$CAPTURE_FONT" \
        -o "$GALLERY_DIR/weather-short.png" \
        uv --directory "$REPO_DIR" run linecast weather --location "$WEATHER_PLACE"

    printf 'Capturing the moon month grid…\n'
    "$CAPTURE_TOOL" -s 120x40 -w 4 --font "$CAPTURE_FONT" \
        -o "$GALLERY_DIR/moon-grid.png" \
        uv --directory "$REPO_DIR" run python \
        "$REPO_DIR/scripts/capture_moment.py" \
        --at 2026-09-13T21:30 --location "$ASTRO_LOCATION" moon -- --grid

    printf 'Capturing a walking route…\n'
    "$CAPTURE_TOOL" -s 120x38 -w 25 --font "$CAPTURE_FONT" \
        -o "$GALLERY_DIR/maps-route.png" \
        uv --directory "$REPO_DIR" run linecast maps --from "Portland, Maine" \
        --to "South Portland, Maine" --profile foot
}

hero() {
    printf 'Capturing hero…\n'
    # One real screenshot: four linecast apps tiled in termshot's private
    # compositor, composed by its gaps, borders, and the desktop wallpaper.
    # Pane order maps to dwindle's slots: big top-left, full-height right
    # column, then the two bottom-left quarters.
    "$CAPTURE_TOOL" --res 3840x2400 --font 'iA Writer Mono S:size=9' \
        -w 90 -o "$SHOT_DIR/hero.png" \
        --pane "uv --directory $REPO_DIR run linecast weather --location '$WEATHER_PLACE'" \
        --pane "uv --directory $REPO_DIR run linecast radar --location '$RADAR_PLACE'" \
        --pane "uv --directory $REPO_DIR run linecast maps --location '$STREET_PLACE' --zoom 0.015" \
        --pane "uv --directory $REPO_DIR run python $REPO_DIR/scripts/capture_moment.py --at 2026-06-21T13:30 --location '$ASTRO_LOCATION' sunshine"
}

run_target() {
    case "$1" in
        weather|sunshine|year|moon|sky|tides|radar|maps|globe|gallery|hero) "$1" ;;
        all)
            weather
            sunshine
            year
            moon
            sky
            tides
            radar
            maps
            globe
            gallery
            ;;
        *)
            printf 'capture_screenshots: unknown target: %s\n' "$1" >&2
            exit 2
            ;;
    esac
}

if [ "$#" -eq 0 ]; then
    set -- all
fi

for target in "$@"; do
    run_target "$target"
done

printf 'Screenshots refreshed in %s\n' "$SHOT_DIR"
