#ifndef G1_DASHBOARD_BRIDGE__SAFETY_MONITOR_HPP_
#define G1_DASHBOARD_BRIDGE__SAFETY_MONITOR_HPP_

#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdint>

#include "g1_dashboard_msgs/msg/joint_command.hpp"

namespace g1_dashboard_bridge
{

/// Monitors dashboard heartbeat and validates joint commands before they
/// are forwarded to the robot firmware.
class SafetyMonitor
{
public:
  SafetyMonitor() = default;

  void set_heartbeat_timeout(double seconds) { heartbeat_timeout_s_ = seconds; }
  void set_limits_enforcement(bool enabled) { enforce_limits_ = enabled; }
  void set_command_rate_limit(double hz) { command_min_dt_s_ = hz > 0.0 ? 1.0 / hz : 0.0; }

  void notify_heartbeat()
  {
    last_heartbeat_ = std::chrono::steady_clock::now();
    heartbeat_received_ = true;
  }

  bool heartbeat_ok() const
  {
    if (!heartbeat_received_) { return false; }
    const auto age = std::chrono::duration<double>(
      std::chrono::steady_clock::now() - last_heartbeat_).count();
    return age < heartbeat_timeout_s_;
  }

  double heartbeat_age_s() const
  {
    if (!heartbeat_received_) { return std::numeric_limits<double>::infinity(); }
    return std::chrono::duration<double>(
      std::chrono::steady_clock::now() - last_heartbeat_).count();
  }

  /// Validate a joint command. Returns true if safe to forward.
  /// Modifies `cmd.target_position` in place if clipping is enabled.
  bool validate(g1_dashboard_msgs::msg::JointCommand & cmd, std::string & reason);

  uint32_t commands_rejected() const { return commands_rejected_.load(); }
  void increment_rejected() { commands_rejected_.fetch_add(1); }

  bool estop_active() const { return estop_active_.load(); }
  void set_estop(bool active) { estop_active_.store(active); }

  bool command_forwarding_enabled() const { return command_forwarding_.load(); }
  void set_command_forwarding(bool enabled) { command_forwarding_.store(enabled); }

private:
  double heartbeat_timeout_s_ {0.5};
  bool enforce_limits_ {true};
  double command_min_dt_s_ {0.02};   // 50 Hz default

  std::atomic<bool> heartbeat_received_ {false};
  std::chrono::steady_clock::time_point last_heartbeat_ {};
  std::chrono::steady_clock::time_point last_command_ {};

  std::atomic<uint32_t> commands_rejected_ {0};
  std::atomic<bool> estop_active_ {false};
  std::atomic<bool> command_forwarding_ {true};
};

}  // namespace g1_dashboard_bridge

#endif  // G1_DASHBOARD_BRIDGE__SAFETY_MONITOR_HPP_
