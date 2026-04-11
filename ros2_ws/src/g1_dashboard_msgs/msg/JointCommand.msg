uint8 joint_index           # 0-28 (see joint index reference)
float64 target_position     # radians
float64 target_velocity     # rad/s (0.0 for position-only)
float64 kp                  # proportional gain
float64 kd                  # derivative gain
float64 feedforward_torque  # N.m (0.0 for PD-only)
