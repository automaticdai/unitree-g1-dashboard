#include <gtest/gtest.h>

#include "g1_dashboard_bridge/lowcmd_builder.hpp"

using g1_dashboard_bridge::LowCmdBuilder;

class LowCmdBuilderTest : public ::testing::Test
{
protected:
  LowCmdBuilder b;
};

TEST_F(LowCmdBuilderTest, MotorInactiveByDefault)
{
  for (uint8_t i = 0; i < 29; ++i) {
    EXPECT_FALSE(b.is_active(i));
  }
}

TEST_F(LowCmdBuilderTest, FirstCommandSeedsFromMeasured)
{
  b.set_measured_position(3, 0.5);  // left knee at 0.5 rad
  b.update_command(3, 1.0, 300.0, 4.0, 0.0);
  EXPECT_TRUE(b.is_active(3));
  EXPECT_NEAR(b.commanded_q(3), 0.5, 1e-9);
  EXPECT_NEAR(b.target_q(3), 1.0, 1e-9);
  EXPECT_DOUBLE_EQ(b.commanded_kp(3), 300.0);
  EXPECT_DOUBLE_EQ(b.commanded_kd(3), 4.0);
}

TEST_F(LowCmdBuilderTest, FirstCommandWithoutMeasuredSeedsFromTarget)
{
  // No set_measured_position call — fall back to target so we never start
  // integrating from a stale zero.
  b.update_command(15, 1.0, 100.0, 2.0, 0.0);
  EXPECT_NEAR(b.commanded_q(15), 1.0, 1e-9);
}

TEST_F(LowCmdBuilderTest, SlewLimitsLargeStep)
{
  b.set_slew_rate(3, 2.0);
  b.set_measured_position(3, 0.0);
  b.update_command(3, 1.0, 300.0, 4.0, 0.0);

  // 1 ms tick: max step = 2.0 * 0.001 = 0.002 rad
  b.step(0.001, false);
  EXPECT_NEAR(b.commanded_q(3), 0.002, 1e-9);

  // After 500 ticks (0.5 s) we've moved 0.5 * 2.0 = 1.0 rad and converged.
  for (int i = 0; i < 499; ++i) {
    b.step(0.001, false);
  }
  EXPECT_NEAR(b.commanded_q(3), 1.0, 1e-9);
}

TEST_F(LowCmdBuilderTest, SlewSnapsWhenWithinTolerance)
{
  b.set_slew_rate(3, 2.0);
  b.set_measured_position(3, 0.0);
  b.update_command(3, 0.001, 300.0, 4.0, 0.0);

  // 0.01 s tick allows up to 0.02 rad; target is 0.001 away — should snap.
  b.step(0.01, false);
  EXPECT_NEAR(b.commanded_q(3), 0.001, 1e-9);
}

TEST_F(LowCmdBuilderTest, SlewHandlesNegativeError)
{
  b.set_slew_rate(3, 2.0);
  b.set_measured_position(3, 1.0);
  b.update_command(3, 0.0, 300.0, 4.0, 0.0);

  b.step(0.001, false);
  EXPECT_NEAR(b.commanded_q(3), 1.0 - 0.002, 1e-9);
}

TEST_F(LowCmdBuilderTest, EstopHoldsMeasured)
{
  b.set_measured_position(3, 0.0);
  b.update_command(3, 1.0, 300.0, 4.0, 0.0);
  b.step(0.002, false);

  // Robot starts to fall during estop; measured drifts.
  b.set_measured_position(3, 0.4);
  b.step(0.002, true);
  EXPECT_NEAR(b.commanded_q(3), 0.4, 1e-9);
  EXPECT_TRUE(b.estop_active());
}

TEST_F(LowCmdBuilderTest, EstopReleaseReseedsFromMeasured)
{
  b.set_slew_rate(3, 2.0);
  b.set_measured_position(3, 0.0);
  b.update_command(3, 1.0, 300.0, 4.0, 0.0);

  // Reach commanded position.
  for (int i = 0; i < 1000; ++i) {
    b.step(0.002, false);
  }
  ASSERT_NEAR(b.commanded_q(3), 1.0, 1e-9);

  // Estop, robot falls.
  b.set_measured_position(3, 0.3);
  b.step(0.002, true);
  ASSERT_NEAR(b.commanded_q(3), 0.3, 1e-9);

  // Release — integrator should restart from 0.3 + slew*dt toward 1.0.
  b.set_measured_position(3, 0.3);
  b.step(0.002, false);
  EXPECT_GT(b.commanded_q(3), 0.3);
  EXPECT_LT(b.commanded_q(3), 0.31);
}

TEST_F(LowCmdBuilderTest, IgnoresOutOfRangeJointIndex)
{
  b.update_command(99, 1.0, 100.0, 1.0, 0.0);
  b.set_measured_position(99, 1.0);
  b.set_slew_rate(99, 5.0);
  for (uint8_t i = 0; i < 29; ++i) {
    EXPECT_FALSE(b.is_active(i));
  }
}

TEST_F(LowCmdBuilderTest, ResetClearsState)
{
  b.set_measured_position(3, 0.5);
  b.update_command(3, 1.0, 300.0, 4.0, 0.0);
  ASSERT_TRUE(b.is_active(3));

  b.reset();
  EXPECT_FALSE(b.is_active(3));
  EXPECT_NEAR(b.commanded_q(3), 0.0, 1e-9);
  EXPECT_FALSE(b.estop_active());
}

TEST_F(LowCmdBuilderTest, MultipleMotorsIndependent)
{
  b.set_slew_rate(3, 2.0);
  b.set_slew_rate(15, 4.0);
  b.set_measured_position(3, 0.0);
  b.set_measured_position(15, 0.0);
  b.update_command(3, 1.0, 300.0, 4.0, 0.0);
  b.update_command(15, 1.0, 100.0, 2.0, 0.0);

  b.step(0.001, false);
  EXPECT_NEAR(b.commanded_q(3), 0.002, 1e-9);
  EXPECT_NEAR(b.commanded_q(15), 0.004, 1e-9);  // 4 rad/s * 1 ms
}
