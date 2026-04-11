"""ROS2 topic names and QoS configuration."""

from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy


# Default QoS for sensor data (best-effort for high-rate topics)
SENSOR_QOS = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
    durability=DurabilityPolicy.VOLATILE,
)

# Reliable QoS for commands and state
RELIABLE_QOS = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    history=HistoryPolicy.KEEP_LAST,
    depth=10,
    durability=DurabilityPolicy.VOLATILE,
)


class Topics:
    """ROS2 topic name constants."""

    JOINT_STATES = '/joint_states'
    JOINT_COMMANDS = '/joint_commands'
    IMU = '/imu/data'
    BATTERY = '/battery_state'
    ROBOT_STATE = '/robot_state'
    SAFETY_STATUS = '/safety_status'
    CAMERA_IMAGE = '/camera/image_raw'
    CAMERA_COMPRESSED = '/camera/image_raw/compressed'
    LIDAR_POINTS = '/lidar/points'
    TF = '/tf'
    HEARTBEAT = '/dashboard_heartbeat'
