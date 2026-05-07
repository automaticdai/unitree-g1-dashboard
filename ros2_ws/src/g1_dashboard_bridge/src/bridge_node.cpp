#include "g1_dashboard_bridge/bridge_node.hpp"

#include <chrono>
#include <cmath>
#include <memory>
#include <string>
#include <vector>

#include "rclcpp/rclcpp.hpp"

namespace g1_dashboard_bridge
{

BridgeNode::BridgeNode()
: Node("g1_dashboard_bridge")
{
  load_parameters();

  // Configure builder.
  builder_.set_damping_kd(damping_kd_);

  // Dashboard-facing publishers.
  safety_pub_ = create_publisher<g1_dashboard_msgs::msg::SafetyStatus>(
    "/safety_status", rclcpp::QoS(10).reliable());
  joint_state_pub_ = create_publisher<sensor_msgs::msg::JointState>(
    "/joint_states", rclcpp::SensorDataQoS());
  imu_pub_ = create_publisher<sensor_msgs::msg::Imu>(
    "/imu/data", rclcpp::SensorDataQoS());
  battery_pub_ = create_publisher<sensor_msgs::msg::BatteryState>(
    "/battery_state", rclcpp::SensorDataQoS());
  robot_state_pub_ = create_publisher<g1_dashboard_msgs::msg::RobotState>(
    "/robot_state", rclcpp::QoS(10).reliable());

  // Dashboard-facing subscribers.
  cmd_sub_ = create_subscription<g1_dashboard_msgs::msg::JointCommand>(
    "/joint_commands",
    rclcpp::QoS(10).reliable(),
    std::bind(&BridgeNode::on_joint_command, this, std::placeholders::_1));

  heartbeat_sub_ = create_subscription<std_msgs::msg::Header>(
    "/dashboard_heartbeat",
    rclcpp::QoS(10).reliable(),
    std::bind(&BridgeNode::on_heartbeat, this, std::placeholders::_1));

  // E-Stop service.
  estop_srv_ = create_service<g1_dashboard_msgs::srv::EmergencyStop>(
    "/emergency_stop",
    std::bind(&BridgeNode::on_estop, this,
              std::placeholders::_1, std::placeholders::_2));

  // Safety status publication at 10 Hz.
  safety_timer_ = create_wall_timer(
    std::chrono::milliseconds(100),
    std::bind(&BridgeNode::publish_safety_status, this));

#ifdef USE_UNITREE_HG
  // Real-time DDS topics — best-effort, depth 1, matches Unitree firmware QoS.
  auto rt_qos = rclcpp::QoS(rclcpp::KeepLast(1)).best_effort();

  lowcmd_pub_ = create_publisher<unitree_hg::msg::LowCmd>(lowcmd_topic_, rt_qos);
  lowstate_sub_ = create_subscription<unitree_hg::msg::LowState>(
    lowstate_topic_, rt_qos,
    std::bind(&BridgeNode::on_lowstate, this, std::placeholders::_1));
  bms_sub_ = create_subscription<unitree_hg::msg::BmsState>(
    bms_topic_, rt_qos,
    std::bind(&BridgeNode::on_bms_state, this, std::placeholders::_1));

  const auto period_ns = static_cast<int64_t>(1.0e9 / lowcmd_publish_rate_hz_);
  lowcmd_timer_ = create_wall_timer(
    std::chrono::nanoseconds(period_ns),
    std::bind(&BridgeNode::publish_lowcmd_tick, this));

  RCLCPP_INFO(get_logger(),
    "Bridge with unitree_hg: lowcmd=%s @ %.0f Hz, lowstate=%s, bms=%s",
    lowcmd_topic_.c_str(), lowcmd_publish_rate_hz_,
    lowstate_topic_.c_str(), bms_topic_.c_str());
#else
  RCLCPP_WARN(get_logger(),
    "Bridge compiled WITHOUT unitree_hg support (-DUSE_UNITREE_HG=ON). "
    "Commands are validated and integrated into the LowCmdBuilder but NOT "
    "forwarded to the robot. Use this mode for dashboard development only.");
#endif

  RCLCPP_INFO(get_logger(),
    "g1_dashboard_bridge ready (variant=%s, max_cmd_rate=%.1f Hz, "
    "heartbeat_timeout=%.2fs, damping_kd=%.2f)",
    robot_variant_.c_str(), command_max_rate_hz_,
    heartbeat_timeout_s_, damping_kd_);
}

void BridgeNode::load_parameters()
{
  robot_variant_       = declare_parameter<std::string>("robot_variant", "29dof");
  joint_rate_hz_       = declare_parameter<double>("joint_state_publish_rate", 50.0);
  imu_rate_hz_         = declare_parameter<double>("imu_publish_rate", 50.0);
  battery_rate_hz_     = declare_parameter<double>("battery_publish_rate", 1.0);
  command_max_rate_hz_ = declare_parameter<double>("command_max_rate", 50.0);
  heartbeat_timeout_s_ = declare_parameter<double>("heartbeat_timeout", 0.5);
  enforce_limits_      = declare_parameter<bool>("enforce_joint_limits", true);
  damping_kd_          = declare_parameter<double>("damping_kd", 0.5);
  lowcmd_publish_rate_hz_ = declare_parameter<double>("lowcmd_publish_rate", 500.0);
  lowcmd_topic_        = declare_parameter<std::string>("lowcmd_topic", "lowcmd");
  lowstate_topic_      = declare_parameter<std::string>("lowstate_topic", "lowstate");
  bms_topic_           = declare_parameter<std::string>("bms_topic", "bms_state");
  const bool forwarding = declare_parameter<bool>("enable_command_forwarding", true);

  // Per-joint slew rate overrides (rad/s). Default is a 29-zero vector;
  // any entry > 0 overrides the builder's builtin default for that joint.
  // (rclcpp in Humble can't declare a parameter from an empty vector — it
  // can't infer the element type — so we use 0.0 as the "leave default" sentinel.)
  const auto slew_rates = declare_parameter<std::vector<double>>(
    "slew_rate_per_joint", std::vector<double>(NUM_JOINTS, 0.0));
  if (slew_rates.size() != NUM_JOINTS) {
    RCLCPP_WARN(get_logger(),
      "slew_rate_per_joint has %zu entries, expected %zu — ignoring",
      slew_rates.size(), NUM_JOINTS);
  } else {
    for (size_t i = 0; i < NUM_JOINTS; ++i) {
      if (slew_rates[i] > 0.0) {
        builder_.set_slew_rate(static_cast<uint8_t>(i), slew_rates[i]);
      }
    }
  }

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

  builder_.update_command(
    validated.joint_index,
    validated.target_position,
    validated.kp,
    validated.kd,
    validated.feedforward_torque);
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

void BridgeNode::publish_lowcmd_tick()
{
#ifdef USE_UNITREE_HG
  const double dt = 1.0 / lowcmd_publish_rate_hz_;
  builder_.step(dt, safety_.estop_active());

  // Don't publish until we've seen at least one LowState — without
  // mode_machine the firmware will refuse the command.
  if (mode_machine_.load() == 0) {
    return;
  }

  unitree_hg::msg::LowCmd msg;
  msg.mode_pr = 0;  // PR mode (matches official g1 example default)
  msg.mode_machine = mode_machine_.load();
  builder_.write_lowcmd(msg);
  lowcmd_pub_->publish(msg);
#else
  // Standalone build: still advance the integrator so dashboard testing /
  // unit tests behave the same way they would on real hardware.
  const double dt = 1.0 / lowcmd_publish_rate_hz_;
  builder_.step(dt, safety_.estop_active());
#endif
}

#ifdef USE_UNITREE_HG

void BridgeNode::on_lowstate(const unitree_hg::msg::LowState::SharedPtr msg)
{
  mode_machine_.store(msg->mode_machine);

  // Feed measured positions to the builder for slew seeding / damping mode.
  for (size_t i = 0; i < NUM_JOINTS; ++i) {
    builder_.set_measured_position(static_cast<uint8_t>(i), msg->motor_state[i].q);
  }

  ++lowstate_count_;
  const auto stamp = now();

  // Downsample to the requested telemetry rates. LowState arrives at 500 Hz.
  const uint32_t joint_div = std::max(1u,
    static_cast<uint32_t>(std::round(500.0 / joint_rate_hz_)));
  const uint32_t imu_div = std::max(1u,
    static_cast<uint32_t>(std::round(500.0 / imu_rate_hz_)));

  if ((lowstate_count_ % joint_div) == 0) {
    sensor_msgs::msg::JointState js;
    js.header.stamp = stamp;
    js.name.reserve(NUM_JOINTS);
    js.position.reserve(NUM_JOINTS);
    js.velocity.reserve(NUM_JOINTS);
    js.effort.reserve(NUM_JOINTS);
    for (size_t i = 0; i < NUM_JOINTS; ++i) {
      js.name.emplace_back(JOINT_TABLE[i].name);
      js.position.push_back(msg->motor_state[i].q);
      js.velocity.push_back(msg->motor_state[i].dq);
      js.effort.push_back(msg->motor_state[i].tau_est);
    }
    joint_state_pub_->publish(js);

    // Also publish RobotState (motor temps + mode) at the same rate.
    g1_dashboard_msgs::msg::RobotState rs;
    rs.header.stamp = stamp;
    rs.mode = 4;  // lowlevel
    rs.mode_name = std::string("lowlevel (mm=") +
                   std::to_string(msg->mode_machine) + ")";
    rs.motor_temperatures.fill(0.0f);
    for (size_t i = 0; i < NUM_JOINTS; ++i) {
      // motor_state.temperature[0] = driver, [1] = rotor — report rotor.
      rs.motor_temperatures[i] = static_cast<float>(msg->motor_state[i].temperature[1]);
    }
    rs.foot_forces.fill(0.0f);  // G1 LowState doesn't expose foot forces.
    robot_state_pub_->publish(rs);
  }

  if ((lowstate_count_ % imu_div) == 0) {
    const auto & imu_in = msg->imu_state;
    sensor_msgs::msg::Imu imu_out;
    imu_out.header.stamp = stamp;
    imu_out.header.frame_id = "imu_link";
    // unitree_hg quaternion is [w, x, y, z]; ROS convention is [x, y, z, w].
    imu_out.orientation.w = imu_in.quaternion[0];
    imu_out.orientation.x = imu_in.quaternion[1];
    imu_out.orientation.y = imu_in.quaternion[2];
    imu_out.orientation.z = imu_in.quaternion[3];
    imu_out.angular_velocity.x = imu_in.gyroscope[0];
    imu_out.angular_velocity.y = imu_in.gyroscope[1];
    imu_out.angular_velocity.z = imu_in.gyroscope[2];
    imu_out.linear_acceleration.x = imu_in.accelerometer[0];
    imu_out.linear_acceleration.y = imu_in.accelerometer[1];
    imu_out.linear_acceleration.z = imu_in.accelerometer[2];
    // Covariances unknown — leave at zero.
    imu_pub_->publish(imu_out);
  }
}

void BridgeNode::on_bms_state(const unitree_hg::msg::BmsState::SharedPtr msg)
{
  sensor_msgs::msg::BatteryState bs;
  bs.header.stamp = now();
  // bmsvoltage is mV in 3 cells; sum them for pack voltage. Field semantics
  // are not fully documented — adjust if the published value disagrees.
  uint32_t v_mv = 0;
  for (auto v : msg->bmsvoltage) { v_mv += v; }
  bs.voltage = v_mv > 0 ? static_cast<float>(v_mv) / 1000.0f : NAN;
  bs.current = static_cast<float>(msg->current) / 1000.0f;  // mA -> A
  bs.percentage = static_cast<float>(msg->soc) / 100.0f;
  bs.temperature = NAN;
  if (!msg->temperature.empty()) {
    float sum = 0.0f;
    int n = 0;
    for (auto t : msg->temperature) { sum += t; ++n; }
    if (n > 0) bs.temperature = sum / n;
  }
  bs.design_capacity = NAN;
  bs.charge = NAN;
  bs.capacity = NAN;
  bs.power_supply_status = sensor_msgs::msg::BatteryState::POWER_SUPPLY_STATUS_UNKNOWN;
  bs.power_supply_health = sensor_msgs::msg::BatteryState::POWER_SUPPLY_HEALTH_UNKNOWN;
  bs.power_supply_technology =
    sensor_msgs::msg::BatteryState::POWER_SUPPLY_TECHNOLOGY_LIPO;
  bs.present = true;
  battery_pub_->publish(bs);
}

#endif  // USE_UNITREE_HG

}  // namespace g1_dashboard_bridge

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<g1_dashboard_bridge::BridgeNode>());
  rclcpp::shutdown();
  return 0;
}
