"""ROS2 node for the G1 dashboard.

Subscribes to all relevant topics and emits Qt signals for thread-safe
GUI updates. Also publishes joint commands and heartbeat.
"""

import time

from rclpy.node import Node
from sensor_msgs.msg import JointState, Imu, BatteryState, Image, PointCloud2
from std_msgs.msg import Header

from PySide6.QtCore import QObject, Signal

from g1_dashboard.config.ros_config import Topics, SENSOR_QOS, RELIABLE_QOS
from g1_dashboard.utils.selection import SelectionState
from g1_dashboard.utils.commanded_state import CommandedState


class DashboardSignals(QObject):
    """Qt signals emitted from ROS2 callbacks for thread-safe GUI updates.

    All signals carry the raw ROS message as their argument.
    Connections are made in the panel constructors (main thread).
    Emissions happen on the rclpy spin thread.
    Qt's signal/slot mechanism handles the cross-thread delivery.
    """
    joint_states_received = Signal(object)
    imu_received = Signal(object)
    battery_received = Signal(object)
    robot_state_received = Signal(object)
    safety_received = Signal(object)
    camera_received = Signal(object)
    pointcloud_received = Signal(object)
    connection_changed = Signal(bool)


class DashboardNode(Node):
    """ROS2 node that bridges ROS topics to Qt signals."""

    def __init__(self):
        super().__init__('g1_dashboard')
        self.signals = DashboardSignals()
        self.selection = SelectionState()
        self.commanded = CommandedState()
        self._topic_last_received: dict[str, float] = {}

        # --- Subscriptions ---

        self.joint_states_sub = self.create_subscription(
            JointState,
            Topics.JOINT_STATES,
            self._on_joint_states,
            qos_profile=SENSOR_QOS,
        )

        self.imu_sub = self.create_subscription(
            Imu,
            Topics.IMU,
            self._on_imu,
            qos_profile=SENSOR_QOS,
        )

        self.battery_sub = self.create_subscription(
            BatteryState,
            Topics.BATTERY,
            self._on_battery,
            qos_profile=SENSOR_QOS,
        )

        self.camera_sub = self.create_subscription(
            Image,
            Topics.CAMERA_IMAGE,
            self._on_camera,
            qos_profile=SENSOR_QOS,
        )

        self.pointcloud_sub = self.create_subscription(
            PointCloud2,
            Topics.LIDAR_POINTS,
            self._on_pointcloud,
            qos_profile=SENSOR_QOS,
        )

        # Custom message subscriptions — gracefully skip if package not built yet
        self.robot_state_sub = None
        self.safety_sub = None
        try:
            from g1_dashboard_msgs.msg import RobotState, SafetyStatus
            self.robot_state_sub = self.create_subscription(
                RobotState, Topics.ROBOT_STATE,
                self._on_robot_state, qos_profile=RELIABLE_QOS)
            self.safety_sub = self.create_subscription(
                SafetyStatus, Topics.SAFETY_STATUS,
                self._on_safety, qos_profile=RELIABLE_QOS)
        except ImportError:
            self.get_logger().warn(
                'g1_dashboard_msgs not available — RobotState/SafetyStatus disabled')

        # --- Publishers ---

        self.heartbeat_pub = self.create_publisher(
            Header,
            Topics.HEARTBEAT,
            qos_profile=RELIABLE_QOS,
        )

        # Heartbeat timer at 10 Hz
        self.heartbeat_timer = self.create_timer(0.1, self._publish_heartbeat)

        # Joint command publisher + E-stop service client are lazy-inited
        # on first use so startup doesn't hard-require g1_dashboard_msgs.
        self._joint_cmd_pub = None
        self._estop_client = None

        self.get_logger().info('G1 Dashboard node initialized')

    # --- Callbacks (run on spin thread) ---

    def _on_joint_states(self, msg: JointState) -> None:
        self._topic_last_received[Topics.JOINT_STATES] = time.time()
        self.signals.joint_states_received.emit(msg)

    def _on_imu(self, msg: Imu) -> None:
        self._topic_last_received[Topics.IMU] = time.time()
        self.signals.imu_received.emit(msg)

    def _on_battery(self, msg: BatteryState) -> None:
        self._topic_last_received[Topics.BATTERY] = time.time()
        self.signals.battery_received.emit(msg)

    def _on_camera(self, msg: Image) -> None:
        self._topic_last_received[Topics.CAMERA_IMAGE] = time.time()
        self.signals.camera_received.emit(msg)

    def _on_pointcloud(self, msg: PointCloud2) -> None:
        self._topic_last_received[Topics.LIDAR_POINTS] = time.time()
        self.signals.pointcloud_received.emit(msg)

    def _on_robot_state(self, msg) -> None:
        self._topic_last_received[Topics.ROBOT_STATE] = time.time()
        self.signals.robot_state_received.emit(msg)

    def _on_safety(self, msg) -> None:
        self._topic_last_received[Topics.SAFETY_STATUS] = time.time()
        self.signals.safety_received.emit(msg)

    def _publish_heartbeat(self) -> None:
        msg = Header()
        msg.stamp = self.get_clock().now().to_msg()
        msg.frame_id = 'g1_dashboard'
        self.heartbeat_pub.publish(msg)

    # --- Public API (called from GUI thread) ---

    def get_topic_age(self, topic: str) -> float | None:
        """Return seconds since last message on a topic, or None if never received."""
        last = self._topic_last_received.get(topic)
        if last is None:
            return None
        return time.time() - last

    def get_active_topics(self) -> dict[str, float]:
        """Return dict of topic -> seconds since last message."""
        now = time.time()
        return {t: now - ts for t, ts in self._topic_last_received.items()}

    def publish_joint_commands(self, commands: list) -> int:
        """Publish a list of JointCommand messages. Returns count published."""
        if not commands:
            return 0
        if self._joint_cmd_pub is None:
            try:
                from g1_dashboard_msgs.msg import JointCommand  # noqa: F401
            except ImportError:
                self.get_logger().error(
                    'Cannot publish joint commands: g1_dashboard_msgs not available')
                return 0
            self._joint_cmd_pub = self.create_publisher(
                JointCommand, Topics.JOINT_COMMANDS, qos_profile=RELIABLE_QOS)
        for cmd in commands:
            self._joint_cmd_pub.publish(cmd)
        return len(commands)

    def trigger_estop(self, activate: bool = True, timeout: float = 1.0) -> bool | None:
        """Call EmergencyStop service. Returns None if unreachable, else success bool.

        Non-blocking from the caller's perspective: uses call_async; we spin
        briefly here because this is invoked from the GUI thread and the
        rclpy spin thread will dispatch the response. The timeout caps how
        long we wait for the service to be discovered.
        """
        try:
            from g1_dashboard_msgs.srv import EmergencyStop
        except ImportError:
            self.get_logger().error('EmergencyStop srv unavailable')
            return None

        if self._estop_client is None:
            self._estop_client = self.create_client(EmergencyStop, '/emergency_stop')

        if not self._estop_client.wait_for_service(timeout_sec=timeout):
            self.get_logger().warn('EmergencyStop service not available')
            return None

        req = EmergencyStop.Request()
        req.activate = activate
        future = self._estop_client.call_async(req)
        # Spin thread handles the callback; fire-and-forget from GUI perspective.
        # Caller can log or poll `future.done()` if they need the result.
        future.add_done_callback(
            lambda f: self.get_logger().info(
                f'E-stop response: success={f.result().success} msg={f.result().message}'
                if f.result() is not None else 'E-stop call failed'))
        return True
