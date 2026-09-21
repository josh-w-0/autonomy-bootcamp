"""
TODO(bootcamper): write the tests for ``src/waypoint_utils.py`` in here.

The example below covers files that parse fine: with and without ``home``,
and files with comments and blank lines in them. The rest is yours:

- Bad data: a file whose top level isn't a mapping, waypoints missing
  ``lat``, ``lon``, or ``alt``, values that aren't numbers, YAML that
  doesn't parse, and a file that isn't there.
- Out of range: latitudes past +/-90 and longitudes past +/-180 get
  rejected.
- Nothing to work with: an empty file, an empty ``waypoints`` list, and
  ``sort_clockwise_sweep`` given a list of 0 or 1 waypoints.
- ``east_north_coordinate_offset_m``: offsets you worked out yourself,
  compared with ``pytest.approx``. Never use ``==`` on meters.
- Ordering: with no ``home``, ``sort_clockwise_sweep`` goes clockwise
  starting from north.
- With a ``home``: the order starts in home's direction instead, and goes
  back to starting at north if home is right on top of the centroid.
- Two waypoints in the same direction: the closer one comes first.
- Parsing gives you frozen ``Coordinate`` objects that can't be changed.

Graded by ``warg run utils grade-tests``: pass on the real code, 90% branch
coverage, and fail on every broken copy in ``grader/mutants/``.
"""

import dataclasses
import math

import pytest

from src.constants import EARTH_RADIUS_M
from src.types import Coordinate
from src.waypoint_utils import (
    east_north_coordinate_offset_m,
    parse_waypoints_file,
    sort_clockwise_sweep,
)

# The helper and the test below are given to you.


def write_to_tmp_waypoints_file(tmp_path, text):
    """Write ``text`` to a YAML file and hand back its path.

    ``tmp_path`` is a pytest fixture: a fresh empty directory per test.
    """
    path = tmp_path / "waypoints.yaml"
    path.write_text(text)
    return path


# One test, three files. ``parametrize`` runs the test body once per
# ``(text, expected)`` pair, and ``ids`` names each run so a failure tells you
# which file broke.
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            """
            home: {lat: 1, lon: 2, alt: 3}
            waypoints:
              - {lat: 4, lon: 5, alt: 6}
            """,
            (Coordinate(1, 2, 3), [Coordinate(4, 5, 6)]),
        ),
        (
            """
            waypoints:
              - {lat: 4, lon: 5, alt: 6}
              - {lat: 7, lon: 8, alt: 9}
            """,
            (None, [Coordinate(4, 5, 6), Coordinate(7, 8, 9)]),
        ),
        (
            """
            # a lap

            home: {lat: 1, lon: 2, alt: 3}

            waypoints:
              # first leg
              - {lat: 4, lon: 5, alt: 6}
            """,
            (Coordinate(1, 2, 3), [Coordinate(4, 5, 6)]),
        ),
    ],
    ids=["home-and-waypoints", "no-home", "comments-and-blank-lines"],
)

def test_parse_waypoints_file_success(tmp_path, text, expected):
    path = write_to_tmp_waypoints_file(tmp_path, text)
    assert parse_waypoints_file(path) == expected

def test_parse_waypoints_missing_file(tmp_path):
    with pytest.raises(OSError):
        parse_waypoints_file(tmp_path / "does_not_exist.yaml")

def test_parse_waypoints_invalid_yaml(tmp_path):
    path = write_to_tmp_waypoints_file(tmp_path, "[unbalanced_bracket")
    with pytest.raises(ValueError, match="invalid YAML"):
        parse_waypoints_file(path)

def test_parse_waypoints_empty_file(tmp_path):
    path = write_to_tmp_waypoints_file(tmp_path, "")
    assert parse_waypoints_file(path) == (None, [])

def test_parse_waypoints_not_mapping(tmp_path):
    path = write_to_tmp_waypoints_file(tmp_path, "- just a list") ## Converts into "['just a list']"
    with pytest.raises(ValueError, match="expected a mapping"):
        parse_waypoints_file(path)

def test_parse_waypoints_not_list(tmp_path):
    path = write_to_tmp_waypoints_file(tmp_path, "waypoints: {lat: 1, lon: 2, alt: 3}")
    with pytest.raises(ValueError, match="'waypoints' must be a list"):
        parse_waypoints_file(path)

def test_parse_entry_not_dict(tmp_path):
    path = write_to_tmp_waypoints_file(tmp_path, "waypoints: ['not a dict']")
    with pytest.raises(ValueError, match="must be a mapping"):
        parse_waypoints_file(path)

def test_parse_entry_missing_keys(tmp_path):
    path = write_to_tmp_waypoints_file(tmp_path, "waypoints: [{lat: 1, lon: 2}]")
    with pytest.raises(ValueError, match="missing key"):
        parse_waypoints_file(path)

