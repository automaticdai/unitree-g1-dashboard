#include <gtest/gtest.h>

#include <chrono>
#include <cmath>
#include <limits>
#include <thread>

#include "g1_dashboard_bridge/safety_monitor.hpp"

using g1_dashboard_bridge::SafetyMonitor;
using g1_dashboard_msgs::msg::JointCommand;

class SafetyMonitorTest : public ::testing::Test
{
protected:
  SafetyMonitor monitor;

  void SetUp() override
  {
    monitor.set_heartbeat_timeout(1.0);
    monitor.set_limits_enforcement(true);
    monitor.set_command_rate_limit(0.0);   // disabled for these tests
    monitor.set_command_forwarding(true);
    monitor.notify_heartbeat();
  }

  JointCommand make_command(uint8_t idx = 3, double pos = 1.0)
  {
    JointCommand cmd;
    cmd.joint_index = idx;
    cmd.target_position = pos;
    cmd.target_velocity = 0.0;
    cmd.kp = 150.0;
    cmd.kd = 2.0;
    cmd.feedforward_torque = 0.0;
    return cmd;
  }
};

TEST_F(SafetyMonitorTest, AcceptsValidCommand)
{
  auto cmd = make_command();
  std::string reason;
  EXPECT_TRUE(monitor.validate(cmd, reason));
  EXPECT_TRUE(reason.empty());
  EXPECT_EQ(monitor.commands_rejected(), 0u);
}

TEST_F(SafetyMonitorTest, RejectsOutOfRangeJointIndex)
{
  auto cmd = make_command(99);
  std::string reason;
  EXPECT_FALSE(monitor.validate(cmd, reason));
  EXPECT_NE(reason.find("joint_index"), std::string::npos);
  EXPECT_EQ(monitor.commands_rejected(), 1u);
}

TEST_F(SafetyMonitorTest, RejectsNaN)
{
  auto cmd = make_command();
  cmd.target_position = std::numeric_limits<double>::quiet_NaN();
  std::string reason;
  EXPECT_FALSE(monitor.validate(cmd, reason));
  EXPECT_NE(reason.find("NaN"), std::string::npos);
}

TEST_F(SafetyMonitorTest, RejectsInf)
{
  auto cmd = make_command();
  cmd.kp = std::numeric_limits<double>::infinity();
  std::string reason;
  EXPECT_FALSE(monitor.validate(cmd, reason));
}

TEST_F(SafetyMonitorTest, RejectsWhenEstopActive)
{
  monitor.set_estop(true);
  auto cmd = make_command();
  std::string reason;
  EXPECT_FALSE(monitor.validate(cmd, reason));
  EXPECT_NE(reason.find("e-stop"), std::string::npos);
}

TEST_F(SafetyMonitorTest, RejectsWhenForwardingDisabled)
{
  monitor.set_command_forwarding(false);
  auto cmd = make_command();
  std::string reason;
  EXPECT_FALSE(monitor.validate(cmd, reason));
}

TEST_F(SafetyMonitorTest, RejectsWhenHeartbeatStale)
{
  monitor.set_heartbeat_timeout(0.01);   // 10ms
  std::this_thread::sleep_for(std::chrono::milliseconds(50));
  auto cmd = make_command();
  std::string reason;
  EXPECT_FALSE(monitor.validate(cmd, reason));
  EXPECT_NE(reason.find("heartbeat"), std::string::npos);
}

TEST_F(SafetyMonitorTest, ClipsOutOfRangePosition)
{
  // left_knee_joint limits: -0.0873 to 2.8798
  auto cmd = make_command(3, 10.0);   // way above upper
  std::string reason;
  EXPECT_TRUE(monitor.validate(cmd, reason));
  EXPECT_NEAR(cmd.target_position, 2.8798, 1e-4);
}

TEST_F(SafetyMonitorTest, RespectsRateLimit)
{
  monitor.set_command_rate_limit(100.0);   // 10ms min interval
  auto cmd = make_command();
  std::string reason;
  ASSERT_TRUE(monitor.validate(cmd, reason));
  // Immediate second call should be rejected
  EXPECT_FALSE(monitor.validate(cmd, reason));
  EXPECT_NE(reason.find("rate"), std::string::npos);
}
