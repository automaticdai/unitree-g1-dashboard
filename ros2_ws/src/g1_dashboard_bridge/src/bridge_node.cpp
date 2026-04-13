#include "g1_dashboard_bridge/bridge_node.hpp"

#include <memory>
#include <string>

#include "rclcpp/rclcpp.hpp"

namespace g1_dashboard_bridge
{

BridgeNode::BridgeNode()
: Node("g1_dashboard_bridge")
{
  load_parameters();

  // Publishers
  safety_pub_ = create_publisher<g1_dashboard_msgs::msg::SafetyStatus>(
    "/safety_status", rclcpp::QoS(10).reliable());

  // Subscribers
  cmd_sub_ = create_subscription<g1_dashboard_msgs::msg::JointCommand>(
    "/joint_commands",
    rclcpp::QoS(10).reliable(),
    std::bind(&BridgeNode::on_joint_command, this, std::placeholders::_1));

  heartbeat_sub_ = create_subscription<std_msgs::msg::Header>(
    "/dashboard_heartbeat",
    rclcpp::QoS(10).reliable(),
    std::bind(&BridgeNode::on_heartbeat, this, std::placeholders::_1));

  // E-Stop service
  estop_srv_ = create_service<g1_dashboard_msgs::srv::EmergencyStop>(
    "/emergency_stop",
    std::bind(&BridgeNode::on_estop, this,
              std::placeholders::_1, std::placeholders::_2));

  // 10 Hz safety status publication
  safety_timer_ = create_wall_timer(
    std::chrono::milliseconds(100),
    std::bind(&BridgeNode::publish_safety_status, this));

#ifndef USE_UNITREE_HG
  RCLCPP_WARN(get_logger(),
    "Bridge compiled WITHOUT unitree_hg support (-DUSE_UNITREE_HG=ON). "
    "Commands are validated and logged but NOT forwarded to the robot. "
    "Use this mode for dashboard development only.");
#endif

  RCLCPP_INFO(get_logger(),
    "g1_dashboard_bridge ready (variant=%s, max_cmd_rate=%.1f Hz, heartbeat_timeout=%.2fs)",
    robot_variant_.c_str(), command_max_rate_hz_, heartbeat_timeout_s_);
}

void BridgeNode::load_parameters()
{
  robot_variant_ = declare_parameter<std::string>("robot_variant", "29dof");
  joint_rate_hz_ = declare_parameter<double>("joint_state_publish_rate", 50.0);
  command_max_rate_hz_ = declare_parameter<double>("command_max_rate", 50.0);
  heartbeat_timeout_s_ = declare_parameter<double>("heartbeat_timeout", 0.5);
  enforce_limits_ = declare_parameter<bool>("enforce_joint_limits", true);
  const bool forwarding = declare_parameter<bool>("enable_command_forwarding", true);

  safety_.set_heartbeat_timeout(heartbeat_timeout_s_);
  safety_.set_command_rate_limit(command_max_rate_hz_);
  safety_.set_limits_enforcement(enforce_limits_);
  safety_.set_command_forwarding(forwarding);
}

void BridgeNode::on_joint_command(
  const g1_dashboard_msgs::msg::JointCommand::SharedPtr cmd)
{
  std::string reason;
  auto validated = *cmd;
  if (!safety_.validate(validated, reason)) {
    RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 1000,
      "Rejected JointCommand(idx=%u): %s",
      static_cast<unsigned>(cmd->joint_index), reason.c_str());
    return;
  }

#ifdef USE_UNITREE_HG
  // TODO: Convert `validated` to unitree_hg::msg::LowCmd and publish on
  // rt/lowcmd. Requires:
  //   - Maintaining a running LowCmd struct with all 29 motor entries
  //   - Updating the entry at validated.joint_index with position, velocity,
  //     kp, kd, tau fields
  //   - Computing CRC via motor_crc_hg.cpp from unitree_ros2
  //   - Publishing the full LowCmd at a fixed rate (e.g., 500 Hz)
  //
  // The stub below will be filled in when the Unitree SDK is integrated.
#else
  RCLCPP_DEBUG(get_logger(),
    "JointCommand validated (idx=%u, pos=%.3f, kp=%.1f, kd=%.2f) "
    "— forwarding skipped (unitree_hg not compiled in)",
    static_cast<unsigned>(validated.joint_index),
    validated.target_position, validated.kp, validated.kd);
#endif
}

void BridgeNode::on_heartbeat(const std_msgs::msg::Header::SharedPtr /*msg*/)
{
  safety_.notify_heartbeat();
}

void BridgeNode::on_estop(
  const std::shared_ptr<g1_dashboard_msgs::srv::EmergencyStop::Request> req,
  std::shared_ptr<g1_dashboard_msgs::srv::EmergencyStop::Response> res)
{
  safety_.set_estop(req->activate);
  res->success = true;
  res->message = req->activate ? "E-Stop engaged" : "E-Stop released";
  RCLCPP_WARN(get_logger(), "%s", res->message.c_str());
}

void BridgeNode::publish_safety_status()
{
  g1_dashboard_msgs::msg::SafetyStatus msg;
  msg.header.stamp = now();
  msg.limits_active = enforce_limits_;
  msg.estop_active = safety_.estop_active();
  msg.command_forwarding_enabled = safety_.command_forwarding_enabled();
  msg.heartbeat_ok = safety_.heartbeat_ok();
  const double age = safety_.heartbeat_age_s();
  msg.heartbeat_age = std::isfinite(age) ? static_cast<float>(age) : 999.0f;
  msg.commands_rejected = safety_.commands_rejected();
  safety_pub_->publish(msg);
}

}  // namespace g1_dashboard_bridge

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<g1_dashboard_bridge::BridgeNode>());
  rclcpp::shutdown();
  return 0;
}
