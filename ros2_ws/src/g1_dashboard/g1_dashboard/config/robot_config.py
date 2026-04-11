"""Unitree G1 joint definitions, limits, and groupings."""

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class JointDef:
    """Definition of a single robot joint."""
    index: int
    name: str           # URDF joint name
    group: str           # Body group name
    lower: float         # Lower limit (radians)
    upper: float         # Upper limit (radians)
    default_kp: float    # Default proportional gain
    default_kd: float    # Default derivative gain


# All 29 DOF joint definitions for Unitree G1
JOINTS: List[JointDef] = [
    # Left Leg (0-5)
    JointDef(0,  'left_hip_pitch_joint',       'Left Leg',  -2.5307,  2.8798, 150.0, 2.0),
    JointDef(1,  'left_hip_roll_joint',        'Left Leg',  -0.5236,  2.9671, 150.0, 2.0),
    JointDef(2,  'left_hip_yaw_joint',         'Left Leg',  -2.7576,  2.7576, 150.0, 2.0),
    JointDef(3,  'left_knee_joint',            'Left Leg',  -0.0873,  2.8798, 300.0, 4.0),
    JointDef(4,  'left_ankle_pitch_joint',     'Left Leg',  -0.8727,  0.5236,  40.0, 2.0),
    JointDef(5,  'left_ankle_roll_joint',      'Left Leg',  -0.2618,  0.2618,  40.0, 2.0),
    # Right Leg (6-11)
    JointDef(6,  'right_hip_pitch_joint',      'Right Leg', -2.5307,  2.8798, 150.0, 2.0),
    JointDef(7,  'right_hip_roll_joint',       'Right Leg', -2.9671,  0.5236, 150.0, 2.0),
    JointDef(8,  'right_hip_yaw_joint',        'Right Leg', -2.7576,  2.7576, 150.0, 2.0),
    JointDef(9,  'right_knee_joint',           'Right Leg', -0.0873,  2.8798, 300.0, 4.0),
    JointDef(10, 'right_ankle_pitch_joint',    'Right Leg', -0.8727,  0.5236,  40.0, 2.0),
    JointDef(11, 'right_ankle_roll_joint',     'Right Leg', -0.2618,  0.2618,  40.0, 2.0),
    # Waist (12-14)
    JointDef(12, 'waist_yaw_joint',            'Waist',     -2.618,   2.618,  200.0, 3.0),
    JointDef(13, 'waist_roll_joint',           'Waist',     -0.52,    0.52,   200.0, 3.0),
    JointDef(14, 'waist_pitch_joint',          'Waist',     -0.52,    0.52,   200.0, 3.0),
    # Left Arm (15-21)
    JointDef(15, 'left_shoulder_pitch_joint',  'Left Arm',  -3.0892,  2.6704, 100.0, 2.0),
    JointDef(16, 'left_shoulder_roll_joint',   'Left Arm',  -1.5882,  2.2515, 100.0, 2.0),
    JointDef(17, 'left_shoulder_yaw_joint',    'Left Arm',  -2.618,   2.618,  100.0, 2.0),
    JointDef(18, 'left_elbow_joint',           'Left Arm',  -1.0472,  2.0944, 100.0, 2.0),
    JointDef(19, 'left_wrist_roll_joint',      'Left Arm',  -1.9722,  1.9722,  20.0, 1.0),
    JointDef(20, 'left_wrist_pitch_joint',     'Left Arm',  -1.6144,  1.6144,  20.0, 1.0),
    JointDef(21, 'left_wrist_yaw_joint',       'Left Arm',  -1.6144,  1.6144,  20.0, 1.0),
    # Right Arm (22-28)
    JointDef(22, 'right_shoulder_pitch_joint', 'Right Arm', -3.0892,  2.6704, 100.0, 2.0),
    JointDef(23, 'right_shoulder_roll_joint',  'Right Arm', -2.2515,  1.5882, 100.0, 2.0),
    JointDef(24, 'right_shoulder_yaw_joint',   'Right Arm', -2.618,   2.618,  100.0, 2.0),
    JointDef(25, 'right_elbow_joint',          'Right Arm', -1.0472,  2.0944, 100.0, 2.0),
    JointDef(26, 'right_wrist_roll_joint',     'Right Arm', -1.9722,  1.9722,  20.0, 1.0),
    JointDef(27, 'right_wrist_pitch_joint',    'Right Arm', -1.6144,  1.6144,  20.0, 1.0),
    JointDef(28, 'right_wrist_yaw_joint',      'Right Arm', -1.6144,  1.6144,  20.0, 1.0),
]

# Indices that are locked in the 23-DOF variant
LOCKED_23DOF = {13, 14, 19, 20, 21, 26, 27, 28}

# Joint index lookup by URDF name
JOINT_BY_NAME: Dict[str, JointDef] = {j.name: j for j in JOINTS}

# Joint index lookup by index
JOINT_BY_INDEX: Dict[int, JointDef] = {j.index: j for j in JOINTS}

# Group ordering for the UI
JOINT_GROUPS: List[str] = ['Left Leg', 'Right Leg', 'Waist', 'Left Arm', 'Right Arm']


def joints_in_group(group: str) -> List[JointDef]:
    """Return all joints belonging to a body group."""
    return [j for j in JOINTS if j.group == group]


def clamp_to_limits(index: int, value: float) -> float:
    """Clamp a joint value to its URDF limits."""
    joint = JOINT_BY_INDEX[index]
    return max(joint.lower, min(joint.upper, value))
