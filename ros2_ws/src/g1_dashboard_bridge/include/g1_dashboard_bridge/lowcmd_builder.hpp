#ifndef G1_DASHBOARD_BRIDGE__LOWCMD_BUILDER_HPP_
#define G1_DASHBOARD_BRIDGE__LOWCMD_BUILDER_HPP_

#include <array>
#include <cstdint>
#include <mutex>

#include "g1_dashboard_bridge/g1_joint_config.hpp"

#ifdef USE_UNITREE_HG
#include "unitree_hg/msg/low_cmd.hpp"
#endif

namespace g1_dashboard_bridge
{

/// Maintains the running per-motor commanded state for a Unitree G1 and
/// produces a complete LowCmd message at every control tick (500 Hz).
///
/// Single-motor JointCommand messages from the dashboard update the *target*
/// for one motor; on every tick step() advances the integrated commanded
/// position toward target by at most slew_rate * dt so step inputs from
/// sliders never reach the firmware as instantaneous jumps.
///
/// On E-Stop the builder switches to damping mode (kp = 0, kd = damping_kd,
/// q = current measured position, tau = 0). When E-Stop releases, the
/// integrator is re-seeded from the latest measured position so it resumes
/// from where the robot actually is — motors went limp during damping, so
/// pre-estop commanded positions are stale.
class LowCmdBuilder
{
public:
  /// Number of motor slots in unitree_hg::LowCmd (35 — 29 active for G1).
  static constexpr size_t LOWCMD_MOTOR_SLOTS = 35;

  LowCmdBuilder();

  /// Configure per-joint slew rate (rad/s). Defaults are conservative:
  /// 2.0 for legs/waist, 4.0 for shoulders/elbows, 6.0 for wrists.
  void set_slew_rate(uint8_t joint_index, double rate_rad_s);

  /// kd applied to all active motors when E-Stop is engaged.
  void set_damping_kd(double kd) { damping_kd_ = kd; }

  /// Latest *measured* joint position (from LowState). Used to seed the
  /// integrator on first command and to re-seed on E-Stop release.
  void set_measured_position(uint8_t joint_index, double q);

  /// Apply a validated JointCommand. Activates the motor on first call.
  /// Caller must run SafetyMonitor::validate() first — this method does
  /// no clipping or rate limiting.
  void update_command(uint8_t joint_index, double target_q,
                      double kp, double kd, double tau);

  /// Advance the integrator by dt seconds. Call at the LowCmd publish rate.
  /// estop_active flips the output to damping mode but does not clear
  /// per-motor target_q — releasing estop resumes from the last target.
  void step(double dt, bool estop_active);

#ifdef USE_UNITREE_HG
  /// Fill out a LowCmd message and compute its CRC. mode_pr / mode_machine
  /// must be set by the caller (they come from LowState).
  void write_lowcmd(unitree_hg::msg::LowCmd & msg) const;
#endif

  // Accessors used by tests and telemetry.
  bool is_active(uint8_t idx) const;
  bool estop_active() const;
  double commanded_q(uint8_t idx) const;
  double target_q(uint8_t idx) const;
  double commanded_kp(uint8_t idx) const;
  double commanded_kd(uint8_t idx) const;

  void reset();

private:
  struct MotorEntry
  {
    bool active = false;
    double target_q = 0.0;
    double current_q = 0.0;       // integrator state, slewed toward target_q
    double kp = 0.0;
    double kd = 0.0;
    double tau = 0.0;
    double slew_rate = 2.0;
    double measured_q = 0.0;
    bool measured_valid = false;
  };

  mutable std::mutex mu_;
  std::array<MotorEntry, NUM_JOINTS> motors_;
  bool prev_estop_ = false;
  double damping_kd_ = 0.5;
};

}  // namespace g1_dashboard_bridge

#endif  // G1_DASHBOARD_BRIDGE__LOWCMD_BUILDER_HPP_
