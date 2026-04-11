# CLAUDE.md

## Project Overview

Unitree G1 humanoid robot dashboard — a native desktop application (not web-based) for real-time control and visualization. Built as a ROS2 node using Python (rclpy + PySide6).

## Architecture

- **g1_dashboard** (Python): The GUI application. A single ROS2 node using rclpy for direct topic subscription/publication. PySide6 (Qt6) for the UI. rclpy spins in a daemon thread; Qt runs on the main thread. ROS callbacks emit Qt signals for thread-safe GUI updates.
- **g1_dashboard_msgs**: Custom ROS2 message/service definitions (JointCommand, RobotState, SafetyStatus, EmergencyStop, SetControlMode).
- **g1_dashboard_bridge** (C++, not yet implemented): Translates Unitree-proprietary `unitree_hg` DDS messages to standard `sensor_msgs` at 50 Hz, with safety validation for bidirectional joint commands.

## Key Paths

- Dashboard source: `ros2_ws/src/g1_dashboard/g1_dashboard/`
- Entry point: `g1_dashboard/main.py` -> `main()`
- ROS2 node: `g1_dashboard/dashboard_node.py` -> `DashboardNode`
- Main window: `g1_dashboard/main_window.py` -> `MainWindow`
- Joint config (29 DOF): `g1_dashboard/config/robot_config.py`
- Topic config: `g1_dashboard/config/ros_config.py`
- Panel widgets: `g1_dashboard/panels/` (digital_twin, joint_control, status, camera, lidar)
- Custom messages: `ros2_ws/src/g1_dashboard_msgs/msg/` and `srv/`
- Dark theme: `ros2_ws/src/g1_dashboard/resource/styles/dark_theme.qss`
- Tests: `ros2_ws/src/g1_dashboard/test/`

## Build & Run

```bash
source /opt/ros/humble/setup.bash
cd ros2_ws && colcon build --symlink-install && source install/setup.bash
ros2 run g1_dashboard dashboard
```

## Test

```bash
cd ros2_ws/src/g1_dashboard && python3 -m pytest test/ -v
```

## Code Conventions

- Python 3.10+ (type hints with `X | None` syntax, not `Optional[X]`)
- PySide6 (not PyQt5/PyQt6) — use `Signal` not `pyqtSignal`
- ROS callbacks MUST NOT touch Qt widgets — emit a Qt signal instead
- Joint indices are 0-28 per `robot_config.py` (matches Unitree firmware ordering)
- All topic names defined in `ros_config.py` — never hardcode topic strings in panels
- Dark theme via QSS stylesheet — panels should not set their own background colors
- Tests use pytest (not unittest)
- Linting with ruff

## Threading Model

```
Main Thread:       Qt event loop (QApplication.exec)
                   All widget creation, updates, rendering

Spin Thread:       rclpy.spin(node) — daemon thread
                   Subscription callbacks run here
                   Callbacks emit Qt signals (thread-safe)
                   NEVER call widget methods from this thread
```

## Current Status

Phase 1 (Foundation) complete. Phases 2-6 pending.