def test_parse_entry_non_numeric(tmp_path):
    path = write_to_tmp_waypoints_file(tmp_path, "waypoints: [{lat: 1, lon: 'foo', alt: 3}]")
    with pytest.raises(ValueError, match="non-numeric value"):
        parse_waypoints_file(path)

def test_parse_entry_out_of_range_lat(tmp_path):
    path = write_to_tmp_waypoints_file(tmp_path, "waypoints: [{lat: 91, lon: 2, alt: 3}]")
    with pytest.raises(ValueError, match="out of range"):
        parse_waypoints_file(path)

def test_parse_entry_out_of_range_lon(tmp_path):
    path = write_to_tmp_waypoints_file(tmp_path, "waypoints: [{lat: 1, lon: -181, alt: 3}]")
    with pytest.raises(ValueError, match="out of range"):
        parse_waypoints_file(path)

def test_coordinate_frozen(tmp_path):
    path = write_to_tmp_waypoints_file(tmp_path, "waypoints: [{lat: 1, lon: 2, alt: 3}]")
    _, wps = parse_waypoints_file(path)
    with pytest.raises(dataclasses.FrozenInstanceError):
        wps[0].lat = 5

def test_east_north_coordinate_offset_m():
    from_lat = 0.0
    from_lon = 0.0
    to_lat = 1.0  ## Move 1 degree north
    to_lon = 0.0
    east, north = east_north_coordinate_offset_m(from_lat, from_lon, to_lat, to_lon)
    assert east == pytest.approx(0.0)
    assert north == pytest.approx(math.radians(1.0) * EARTH_RADIUS_M)

    to_lat = 0.0
    to_lon = 1.0 ## Move 1 degree east
    east, north = east_north_coordinate_offset_m(from_lat, from_lon, to_lat, to_lon)
    assert east == pytest.approx(math.radians(1.0) * EARTH_RADIUS_M)
    assert north == pytest.approx(0.0)

    from_lat = 60.0 
    to_lat = 60.0 ## Move 1 degree east at 60 degrees latitude
    from_lon = 0.0
    to_lon = 1.0
    east, north = east_north_coordinate_offset_m(from_lat, from_lon, to_lat, to_lon)
    assert east == pytest.approx(math.radians(1.0) * math.cos(math.radians(60.0)) * EARTH_RADIUS_M)
    assert north == pytest.approx(0.0)

def test_sort_0_1_waypoints(): ## If you have 0 or 1 waypoints, the order is trivial and should be returned as is.
    assert sort_clockwise_sweep([]) == []
    wp = Coordinate(1, 1, 1)
    assert sort_clockwise_sweep([wp]) == [wp]

def test_sort_no_home():
    wp_n = Coordinate(1, 0, 0)
    wp_e = Coordinate(0, 1, 0)
    wp_s = Coordinate(-1, 0, 0)
    wp_w = Coordinate(0, -1, 0)
    wps = [wp_s, wp_e, wp_w, wp_n]
    assert sort_clockwise_sweep(wps) == [wp_n, wp_e, wp_s, wp_w] ## Note that the order is clockwise.

def test_sort_with_home():
    wp_n = Coordinate(1, 0, 0)
    wp_e = Coordinate(0, 1, 0)
    wp_s = Coordinate(-1, 0, 0)
    wp_w = Coordinate(0, -1, 0)
    wps = [wp_n, wp_e, wp_s, wp_w]
    home = Coordinate(-2, 0, 0) ## The sweep should start from the south, since home is in that direction.
    assert sort_clockwise_sweep(wps, home) == [wp_s, wp_w, wp_n, wp_e]

def test_sort_home_at_centroid():
    wp_n = Coordinate(1, 0, 0)
    wp_e = Coordinate(0, 1, 0)
    wp_s = Coordinate(-1, 0, 0)
    wp_w = Coordinate(0, -1, 0)
    wps = [wp_s, wp_e, wp_w, wp_n]
    home = Coordinate(0, 0, 0) ## Home is at the centroid of the waypoints, so the order should start from north (default).
    assert sort_clockwise_sweep(wps, home) == [wp_n, wp_e, wp_s, wp_w]

def test_sort_same_direction():
    wp_n_near = Coordinate(1, 0, 0)
    wp_n_far = Coordinate(2, 0, 0)
    wp_s_far = Coordinate(-2, 0, 0)
    wp_s_near = Coordinate(-1, 0, 0)
    wps = [wp_n_far, wp_n_near, wp_s_near, wp_s_far] ## The waypoint closer to the centroid should come first in the order.
    assert sort_clockwise_sweep(wps) == [wp_n_near, wp_n_far, wp_s_near, wp_s_far]

