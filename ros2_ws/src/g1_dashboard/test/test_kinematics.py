"""Tests for the G1 robot skeleton and forward kinematics."""

import math

import numpy as np
import pytest

from g1_dashboard.utils.kinematics import (
    G1_LINKS, RobotSkeleton, zero_pose,
)


def test_skeleton_has_expected_link_count():
    sk = RobotSkeleton()
    # 1 pelvis + 4 waist + 1 torso + 1 head + 7 left leg + 7 right leg + 9 left arm + 9 right arm
    assert len(sk.links) == len(G1_LINKS)


def test_skeleton_has_single_root():
    sk = RobotSkeleton()
    assert sk.root.name == 'pelvis'
    assert sk.root.parent is None


def test_skeleton_all_parents_resolve():
    sk = RobotSkeleton()
    names = {lk.name for lk in sk.links}
    for lk in sk.links:
        if lk.parent is not None:
            assert lk.parent in names


def test_skeleton_joint_indices_unique():
    sk = RobotSkeleton()
    seen = set()
    for lk in sk.links:
        if lk.joint_index is not None:
            assert lk.joint_index not in seen, f'duplicate joint index {lk.joint_index}'
            seen.add(lk.joint_index)
    # All 29 joint indices should be represented
    assert seen == set(range(29))


def test_skeleton_rejects_dangling_parent():
    from g1_dashboard.utils.kinematics import Link
    # Root link + link with dangling parent reference
    bad_links = [
        Link('root', None, np.zeros(3)),
        Link('a', 'nonexistent', np.zeros(3)),
    ]
    with pytest.raises(ValueError, match='parent'):
        RobotSkeleton(bad_links)


def test_skeleton_rejects_missing_root():
    from g1_dashboard.utils.kinematics import Link
    # Every link has a parent -> no root
    bad_links = [Link('a', 'b', np.zeros(3)), Link('b', 'a', np.zeros(3))]
    with pytest.raises(ValueError):
        RobotSkeleton(bad_links)


def test_fk_zero_pose_is_deterministic():
    sk = RobotSkeleton()
    fk1 = sk.compute_fk(zero_pose())
    fk2 = sk.compute_fk(zero_pose())
    for name in fk1.link_positions:
        assert np.allclose(fk1.link_positions[name], fk2.link_positions[name])


def test_fk_zero_pose_head_above_pelvis():
    sk = RobotSkeleton()
    fk = sk.compute_fk(zero_pose())
    pelvis_z = fk.link_positions['pelvis'][2]
    head_z = fk.link_positions['head'][2]
    assert head_z > pelvis_z + 0.2   # Head should be noticeably above pelvis


def test_fk_zero_pose_feet_near_ground():
    sk = RobotSkeleton()
    fk = sk.compute_fk(zero_pose())
    # Feet should be near Z=0 in the default pose (pelvis at 0.793, legs ~0.66 long)
    for foot in ('left_foot', 'right_foot'):
        assert fk.link_positions[foot][2] < 0.15


def test_fk_symmetric_legs_in_zero_pose():
    sk = RobotSkeleton()
    fk = sk.compute_fk(zero_pose())
    lh = fk.link_positions['left_hip_pitch']
    rh = fk.link_positions['right_hip_pitch']
    # Hips should mirror across Y
    assert lh[1] == pytest.approx(-rh[1], abs=1e-9)
    assert lh[0] == pytest.approx(rh[0], abs=1e-9)
    assert lh[2] == pytest.approx(rh[2], abs=1e-9)


def test_fk_knee_rotation_moves_foot():
    sk = RobotSkeleton()
    baseline = sk.compute_fk(zero_pose())

    pose = zero_pose()
    pose[3] = math.radians(45)   # left_knee pitch
    rotated = sk.compute_fk(pose)

    baseline_foot = baseline.link_positions['left_foot']
    rotated_foot = rotated.link_positions['left_foot']
    # Foot should have moved
    assert not np.allclose(baseline_foot, rotated_foot)


def test_fk_populates_all_29_joint_positions():
    sk = RobotSkeleton()
    fk = sk.compute_fk(zero_pose())
    assert set(fk.joint_positions.keys()) == set(range(29))


def test_fk_right_arm_on_right_side():
    sk = RobotSkeleton()
    fk = sk.compute_fk(zero_pose())
    # Right shoulder should be on Y < 0 in robot frame (right side)
    rs = fk.link_positions['right_shoulder_pitch']
    assert rs[1] < 0.0


def test_zero_pose_is_29_zeros():
    p = zero_pose()
    assert len(p) == 29
    assert all(v == 0.0 for v in p)
