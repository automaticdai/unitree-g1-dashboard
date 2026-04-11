std_msgs/Header header
bool limits_active               # Joint limit enforcement enabled
bool estop_active                # Emergency stop engaged
bool command_forwarding_enabled  # Commands being sent to robot
bool heartbeat_ok                # Frontend heartbeat received recently
float32 heartbeat_age            # Seconds since last heartbeat
uint32 commands_rejected         # Count of rejected commands (limit violations)
