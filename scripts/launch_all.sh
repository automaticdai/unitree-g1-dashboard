#!/bin/bash
# Convenience script to build and launch the full G1 dashboard stack.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WS_DIR="${SCRIPT_DIR}/../ros2_ws"

# Source ROS2
if [ -f /opt/ros/humble/setup.bash ]; then
    source /opt/ros/humble/setup.bash
else
    echo "ERROR: ROS2 Humble not found at /opt/ros/humble/setup.bash"
    exit 1
fi

# Build workspace
echo "Building workspace..."
cd "${WS_DIR}"
colcon build --symlink-install
source install/setup.bash

# Set DDS configuration
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

# Launch
echo "Launching G1 Dashboard..."
ros2 launch g1_dashboard dashboard.launch.py "$@"
