"""Forward kinematics for the Unitree G1 humanoid.

Uses a hard-coded approximate skeleton with link offsets derived from G1
physical dimensions (~1.32m tall). This enables rendering a stick-figure
digital twin without requiring the official URDF meshes.

When the real URDF is available, `RobotSkeleton` can be built from
yourdfpy instead — the public API (compute_fk, link_positions) stays the
same so the renderer doesn't change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence

import numpy as np

from g1_dashboard.utils.transforms import (
    Mat4, compose, identity, rotation_axis, translation,
)


# Rotation axes (unit vectors) for each joint type
AXIS_X = np.array([1.0, 0.0, 0.0])
AXIS_Y = np.array([0.0, 1.0, 0.0])
AXIS_Z = np.array([0.0, 0.0, 1.0])


@dataclass
class Link:
    """One node of the kinematic tree.

    Attributes:
        name: URDF link name
        parent: Parent link name (None for root)
        origin_xyz: Translation offset from parent frame (meters)
        joint_axis: Rotation axis in parent frame (for revolute joints)
        joint_index: Robot joint index (0-28) driving this link's rotation;
                     None if the link has no driving joint (fixed offset)
    """
    name: str
    parent: str | None
    origin_xyz: np.ndarray
    joint_axis: np.ndarray = field(default_factory=lambda: AXIS_Z.copy())
    joint_index: int | None = None


# Approximate G1 skeleton — link offsets in meters.
# Axes: X forward, Y left, Z up (REP-103 convention).
# Values are approximate; replace with URDF-derived values when meshes are integrated.
G1_LINKS: List[Link] = [
    # Root (pelvis)
    Link('pelvis', None, np.array([0.0, 0.0, 0.793])),

    # Waist chain — drives torso
    Link('waist_yaw',   'pelvis',       np.array([0.0, 0.0, 0.0]),   AXIS_Z, 12),
    Link('waist_roll',  'waist_yaw',    np.array([0.0, 0.0, 0.0]),   AXIS_X, 13),
    Link('waist_pitch', 'waist_roll',   np.array([0.0, 0.0, 0.0]),   AXIS_Y, 14),
    Link('torso',       'waist_pitch',  np.array([0.0, 0.0, 0.18])),   # fixed offset up to shoulders
    Link('head',        'torso',        np.array([0.0, 0.0, 0.22])),

    # Left leg chain (down from pelvis)
    Link('left_hip_pitch',   'pelvis',            np.array([0.0,  0.085, -0.065]), AXIS_Y, 0),
    Link('left_hip_roll',    'left_hip_pitch',    np.array([0.0,  0.0,   0.0]),    AXIS_X, 1),
    Link('left_hip_yaw',     'left_hip_roll',     np.array([0.0,  0.0,   0.0]),    AXIS_Z, 2),
    Link('left_knee',        'left_hip_yaw',      np.array([0.0,  0.0,  -0.30]),   AXIS_Y, 3),
    Link('left_ankle_pitch', 'left_knee',         np.array([0.0,  0.0,  -0.30]),   AXIS_Y, 4),
    Link('left_ankle_roll',  'left_ankle_pitch',  np.array([0.0,  0.0,   0.0]),    AXIS_X, 5),
    Link('left_foot',        'left_ankle_roll',   np.array([0.06, 0.0,  -0.04])),

    # Right leg chain
    Link('right_hip_pitch',   'pelvis',             np.array([0.0, -0.085, -0.065]), AXIS_Y, 6),
    Link('right_hip_roll',    'right_hip_pitch',    np.array([0.0,  0.0,   0.0]),    AXIS_X, 7),
    Link('right_hip_yaw',     'right_hip_roll',     np.array([0.0,  0.0,   0.0]),    AXIS_Z, 8),
    Link('right_knee',        'right_hip_yaw',      np.array([0.0,  0.0,  -0.30]),   AXIS_Y, 9),
    Link('right_ankle_pitch', 'right_knee',         np.array([0.0,  0.0,  -0.30]),   AXIS_Y, 10),
    Link('right_ankle_roll',  'right_ankle_pitch',  np.array([0.0,  0.0,   0.0]),    AXIS_X, 11),
    Link('right_foot',        'right_ankle_roll',   np.array([0.06, 0.0,  -0.04])),

    # Left arm chain (out from torso)
    Link('left_shoulder_pitch', 'torso',                  np.array([0.0, 0.18, 0.08]), AXIS_Y, 15),
    Link('left_shoulder_roll',  'left_shoulder_pitch',    np.array([0.0, 0.0,  0.0]),  AXIS_X, 16),
    Link('left_shoulder_yaw',   'left_shoulder_roll',     np.array([0.0, 0.0,  0.0]),  AXIS_Z, 17),
    Link('left_elbow',          'left_shoulder_yaw',      np.array([0.0, 0.0, -0.23]), AXIS_Y, 18),
    Link('left_wrist_roll',     'left_elbow',             np.array([0.0, 0.0, -0.20]), AXIS_Z, 19),
    Link('left_wrist_pitch',    'left_wrist_roll',        np.array([0.0, 0.0,  0.0]),  AXIS_Y, 20),
    Link('left_wrist_yaw',      'left_wrist_pitch',       np.array([0.0, 0.0,  0.0]),  AXIS_X, 21),
    Link('left_hand',           'left_wrist_yaw',         np.array([0.0, 0.0, -0.08])),

    # Right arm chain
    Link('right_shoulder_pitch', 'torso',                  np.array([0.0, -0.18, 0.08]), AXIS_Y, 22),
    Link('right_shoulder_roll',  'right_shoulder_pitch',   np.array([0.0,  0.0,  0.0]),  AXIS_X, 23),
    Link('right_shoulder_yaw',   'right_shoulder_roll',    np.array([0.0,  0.0,  0.0]),  AXIS_Z, 24),
    Link('right_elbow',          'right_shoulder_yaw',     np.array([0.0,  0.0, -0.23]), AXIS_Y, 25),
    Link('right_wrist_roll',     'right_elbow',            np.array([0.0,  0.0, -0.20]), AXIS_Z, 26),
    Link('right_wrist_pitch',    'right_wrist_roll',       np.array([0.0,  0.0,  0.0]),  AXIS_Y, 27),
    Link('right_wrist_yaw',      'right_wrist_pitch',      np.array([0.0,  0.0,  0.0]),  AXIS_X, 28),
    Link('right_hand',           'right_wrist_yaw',        np.array([0.0,  0.0, -0.08])),
]


@dataclass
class FKResult:
    """Result of a forward kinematics computation."""
    link_transforms: Dict[str, Mat4]      # link name -> world transform
    joint_positions: Dict[int, np.ndarray]  # joint index -> 3D position
    link_positions: Dict[str, np.ndarray]   # link name -> 3D position


class RobotSkeleton:
    """G1 kinematic tree with forward kinematics."""

    def __init__(self, links: Sequence[Link] = G1_LINKS):
        self._links = list(links)
        self._by_name = {lk.name: lk for lk in self._links}
        self._root = next((lk for lk in self._links if lk.parent is None), None)
        if self._root is None:
            raise ValueError('skeleton has no root link')

        # Validate: every parent reference resolves
        for link in self._links:
            if link.parent is not None and link.parent not in self._by_name:
                raise ValueError(
                    f'link {link.name!r} references unknown parent {link.parent!r}')

        # Children lookup for tree traversal
        self._children: Dict[str, List[Link]] = {lk.name: [] for lk in self._links}
        for link in self._links:
            if link.parent is not None:
                self._children[link.parent].append(link)

    @property
    def links(self) -> List[Link]:
        return list(self._links)

    @property
    def root(self) -> Link:
        return self._root

    def children(self, name: str) -> List[Link]:
        return list(self._children.get(name, []))

    def compute_fk(self, joint_positions: Sequence[float]) -> FKResult:
        """Compute world transforms for every link from joint angles.

        Args:
            joint_positions: List of 29 joint angles in radians. Entries for
                             joint indices not present in the skeleton are
                             ignored.

        Returns:
            FKResult with transforms, joint positions, link positions.
        """
        link_transforms: Dict[str, Mat4] = {}
        joint_positions_out: Dict[int, np.ndarray] = {}
        link_positions_out: Dict[str, np.ndarray] = {}

        def walk(link: Link, parent_tf: Mat4) -> None:
            # Translation from parent origin to this link's joint frame
            tf = parent_tf @ translation(*link.origin_xyz)

            # Apply joint rotation if this link is driven by a joint
            if link.joint_index is not None and link.joint_index < len(joint_positions):
                angle = float(joint_positions[link.joint_index])
                tf = tf @ rotation_axis(link.joint_axis, angle)
                # Joint position = translation-only part of the transform
                joint_positions_out[link.joint_index] = tf[:3, 3].copy()

            link_transforms[link.name] = tf
            link_positions_out[link.name] = tf[:3, 3].copy()

            for child in self._children[link.name]:
                walk(child, tf)

        walk(self._root, identity())
        return FKResult(link_transforms, joint_positions_out, link_positions_out)

    def joint_index_from_name(self, link_name: str) -> int | None:
        link = self._by_name.get(link_name)
        return link.joint_index if link is not None else None


def zero_pose() -> List[float]:
    """Return a joint angle vector of 29 zeros (default home pose)."""
    return [0.0] * 29
