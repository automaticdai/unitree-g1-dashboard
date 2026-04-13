#ifndef G1_DASHBOARD_BRIDGE__BRIDGE_NODE_HPP_
#define G1_DASHBOARD_BRIDGE__BRIDGE_NODE_HPP_

#include <memory>
#include <string>

#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/joint_state.hpp"
#include "sensor_msgs/msg/imu.hpp"
#include "sensor_msgs/msg/battery_state.hpp"
#include "std_msgs/msg/header.hpp"

#include "g1_dashboard_msgs/msg/joint_command.hpp"
#include "g1_dashboard_msgs/msg/robot_state.hpp"
#include "g1_dashboard_msgs/msg/safety_status.hpp"
#include "g1_dashboard_msgs/srv/emergency_stop.hpp"

#include "g1_dashboard_bridge/safety_monitor.hpp"

namespace g1_dashboard_bridge
{

/// Translates Unitree-native DDS messages to standard ROS2 sensor_msgs and
/// forwards validated JointCommand messages back to the robot as LowCmd.
///
/// When compiled with -DUSE_UNITREE_HG=ON the node subscribes to rt/lowstate
/// and publishes rt/lowcmd using unitree_hg messages. Without that flag the
/// node still publishes a valid /safety_status stream and logs any joint
/// commands it receives — useful for Phase 1/2 development without the
/// proprietary Unitree SDK.
class BridgeNode : public rclcpp::Node
{
public:
  BridgeNode();

private:
  void load_parameters();

  // Dashboard-facing publishers
  rclcpp::Publisher<g1_dashboard_msgs::msg::SafetyStatus>::SharedPtr safety_pub_;

  // Dashboard-facing subscribers
  rclcpp::Subscription<g1_dashboard_msgs::msg::JointCommand>::SharedPtr cmd_sub_;
  rclcpp::Subscription<std_msgs::msg::Header>::SharedPtr heartbeat_sub_;

  // E-Stop service
  rclcpp::Service<g1_dashboard_msgs::srv::EmergencyStop>::SharedPtr estop_srv_;

  // Timers
  rclcpp::TimerBase::SharedPtr safety_timer_;

  // State
  SafetyMonitor safety_;
  std::string robot_variant_ {"29dof"};
  double joint_rate_hz_ {50.0};
  double command_max_rate_hz_ {50.0};
  double heartbeat_timeout_s_ {0.5};
  bool enforce_limits_ {true};

  // Handlers
  void on_joint_command(const g1_dashboard_msgs::msg::JointCommand::SharedPtr cmd);
  void on_heartbeat(const std_msgs::msg::Header::SharedPtr msg);
  void on_estop(
    const std::shared_ptr<g1_dashboard_msgs::srv::EmergencyStop::Request> req,
    std::shared_ptr<g1_dashboard_msgs::srv::EmergencyStop::Response> res);
  void publish_safety_status();
};

}  // namespace g1_dashboard_bridge

#endif  // G1_DASHBOARD_BRIDGE__BRIDGE_NODE_HPP_
