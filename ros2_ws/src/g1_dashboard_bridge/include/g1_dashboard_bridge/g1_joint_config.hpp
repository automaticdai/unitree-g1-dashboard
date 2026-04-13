#ifndef G1_DASHBOARD_BRIDGE__G1_JOINT_CONFIG_HPP_
#define G1_DASHBOARD_BRIDGE__G1_JOINT_CONFIG_HPP_

#include <array>
#include <string>

namespace g1_dashboard_bridge
{

struct JointLimits
{
  double lower;
  double upper;
  double default_kp;
  double default_kd;
};

struct JointDef
{
  uint8_t index;
  const char * name;     // URDF joint name
  const char * group;
  JointLimits limits;
};

constexpr size_t NUM_JOINTS = 29;

// Joint table — must match g1_dashboard/config/robot_config.py exactly.
// Indices 0-28 follow Unitree firmware ordering.
constexpr std::array<JointDef, NUM_JOINTS> JOINT_TABLE = {{
  {0,  "left_hip_pitch_joint",       "Left Leg",  {-2.5307,  2.8798, 150.0, 2.0}},
  {1,  "left_hip_roll_joint",        "Left Leg",  {-0.5236,  2.9671, 150.0, 2.0}},
  {2,  "left_hip_yaw_joint",         "Left Leg",  {-2.7576,  2.7576, 150.0, 2.0}},
  {3,  "left_knee_joint",            "Left Leg",  {-0.0873,  2.8798, 300.0, 4.0}},
  {4,  "left_ankle_pitch_joint",     "Left Leg",  {-0.8727,  0.5236,  40.0, 2.0}},
  {5,  "left_ankle_roll_joint",      "Left Leg",  {-0.2618,  0.2618,  40.0, 2.0}},
  {6,  "right_hip_pitch_joint",      "Right Leg", {-2.5307,  2.8798, 150.0, 2.0}},
  {7,  "right_hip_roll_joint",       "Right Leg", {-2.9671,  0.5236, 150.0, 2.0}},
  {8,  "right_hip_yaw_joint",        "Right Leg", {-2.7576,  2.7576, 150.0, 2.0}},
  {9,  "right_knee_joint",           "Right Leg", {-0.0873,  2.8798, 300.0, 4.0}},
  {10, "right_ankle_pitch_joint",    "Right Leg", {-0.8727,  0.5236,  40.0, 2.0}},
  {11, "right_ankle_roll_joint",     "Right Leg", {-0.2618,  0.2618,  40.0, 2.0}},
  {12, "waist_yaw_joint",            "Waist",     {-2.618,   2.618,  200.0, 3.0}},
  {13, "waist_roll_joint",           "Waist",     {-0.52,    0.52,   200.0, 3.0}},
  {14, "waist_pitch_joint",          "Waist",     {-0.52,    0.52,   200.0, 3.0}},
  {15, "left_shoulder_pitch_joint",  "Left Arm",  {-3.0892,  2.6704, 100.0, 2.0}},
  {16, "left_shoulder_roll_joint",   "Left Arm",  {-1.5882,  2.2515, 100.0, 2.0}},
  {17, "left_shoulder_yaw_joint",    "Left Arm",  {-2.618,   2.618,  100.0, 2.0}},
  {18, "left_elbow_joint",           "Left Arm",  {-1.0472,  2.0944, 100.0, 2.0}},
  {19, "left_wrist_roll_joint",      "Left Arm",  {-1.9722,  1.9722,  20.0, 1.0}},
  {20, "left_wrist_pitch_joint",     "Left Arm",  {-1.6144,  1.6144,  20.0, 1.0}},
  {21, "left_wrist_yaw_joint",       "Left Arm",  {-1.6144,  1.6144,  20.0, 1.0}},
  {22, "right_shoulder_pitch_joint", "Right Arm", {-3.0892,  2.6704, 100.0, 2.0}},
  {23, "right_shoulder_roll_joint",  "Right Arm", {-2.2515,  1.5882, 100.0, 2.0}},
  {24, "right_shoulder_yaw_joint",   "Right Arm", {-2.618,   2.618,  100.0, 2.0}},
  {25, "right_elbow_joint",          "Right Arm", {-1.0472,  2.0944, 100.0, 2.0}},
  {26, "right_wrist_roll_joint",     "Right Arm", {-1.9722,  1.9722,  20.0, 1.0}},
  {27, "right_wrist_pitch_joint",    "Right Arm", {-1.6144,  1.6144,  20.0, 1.0}},
  {28, "right_wrist_yaw_joint",      "Right Arm", {-1.6144,  1.6144,  20.0, 1.0}},
}};

inline double clamp_to_limits(uint8_t index, double value)
{
  if (index >= NUM_JOINTS) {
    return value;
  }
  const auto & lim = JOINT_TABLE[index].limits;
  if (value < lim.lower) { return lim.lower; }
  if (value > lim.upper) { return lim.upper; }
  return value;
}

}  // namespace g1_dashboard_bridge

#endif  // G1_DASHBOARD_BRIDGE__G1_JOINT_CONFIG_HPP_
