"""Simulator node — publishes fake robot telemetry for hardware-free testing.

Mimics what g1_dashboard_bridge will produce once it's running against the
real robot. Useful for developing and testing the dashboard GUI without
needing a physical G1 or the proprietary unitree_hg SDK.

Topics published:
    /joint_states      sensor_msgs/JointState     (50 Hz)
    /imu/data          sensor_msgs/Imu            (50 Hz)
    /battery_state     sensor_msgs/BatteryState   (1 Hz)
    /robot_state       g1_dashboard_msgs/RobotState   (10 Hz)
    /safety_status     g1_dashboard_msgs/SafetyStatus (10 Hz)
"""

import math
import random
import sys
import time

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import JointState, Imu, BatteryState
from std_msgs.msg import Header

from g1_dashboard.config.robot_config import JOINTS
from g1_dashboard.config.ros_config import Topics, SENSOR_QOS, RELIABLE_QOS


class SimulatorNode(Node):
    """Publishes synthetic robot telemetry on dashboard-facing topics."""

    def __init__(self):
        super().__init__('g1_simulator')

        # Publishers
        self.joint_pub = self.create_publisher(
            JointState, Topics.JOINT_STATES, qos_profile=SENSOR_QOS)
        self.imu_pub = self.create_publisher(
            Imu, Topics.IMU, qos_profile=SENSOR_QOS)
        self.battery_pub = self.create_publisher(
            BatteryState, Topics.BATTERY, qos_profile=SENSOR_QOS)

        # Optional custom messages (may not be available if g1_dashboard_msgs
        # isn't built yet; fall back gracefully)
        self.robot_state_pub = None
        self.safety_pub = None
        try:
            from g1_dashboard_msgs.msg import RobotState, SafetyStatus
            self._RobotState = RobotState
            self._SafetyStatus = SafetyStatus
            self.robot_state_pub = self.create_publisher(
                RobotState, Topics.ROBOT_STATE, qos_profile=RELIABLE_QOS)
            self.safety_pub = self.create_publisher(
                SafetyStatus, Topics.SAFETY_STATUS, qos_profile=RELIABLE_QOS)
            self.get_logger().info('Publishing custom robot/safety state')
        except ImportError:
            self.get_logger().warn(
                'g1_dashboard_msgs not available — skipping RobotState/SafetyStatus')

        # Timers
        self.create_timer(0.02, self._tick_fast)   # 50 Hz — joints + IMU
        self.create_timer(1.0, self._tick_battery)  # 1 Hz — battery
        self.create_timer(0.1, self._tick_state)    # 10 Hz — robot/safety state

        self._t0 = time.time()
        self._battery_pct = 92.0

        self.get_logger().info('G1 Simulator running')

    def _elapsed(self) -> float:
        return time.time() - self._t0

    def _tick_fast(self) -> None:
        t = self._elapsed()
        self._publish_joint_states(t)
        self._publish_imu(t)

    def _publish_joint_states(self, t: float) -> None:
        msg = JointState()
        msg.header = Header()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_link'

        msg.name = [j.name for j in JOINTS]
        # Each joint oscillates within 40% of its range at its own phase
        positions = []
        velocities = []
        efforts = []
        for j in JOINTS:
            center = 0.5 * (j.lower + j.upper)
            amp = 0.4 * 0.5 * (j.upper - j.lower)
            phase = 0.3 * j.index
            pos = center + amp * math.sin(0.5 * t + phase)
            vel = amp * 0.5 * math.cos(0.5 * t + phase)
            eff = 0.5 * math.sin(0.7 * t + phase)
            positions.append(pos)
            velocities.append(vel)
            efforts.append(eff)
        msg.position = positions
        msg.velocity = velocities
        msg.effort = efforts

        self.joint_pub.publish(msg)

    def _publish_imu(self, t: float) -> None:
        msg = Imu()
        msg.header = Header()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'imu_link'

        # Slow roll/pitch/yaw oscillation -> quaternion
        roll = 0.15 * math.sin(0.4 * t)
        pitch = 0.10 * math.sin(0.6 * t + 1.0)
        yaw = 0.20 * math.sin(0.2 * t)
        qx, qy, qz, qw = _euler_to_quaternion(roll, pitch, yaw)
        msg.orientation.x = qx
        msg.orientation.y = qy
        msg.orientation.z = qz
        msg.orientation.w = qw

        # Angular velocity: derivative-ish of roll/pitch/yaw
        msg.angular_velocity.x = 0.06 * math.cos(0.4 * t)
        msg.angular_velocity.y = 0.06 * math.cos(0.6 * t + 1.0)
        msg.angular_velocity.z = 0.04 * math.cos(0.2 * t)

        # Linear acceleration: gravity + small noise
        msg.linear_acceleration.x = 0.05 * math.sin(1.5 * t) + random.uniform(-0.02, 0.02)
        msg.linear_acceleration.y = 0.05 * math.cos(1.5 * t) + random.uniform(-0.02, 0.02)
        msg.linear_acceleration.z = 9.81 + random.uniform(-0.05, 0.05)

        self.imu_pub.publish(msg)

    def _tick_battery(self) -> None:
        # Slow discharge
        self._battery_pct = max(5.0, self._battery_pct - 0.05)

        msg = BatteryState()
        msg.header = Header()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.percentage = self._battery_pct / 100.0   # ROS convention: 0.0-1.0
        msg.voltage = 48.0 + 4.0 * (self._battery_pct / 100.0)
        msg.current = -8.5 + random.uniform(-0.5, 0.5)
        msg.charge = 10.0 * (self._battery_pct / 100.0)
        msg.capacity = 10.0
        msg.design_capacity = 10.0
        msg.temperature = 28.0 + random.uniform(-1.0, 2.0)
        msg.present = True
        self.battery_pub.publish(msg)

    def _tick_state(self) -> None:
        if self.robot_state_pub is not None:
            msg = self._RobotState()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.mode = 4  # lowlevel
            msg.mode_name = 'Low-Level Control'
            msg.error_codes = []
            # 29 motor temperatures oscillating around 40-55 C
            t = self._elapsed()
            msg.motor_temperatures = [
                40.0 + 8.0 * (0.5 + 0.5 * math.sin(0.3 * t + 0.2 * i))
                for i in range(29)
            ]
            # 4 foot force sensors (alternating gait)
            msg.foot_forces = [
                max(0.0, 200.0 * math.sin(2.0 * t)),
                max(0.0, 200.0 * math.sin(2.0 * t + math.pi)),
                max(0.0, 200.0 * math.sin(2.0 * t + math.pi)),
                max(0.0, 200.0 * math.sin(2.0 * t)),
            ]
            self.robot_state_pub.publish(msg)

        if self.safety_pub is not None:
            msg = self._SafetyStatus()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.limits_active = True
            msg.estop_active = False
            msg.command_forwarding_enabled = True
            msg.heartbeat_ok = True
            msg.heartbeat_age = 0.05
            msg.commands_rejected = 0
            self.safety_pub.publish(msg)


def _euler_to_quaternion(roll: float, pitch: float, yaw: float):
    cr, sr = math.cos(roll * 0.5), math.sin(roll * 0.5)
    cp, sp = math.cos(pitch * 0.5), math.sin(pitch * 0.5)
    cy, sy = math.cos(yaw * 0.5), math.sin(yaw * 0.5)
    qw = cr * cp * cy + sr * sp * sy
    qx = sr * cp * cy - cr * sp * sy
    qy = cr * sp * cy + sr * cp * sy
    qz = cr * cp * sy - sr * sp * cy
    return qx, qy, qz, qw


def main():
    rclpy.init(args=sys.argv)
    node = SimulatorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
