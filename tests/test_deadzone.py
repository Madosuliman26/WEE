import pytest

from gcs.input.controller import axis_to_direction


@pytest.mark.parametrize(
    "value, deadzone, expected",
    [
        (0.0, 0.5, 0),       # centre
        (0.05, 0.5, 0),      # tiny drift
        (-0.09, 0.5, 0),     # tiny drift, negative
        (0.3, 0.5, 0),       # light touch, still inside
        (0.55, 0.5, 1),      # pushed past the dead-zone
        (-0.55, 0.5, -1),    # pushed back
        (1.0, 0.5, 1),       # full forward
        (-1.0, 0.5, -1),     # full back
        (0.5, 0.5, 0),       # exactly on the edge counts as inside
        (-0.5, 0.5, 0),      # same, negative
    ],
)
def test_axis_to_direction(value, deadzone, expected):
    assert axis_to_direction(value, deadzone) == expected


def test_zero_deadzone_still_returns_zero_at_centre():
    assert axis_to_direction(0.0, 0.0) == 0


@pytest.mark.parametrize("bad", [-0.1, 1.0, 1.5])
def test_invalid_deadzone_raises(bad):
    with pytest.raises(ValueError):
        axis_to_direction(0.5, bad)