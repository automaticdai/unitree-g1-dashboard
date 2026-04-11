"""Tests for robot configuration module."""

from g1_dashboard.config.robot_config import (
    JOINTS, JOINT_BY_NAME, JOINT_BY_INDEX, JOINT_GROUPS,
    LOCKED_23DOF, joints_in_group, clamp_to_limits,
)


def test_joint_count():
    assert len(JOINTS) == 29


def test_joint_indices_unique():
    indices = [j.index for j in JOINTS]
    assert len(set(indices)) == 29
    assert sorted(indices) == list(range(29))


def test_joint_names_unique():
    names = [j.name for j in JOINTS]
    assert len(set(names)) == 29


def test_joint_by_name_lookup():
    j = JOINT_BY_NAME['left_knee_joint']
    assert j.index == 3
    assert j.group == 'Left Leg'


def test_joint_by_index_lookup():
    j = JOINT_BY_INDEX[12]
    assert j.name == 'waist_yaw_joint'
    assert j.group == 'Waist'


def test_joint_groups():
    assert len(JOINT_GROUPS) == 5
    total = sum(len(joints_in_group(g)) for g in JOINT_GROUPS)
    assert total == 29


def test_locked_23dof():
    assert 13 in LOCKED_23DOF  # waist_roll
    assert 14 in LOCKED_23DOF  # waist_pitch
    assert 19 in LOCKED_23DOF  # left_wrist_roll
    assert len(LOCKED_23DOF) == 8


def test_clamp_to_limits():
    # Within limits
    assert clamp_to_limits(3, 1.0) == 1.0
    # Below lower limit
    assert clamp_to_limits(3, -5.0) == JOINT_BY_INDEX[3].lower
    # Above upper limit
    assert clamp_to_limits(3, 10.0) == JOINT_BY_INDEX[3].upper


def test_all_joints_have_valid_limits():
    for joint in JOINTS:
        assert joint.lower < joint.upper, f'{joint.name} has invalid limits'
        assert joint.default_kp > 0
        assert joint.default_kd > 0
