#include "g1_dashboard_bridge/lowcmd_builder.hpp"

#include <algorithm>
#include <cmath>

#ifdef USE_UNITREE_HG
#include "g1_dashboard_bridge/vendor/motor_crc_hg.h"
#endif

namespace g1_dashboard_bridge
{

namespace
{
// Conservative defaults: legs/waist 2 rad/s, shoulders/elbows 4 rad/s,
// wrists 6 rad/s. Lighter, lower-inertia joints can move faster safely.
constexpr double slew_default(uint8_t i)
{
  if (i <= 14) {
    return 2.0;  // legs (0-11), waist (12-14)
  }
  if ((i >= 19 && i <= 21) || (i >= 26 && i <= 28)) {
    return 6.0;  // wrists
  }
  return 4.0;    // shoulders, elbows
}
}  // namespace

LowCmdBuilder::LowCmdBuilder()
{
  for (size_t i = 0; i < NUM_JOINTS; ++i) {
    motors_[i].slew_rate = slew_default(static_cast<uint8_t>(i));
  }
}

void LowCmdBuilder::set_slew_rate(uint8_t idx, double rate)
{
  if (idx >= NUM_JOINTS) {
    return;
  }
  std::lock_guard<std::mutex> lock(mu_);
  motors_[idx].slew_rate = std::max(0.01, rate);
}

void LowCmdBuilder::set_measured_position(uint8_t idx, double q)
{
  if (idx >= NUM_JOINTS) {
    return;
  }
  std::lock_guard<std::mutex> lock(mu_);
  motors_[idx].measured_q = q;
  motors_[idx].measured_valid = true;
}

void LowCmdBuilder::update_command(uint8_t idx, double target_q,
                                   double kp, double kd, double tau)
{
  if (idx >= NUM_JOINTS) {
    return;
  }
  std::lock_guard<std::mutex> lock(mu_);
  auto & m = motors_[idx];
  if (!m.active) {
    // First command for this motor: seed from measured position so the
    // first slew step starts at the truth, not at zero.
    m.current_q = m.measured_valid ? m.measured_q : target_q;
    m.active = true;
  }
  m.target_q = target_q;
  m.kp = kp;
  m.kd = kd;
  m.tau = tau;
}

void LowCmdBuilder::step(double dt, bool estop_active)
{
  std::lock_guard<std::mutex> lock(mu_);

  // Re-seed integrator from measured position on estop release: motors went
  // limp during damping so commanded current_q drifted from physical reality.
  if (prev_estop_ && !estop_active) {
    for (auto & m : motors_) {
      if (m.active && m.measured_valid) {
        m.current_q = m.measured_q;
      }
    }
  }
  prev_estop_ = estop_active;

  for (auto & m : motors_) {
    if (!m.active) {
      continue;
    }
    if (estop_active) {
      // Damping mode: track measured position so when estop releases there
      // is no transient. write_lowcmd sets kp=0/kd=damping_kd separately.
      if (m.measured_valid) {
        m.current_q = m.measured_q;
      }
      continue;
    }
    const double max_step = m.slew_rate * dt;
    const double err = m.target_q - m.current_q;
    if (std::abs(err) <= max_step) {
      m.current_q = m.target_q;
    } else {
      m.current_q += (err > 0 ? max_step : -max_step);
    }
  }
}

#ifdef USE_UNITREE_HG
void LowCmdBuilder::write_lowcmd(unitree_hg::msg::LowCmd & msg) const
{
  std::lock_guard<std::mutex> lock(mu_);

  // Zero unused slots (G1 uses 0..28; slots 29..34 are reserved/hands).
  for (size_t i = 0; i < LOWCMD_MOTOR_SLOTS; ++i) {
    msg.motor_cmd[i].mode = 0;
    msg.motor_cmd[i].q = 0.0f;
    msg.motor_cmd[i].dq = 0.0f;
    msg.motor_cmd[i].tau = 0.0f;
    msg.motor_cmd[i].kp = 0.0f;
    msg.motor_cmd[i].kd = 0.0f;
    msg.motor_cmd[i].reserve = 0;
  }

  for (size_t i = 0; i < NUM_JOINTS; ++i) {
    const auto & m = motors_[i];
    if (!m.active) {
      continue;
    }
    msg.motor_cmd[i].mode = 1;
    msg.motor_cmd[i].q = static_cast<float>(m.current_q);
    msg.motor_cmd[i].dq = 0.0f;
    if (prev_estop_) {
      msg.motor_cmd[i].kp = 0.0f;
      msg.motor_cmd[i].kd = static_cast<float>(damping_kd_);
      msg.motor_cmd[i].tau = 0.0f;
    } else {
      msg.motor_cmd[i].kp = static_cast<float>(m.kp);
      msg.motor_cmd[i].kd = static_cast<float>(m.kd);
      msg.motor_cmd[i].tau = static_cast<float>(m.tau);
    }
  }

  get_crc(msg);
}
#endif

bool LowCmdBuilder::is_active(uint8_t idx) const
{
  if (idx >= NUM_JOINTS) {
    return false;
  }
  std::lock_guard<std::mutex> lock(mu_);
  return motors_[idx].active;
}

bool LowCmdBuilder::estop_active() const
{
  std::lock_guard<std::mutex> lock(mu_);
  return prev_estop_;
}

double LowCmdBuilder::commanded_q(uint8_t idx) const
{
  if (idx >= NUM_JOINTS) {
    return 0.0;
  }
  std::lock_guard<std::mutex> lock(mu_);
  return motors_[idx].current_q;
}

double LowCmdBuilder::target_q(uint8_t idx) const
{
  if (idx >= NUM_JOINTS) {
    return 0.0;
  }
  std::lock_guard<std::mutex> lock(mu_);
  return motors_[idx].target_q;
}

double LowCmdBuilder::commanded_kp(uint8_t idx) const
{
  if (idx >= NUM_JOINTS) {
    return 0.0;
  }
  std::lock_guard<std::mutex> lock(mu_);
  return motors_[idx].kp;
}

double LowCmdBuilder::commanded_kd(uint8_t idx) const
{
  if (idx >= NUM_JOINTS) {
    return 0.0;
  }
  std::lock_guard<std::mutex> lock(mu_);
  return motors_[idx].kd;
}

void LowCmdBuilder::reset()
{
  std::lock_guard<std::mutex> lock(mu_);
  for (auto & m : motors_) {
    m.active = false;
    m.current_q = 0.0;
    m.target_q = 0.0;
    m.kp = 0.0;
    m.kd = 0.0;
    m.tau = 0.0;
    m.measured_valid = false;
  }
  prev_estop_ = false;
}

}  // namespace g1_dashboard_bridge
