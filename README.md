# unitree-g1-dashboard

A native desktop dashboard for controlling and visualizing the **Unitree G1 humanoid robot**. Features a real-time digital twin with bidirectional data flow, built as a ROS2 node using Python (rclpy + PySide6).

## Features

- **Digital Twin** — 3D URDF model with real-time joint animation, interactive joint selection, and command preview ghost overlay
- **Joint Control** — Bidirectional: visualize 29-DOF joint angles and send commands with safety enforcement (live/staged modes, E-stop)
- **Status Panel** — IMU orientation cube, battery gauge, motor temperatures, robot mode, real-time pyqtgraph plots, error log
- **Camera** — Live image display via rclpy subscription + cv_bridge (no web server needed)
- **LiDAR** — OpenGL point cloud visualization with color modes and decimation

## Architecture

The dashboard **is** a ROS2 node — no `rosbridge`, no middleware, no serialization overhead.

```
G1 Robot  ->  g1_dashboard_bridge (C++/ROS2)  ->  sensor_msgs at 50 Hz
          <-  validated LowCmd with CRC        <-  /joint_commands
                          |
                          v
              g1_dashboard (Python/ROS2)
              rclpy subscriptions + PySide6 GUI
              OpenGL viewports for 3D + point cloud
```

## Tech Stack

| Layer | Stack |
|-------|-------|
| Bridge | C++ ROS2 node, CycloneDDS 0.10.2, unitree_hg messages |
| Dashboard | Python 3.10+, rclpy, PySide6 (Qt6), PyOpenGL |
| 3D / URDF | yourdfpy, trimesh, QOpenGLWidget |
| Plotting | pyqtgraph (real-time 50 Hz graphs) |
| Camera | cv_bridge + OpenCV |
| Point Cloud | sensor_msgs_py + OpenGL VBO |

## Project Structure

```
ros2_ws/src/
├── g1_dashboard/              # Dashboard GUI (Python/rclpy/PySide6)
│   ├── g1_dashboard/          # Source package
│   │   ├── main.py            # Entry point: rclpy init + Qt app
│   │   ├── dashboard_node.py  # ROS2 node with Qt signal bridge
│   │   ├── main_window.py     # QMainWindow with dockable panels
│   │   ├── config/            # Topic names, joint definitions
│   │   ├── panels/            # 5 dock panels (twin, joints, status, camera, lidar)
│   │   ├── widgets/           # Reusable Qt widgets
│   │   ├── rendering/         # OpenGL renderers (URDF, point cloud)
│   │   └── utils/             # Thread bridge, transforms, helpers
│   ├── launch/                # ROS2 launch files
│   ├── config/                # YAML parameters
│   ├── resource/              # URDF, meshes, icons, QSS theme
│   └── test/                  # pytest tests
├── g1_dashboard_msgs/         # Custom messages (JointCommand, RobotState, SafetyStatus)
└── g1_dashboard_bridge/       # C++ bridge: unitree_hg <-> sensor_msgs (Phase 2)
```

## Quick Start

### Prerequisites

- Ubuntu 22.04 with ROS2 Humble (`ros-humble-desktop`)
- Python 3.10+ with PySide6: `pip install PySide6 pyqtgraph pyopengl yourdfpy trimesh`
- CycloneDDS 0.10.2 (for Unitree robot communication)

### Build & Run

```bash
# Build
source /opt/ros/humble/setup.bash
cd ros2_ws && colcon build --symlink-install && source install/setup.bash

# Run dashboard
ros2 run g1_dashboard dashboard

# Or launch full stack (bridge + dashboard)
ros2 launch g1_dashboard dashboard.launch.py robot_model:=g1_29dof_rev_1_0
```

### Testing Without a Robot

```bash
# Publish fake joint states
ros2 topic pub /joint_states sensor_msgs/msg/JointState \
  "{header: {stamp: {sec: 0}}, name: ['left_hip_pitch_joint'], position: [0.5]}" --rate 50

# Or use joint_state_publisher_gui
ros2 launch g1_dashboard dashboard_only.launch.py use_joint_state_publisher_gui:=true
```

### Run Tests

```bash
cd ros2_ws/src/g1_dashboard && python3 -m pytest test/ -v
```

## Development Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 1. Foundation | Done | Package scaffold, rclpy+PySide6 integration, dock layout, dark theme, status bar |
| 2. Bridge + Status | Pending | C++ bridge node, live IMU/battery/state with pyqtgraph |
| 3. Digital Twin | Pending | URDF loading, OpenGL rendering, joint animation, picking |
| 4. Joint Control | Pending | Sliders, command publishing, ghost overlay, E-stop |
| 5. Camera + LiDAR | Pending | cv_bridge image display, OpenGL point cloud |
| 6. Polish + Deploy | Pending | Integration testing, Docker, documentation |

## Documentation

See [SPEC.md](SPEC.md) for the full project specification including architecture, panel designs, ROS2 node details, threading model, joint reference tables, and development phases.
