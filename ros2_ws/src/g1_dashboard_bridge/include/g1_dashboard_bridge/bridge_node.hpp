#ifndef G1_DASHBOARD_BRIDGE__BRIDGE_NODE_HPP_
#define G1_DASHBOARD_BRIDGE__BRIDGE_NODE_HPP_

#include <atomic>
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
#include "g1_dashboard_bridge/lowcmd_builder.hpp"

#ifdef USE_UNITREE_HG
#include "unitree_hg/msg/low_cmd.hpp"
#include "unitree_hg/msg/low_state.hpp"
#include "unitree_hg/msg/bms_state.hpp"
#endif

namespace g1_dashboard_bridge
{

/// Translates Unitree-native DDS messages to standard ROS2 sensor_msgs and
/// forwards validated JointCommand messages back to the robot as LowCmd.
///
/// When compiled with -DUSE_UNITREE_HG=ON the node:
///   - subscribes to rt/lowstate (LowState at 500 Hz) and republishes as
///     sensor_msgs/JointState (29 motors) + sensor_msgs/Imu + RobotState
///     at the configured downsampled rates;
///   - subscribes to rt/bms_state and republishes as sensor_msgs/BatteryState;
///   - drives a 500 Hz timer that builds a complete LowCmd from LowCmdBuilder
///     and publishes it on rt/lowcmd with CRC.
///
/// Without USE_UNITREE_HG the node still validates JointCommands and updates
/// the LowCmdBuilder's internal state — useful for development and tests.
class BridgeNode : public rclcpp::Node
{
public:
  BridgeNode();

private:
  void load_parameters();

  // Dashboard-facing publishers
  rclcpp::Publisher<g1_dashboard_msgs::msg::SafetyStatus>::SharedPtr safety_pub_;
  rclcpp::Publisher<sensor_msgs::msg::JointState>::SharedPtr joint_state_pub_;
  rclcpp::Publisher<sensor_msgs::msg::Imu>::SharedPtr imu_pub_;
  rclcpp::Publisher<sensor_msgs::msg::BatteryState>::SharedPtr battery_pub_;
  rclcpp::Publisher<g1_dashboard_msgs::msg::RobotState>::SharedPtr robot_state_pub_;

  // Dashboard-facing subscribers
  rclcpp::Subscription<g1_dashboard_msgs::msg::JointCommand>::SharedPtr cmd_sub_;
  rclcpp::Subscription<std_msgs::msg::Header>::SharedPtr heartbeat_sub_;

#ifdef USE_UNITREE_HG
  // Robot-facing pub/sub
  rclcpp::Publisher<unitree_hg::msg::LowCmd>::SharedPtr lowcmd_pub_;
  rclcpp::Subscription<unitree_hg::msg::LowState>::SharedPtr lowstate_sub_;
  rclcpp::Subscription<unitree_hg::msg::BmsState>::SharedPtr bms_sub_;
#endif

  // E-Stop service
  rclcpp::Service<g1_dashboard_msgs::srv::EmergencyStop>::SharedPtr estop_srv_;

  // Timers
  rclcpp::TimerBase::SharedPtr safety_timer_;
  rclcpp::TimerBase::SharedPtr lowcmd_timer_;

  // State
  SafetyMonitor safety_;
  LowCmdBuilder builder_;

  std::string robot_variant_ {"29dof"};
  std::string lowcmd_topic_ {"lowcmd"};
  std::string lowstate_topic_ {"lowstate"};
  std::string bms_topic_ {"bms_state"};
  double joint_rate_hz_ {50.0};
  double imu_rate_hz_ {50.0};
  double battery_rate_hz_ {1.0};
  double command_max_rate_hz_ {50.0};
  double heartbeat_timeout_s_ {0.5};
  double damping_kd_ {0.5};
  double lowcmd_publish_rate_hz_ {500.0};
  bool enforce_limits_ {true};

  // Mode echoed back from latest LowState — required by firmware in LowCmd.
  std::atomic<uint8_t> mode_machine_ {0};

  // Downsample counters for telemetry.
  uint32_t joint_state_skip_ {0};
  uint32_t imu_skip_ {0};
  uint32_t lowstate_count_ {0};

  // Handlers
  void on_joint_command(const g1_dashboard_msgs::msg::JointCommand::SharedPtr cmd);
  void on_heartbeat(const std_msgs::msg::Header::SharedPtr msg);
  void on_estop(
    const std::shared_ptr<g1_dashboard_msgs::srv::EmergencyStop::Request> req,
    std::shared_ptr<g1_dashboard_msgs::srv::EmergencyStop::Response> res);
  void publish_safety_status();
  void publish_lowcmd_tick();

#ifdef USE_UNITREE_HG
  void on_lowstate(const unitree_hg::msg::LowState::SharedPtr msg);
  void on_bms_state(const unitree_hg::msg::BmsState::SharedPtr msg);
#endif
};

}  // namespace g1_dashboard_bridge

#endif  // G1_DASHBOARD_BRIDGE__BRIDGE_NODE_HPP_
