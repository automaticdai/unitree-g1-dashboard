"""Tests for motor temperature color mapping.

Widget construction requires a QApplication; we only test the pure
_temp_color mapping function and the name abbreviation helper.
"""

import importlib.util

import pytest

_HAS_PYSIDE = importlib.util.find_spec('PySide6') is not None
pytestmark = pytest.mark.skipif(not _HAS_PYSIDE, reason='PySide6 required')


def test_unknown_temp_is_grey():
    from g1_dashboard.widgets.motor_temp_heatmap import _temp_color
    c = _temp_color(0.0)
    assert (c.red(), c.green(), c.blue()) == (60, 60, 60)


def test_low_temp_is_green():
    from g1_dashboard.widgets.motor_temp_heatmap import _temp_color
    c = _temp_color(25.0)
    assert c.green() > c.red()
    assert c.green() > c.blue()


def test_warning_temp_is_amber():
    from g1_dashboard.widgets.motor_temp_heatmap import _temp_color, TEMP_OK, TEMP_WARN
    c = _temp_color((TEMP_OK + TEMP_WARN) / 2)
    assert c.red() >= 100
    assert c.green() >= 100
    assert c.blue() < 100


def test_high_temp_is_red():
    from g1_dashboard.widgets.motor_temp_heatmap import _temp_color, TEMP_WARN
    c = _temp_color(TEMP_WARN + 20.0)
    assert c.red() > c.green()
    assert c.red() > c.blue()


def test_short_name_left_hip_pitch():
    from g1_dashboard.widgets.motor_temp_heatmap import _short_joint_name
    assert _short_joint_name('left_hip_pitch_joint') == 'LHP'


def test_short_name_right_knee():
    from g1_dashboard.widgets.motor_temp_heatmap import _short_joint_name
    assert _short_joint_name('right_knee_joint') == 'RK'


def test_short_name_waist_yaw():
    from g1_dashboard.widgets.motor_temp_heatmap import _short_joint_name
    result = _short_joint_name('waist_yaw_joint')
    assert result == 'WY'
