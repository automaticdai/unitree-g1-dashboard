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

All phases (1-6) complete.

Phase 2 adds:
- `g1_dashboard_bridge` C++ node with `SafetyMonitor` (heartbeat watchdog, limit clipping, NaN/Inf rejection, rate limit). Real unitree_hg integration gated by CMake `-DUSE_UNITREE_HG=ON` — in standalone mode the bridge validates and logs commands only.
- `g1_dashboard` simulator entry point (`ros2 run g1_dashboard simulator`) publishes realistic fake telemetry for hardware-free testing.
- Status panel rewritten with `BatteryGauge` (custom QPainter widget), `MotorTempHeatmap` (29 cells grouped by body part with temperature-based color), `RollingPlot` (pyqtgraph 10-second sliding window for angular velocity and linear acceleration).
- C++ gtests for safety_monitor (9 cases) and joint_limits (7 cases).

Phase 3 adds:
- Stick-figure G1 skeleton in `utils/kinematics.py` — 36 links with approximate G1 dimensions, forward kinematics from 29-vector joint angles. No URDF mesh files needed.
- `utils/transforms.py` — 4x4 matrix helpers (rotation, translation, look_at, perspective, ray-point distance). Fully tested (16 cases).
- `rendering/camera_controller.py` — orbit/pan/zoom camera with spherical coordinates. Screen-to-world ray casting for picking.
- `rendering/robot_renderer.py` — legacy-OpenGL stick-figure renderer (spheres at joints, cylinders for links), ray-based joint picking.
- `rendering/gl_widget.py` — `QOpenGLWidget` with ~30 FPS throttled redraw, mouse input handlers.
- `utils/selection.py` — `SelectionState` QObject shared across panels. 3D click ↔ joint row click are both wired to it and stay in sync.
- `widgets/joint_row.py` — clickable joint row with live value display, rad/deg toggle.

Phase 4 adds:
- `JointRow` upgraded with `QSlider` + `QDoubleSpinBox` per joint; tracks `current` vs `command` with a `dirty` flag. Dirty rows show an orange left border.
- `JointControlPanel` Send/Reset/Home/E-Stop buttons are wired. "Live send" toggle publishes `JointCommand` on every edit; staged mode batches on "Send". "Reset" snaps commands to current; "Home" commands zero pose. E-Stop calls the `EmergencyStop` service on `/emergency_stop`.
- Gain editor in the panel footer: kp/kd spin boxes + preset dropdown (Stiff/Default/Compliant/Custom). Presets are relative multipliers applied to each joint's `default_kp`/`default_kd`; overrides are per-joint.
- `DashboardNode` lazy-inits the `JointCommand` publisher on `/joint_commands` and an `EmergencyStop` service client.
- `utils/commanded_state.py` — `CommandedState` QObject shared on the node, mirroring `SelectionState`. Emits `commands_changed(positions, dirty)` when the commanded pose changes.
- `RobotRenderer.draw_ghost()` + `DigitalTwinGLWidget.set_commanded_pose()` render a semi-transparent orange skeleton overlay whenever any joint is dirty.

Phase 5 adds:
- `panels/camera_panel.py` — `msg_to_qimage()` converts `sensor_msgs/Image` (rgb8/bgr8/mono8) and `CompressedImage` to `QPixmap`. Uses cv_bridge if available, falls back to manual decoding. Snapshot saves PNG via `QFileDialog`. FPS counter (1-second sliding window).
- `utils/color_maps.py` — vectorized Viridis/Jet/Turbo (no matplotlib dependency) + `normalize()` with optional explicit bounds.
- `utils/point_cloud_utils.py` — `decode_pointcloud2()` via `sensor_msgs_py` (with manual struct fallback), `decimate()`, `filter_distance()`.
- `rendering/point_cloud_renderer.py` — `PointCloudGLWidget` with legacy GL vertex/color arrays for `GL_POINTS`. Reuses `CameraController` so navigation matches the digital twin.
- `panels/lidar_panel.py` — viewport + color mode dropdown (Height/Intensity/Distance/Flat), colormap dropdown, point size slider, point budget, distance min/max, accumulate-N-frames mode, reset view.

Phase 6 adds:
- `main_window.py` — keyboard shortcuts: Space (E-stop), Ctrl+Enter (Send), Ctrl+R (Reset), Ctrl+H (Home), Ctrl+L (toggle live mode), Ctrl+0 (reset 3D view), F2-F6 (toggle each panel). `Help → Shortcuts` lists them in-app.
- Layout persistence via `QSettings`: geometry + dock state saved on close, restored on next open. `Layout` menu adds Save Current / Load (named) / Manage / Reset to Default.
- `Dockerfile` based on `osrf/ros:humble-desktop` with PySide6, cv_bridge, sensor_msgs_py, OpenCV preinstalled. README documents X11 forwarding command.
- `docs/USAGE.md` covers panels, shortcuts, layout flow, joint control workflow, gain presets.

Test coverage: 63 Python tests passing, 24 skipped (PySide6/rclpy-gated). 16 C++ tests in bridge.
