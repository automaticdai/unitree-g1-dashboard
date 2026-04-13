#include <gtest/gtest.h>

#include "g1_dashboard_bridge/g1_joint_config.hpp"

using g1_dashboard_bridge::JOINT_TABLE;
using g1_dashboard_bridge::NUM_JOINTS;
using g1_dashboard_bridge::clamp_to_limits;

TEST(JointConfigTest, HasTwentyNineJoints)
{
  EXPECT_EQ(NUM_JOINTS, 29u);
  EXPECT_EQ(JOINT_TABLE.size(), 29u);
}

TEST(JointConfigTest, IndicesMatchArrayPosition)
{
  for (size_t i = 0; i < JOINT_TABLE.size(); ++i) {
    EXPECT_EQ(JOINT_TABLE[i].index, i);
  }
}

TEST(JointConfigTest, AllLimitsValid)
{
  for (const auto & joint : JOINT_TABLE) {
    EXPECT_LT(joint.limits.lower, joint.limits.upper)
      << "Invalid limits for joint " << joint.name;
    EXPECT_GT(joint.limits.default_kp, 0.0);
    EXPECT_GT(joint.limits.default_kd, 0.0);
  }
}

TEST(JointConfigTest, ClampInRangePassesThrough)
{
  EXPECT_NEAR(clamp_to_limits(3, 1.0), 1.0, 1e-9);
}

TEST(JointConfigTest, ClampBelowLower)
{
  // left_knee lower bound: -0.0873
  EXPECT_NEAR(clamp_to_limits(3, -5.0), -0.0873, 1e-4);
}

TEST(JointConfigTest, ClampAboveUpper)
{
  // left_knee upper bound: 2.8798
  EXPECT_NEAR(clamp_to_limits(3, 10.0), 2.8798, 1e-4);
}

TEST(JointConfigTest, ClampBadIndexReturnsInput)
{
  // Out-of-range index: function returns the value unchanged
  EXPECT_NEAR(clamp_to_limits(100, 42.0), 42.0, 1e-9);
}
