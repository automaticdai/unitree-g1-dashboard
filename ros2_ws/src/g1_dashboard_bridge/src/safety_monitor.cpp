#include "g1_dashboard_bridge/safety_monitor.hpp"

#include <cmath>

#include "g1_dashboard_bridge/g1_joint_config.hpp"

namespace g1_dashboard_bridge
{

bool SafetyMonitor::validate(
  g1_dashboard_msgs::msg::JointCommand & cmd,
  std::string & reason)
{
  // Joint index bounds
  if (cmd.joint_index >= NUM_JOINTS) {
    reason = "joint_index out of range";
    increment_rejected();
    return false;
  }

  // NaN / Inf check
  const auto bad = [](double v) { return std::isnan(v) || std::isinf(v); };
  if (bad(cmd.target_position) || bad(cmd.target_velocity) ||
      bad(cmd.kp) || bad(cmd.kd) || bad(cmd.feedforward_torque))
  {
    reason = "command contains NaN or Inf";
    increment_rejected();
    return false;
  }

  // Forwarding gate
  if (!command_forwarding_.load()) {
    reason = "command forwarding disabled";
    increment_rejected();
    return false;
  }
  if (estop_active_.load()) {
    reason = "e-stop active";
    increment_rejected();
    return false;
  }

  // Heartbeat gate
  if (!heartbeat_ok()) {
    reason = "dashboard heartbeat lost";
    increment_rejected();
    return false;
  }

  // Rate limit
  const auto now = std::chrono::steady_clock::now();
  if (command_min_dt_s_ > 0.0) {
    const auto dt = std::chrono::duration<double>(now - last_command_).count();
    if (dt < command_min_dt_s_) {
      reason = "command rate limit exceeded";
      increment_rejected();
      return false;
    }
  }
  last_command_ = now;

  // Joint limit clipping
  if (enforce_limits_) {
    const auto clipped = clamp_to_limits(cmd.joint_index, cmd.target_position);
    if (clipped != cmd.target_position) {
      cmd.target_position = clipped;
      // Note: not rejected — we clip silently but could increment a
      // "commands_clipped" counter for telemetry.
    }
  }

  reason.clear();
  return true;
}

}  // namespace g1_dashboard_bridge
