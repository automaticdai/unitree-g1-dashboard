"""Tests for gain preset multipliers."""

import importlib.util

import pytest

_HAS_PYSIDE = importlib.util.find_spec('PySide6') is not None
_HAS_RCLPY = importlib.util.find_spec('rclpy') is not None
pytestmark = pytest.mark.skipif(
    not (_HAS_PYSIDE and _HAS_RCLPY),
    reason='PySide6 and rclpy required',
)


def test_presets_are_relative_multipliers():
    from g1_dashboard.panels.joint_control_panel import GAIN_PRESETS

    assert set(GAIN_PRESETS.keys()) == {'Stiff', 'Default', 'Compliant'}
    assert GAIN_PRESETS['Default'] == (1.0, 1.0)
    assert GAIN_PRESETS['Stiff'][0] > GAIN_PRESETS['Default'][0]
    assert GAIN_PRESETS['Compliant'][0] < GAIN_PRESETS['Default'][0]


def test_preset_scales_per_joint_defaults():
    from g1_dashboard.config.robot_config import JOINT_BY_INDEX
    from g1_dashboard.panels.joint_control_panel import GAIN_PRESETS

    for joint in JOINT_BY_INDEX.values():
        for name, (kp_mul, kd_mul) in GAIN_PRESETS.items():
            kp = joint.default_kp * kp_mul
            kd = joint.default_kd * kd_mul
            assert kp >= 0, f'{name} gave negative kp on joint {joint.index}'
            assert kd >= 0, f'{name} gave negative kd on joint {joint.index}'
