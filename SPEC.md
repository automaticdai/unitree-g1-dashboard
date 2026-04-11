# Unitree G1 Dashboard — Project Specification

A native desktop dashboard for controlling and visualizing the Unitree G1 humanoid robot. The dashboard formulates a **digital twin** with **bidirectional data flow** — researchers can observe real-time robot state AND send commands back. Built as a **ROS2 node** using **Python (rclpy + PySide6)**, subscribing and publishing directly on the ROS2 graph with no middleware bridge.

---

## 1. System Architecture

```
G1 Robot (192.168.123.161)
    | Ethernet / CycloneDDS (rt/lowstate, rt/lowcmd)
    v
ROS2 Host Machine (192.168.123.99)
    |-- g1_dashboard_bridge node (C++)     <- translates unitree_hg <-> sensor_msgs
    |-- robot_state_publisher              <- URDF -> TF tree
    v
    |-- g1_dashboard node (Python)         <- THE DASHBOARD (rclpy + PySide6)
        |-- subscribes directly to /joint_states, /imu/data, /battery_state, etc.
        |-- publishes directly to /joint_commands
        |-- renders Qt GUI with OpenGL viewports
```

### Key Difference from a Web-Based Approach

The dashboard **is** a ROS2 node. No `rosbridge_suite`, no `web_video_server`, no WebSocket serialization. The PySide6 GUI runs in the same process as rclpy, subscribing to topics at native speed with zero translation overhead.

### 1.1 Downstream Data Flow (Robot -> Dashboard)

1. G1 firmware publishes `unitree_hg::msg::LowState` at 500 Hz on DDS topic `rt/lowstate`
2. `g1_dashboard_bridge` (C++) subscribes, extracts motor/IMU/BMS data, re-publishes as standard `sensor_msgs` at 50 Hz
3. `g1_dashboard` (Python) subscribes directly via rclpy callbacks
4. Qt signals bridge ROS callbacks to the GUI thread for rendering
5. Camera images received as `sensor_msgs/Image` via rclpy, converted to `QImage` with `cv_bridge` + OpenCV
6. Point clouds received as `sensor_msgs/PointCloud2` via rclpy, decoded with `sensor_msgs_py`, rendered via OpenGL

### 1.2 Upstream Data Flow (Dashboard -> Robot)

1. Researcher adjusts joint angle via slider, 3D model interaction, or numeric input
2. Dashboard node publishes `g1_dashboard_msgs/JointCommand` directly via rclpy
3. `g1_dashboard_bridge` validates limits, converts to `unitree_hg::msg::LowCmd` with CRC
4. Robot firmware executes the command

### 1.3 Threading Model

```
Main Thread (Qt Event Loop)
    |-- PySide6 GUI rendering
    |-- Signal/slot connections for all UI updates
    |-- OpenGL viewports (digital twin, point cloud)

ROS2 Spin Thread (background)
    |-- rclpy.spin() in a daemon thread
    |-- Subscription callbacks emit Qt signals (thread-safe)
    |-- Timer callbacks for heartbeat publishing
```

`rclpy` callbacks run on the spin thread. They must NOT touch Qt widgets directly. Instead, each callback emits a Qt signal carrying the message data, which the main thread receives via slot connections.

### 1.4 Safety Architecture

- **Joint limit enforcement**: Bridge node hard-clips all commanded values to URDF-defined limits (authoritative safety gate). GUI also enforces limits but bridge is definitive.
- **Rate limiting**: Commands throttled to max 50 Hz in the bridge
- **Dead-man switch**: Dashboard publishes heartbeat at 10 Hz. If bridge loses heartbeat for 500 ms, it issues soft stop (damping mode).
- **Mode gating**: Bridge only forwards commands in appropriate control mode. Mode mismatch triggers a dashboard warning.
- **Command validation**: Every `JointCommand` checked for NaN, Inf, and out-of-range values

---

## 2. Technology Stack

### 2.1 ROS2 Backend

| Component | Package / Version | Purpose |
|---|---|---|
| ROS2 Distribution | **Humble Hawksbill** (LTS) | Core middleware |
| DDS Implementation | **CycloneDDS 0.10.2** | Wire-compatible with Unitree firmware |
| RMW Layer | `rmw_cyclonedds_cpp` | ROS2-to-CycloneDDS bridge |
| Unitree Messages | `unitree_hg` (from `unitree_ros2`) | Native G1 message types |
| Standard Messages | `sensor_msgs`, `geometry_msgs`, `std_msgs` | Dashboard-facing topics |
| TF2 | `tf2_ros` | Transform broadcasting |
| Robot Description | `robot_state_publisher` | URDF-based TF tree |
| Build System | `colcon` | Workspace build |

### 2.2 Dashboard Application

| Component | Package / Version | Purpose |
|---|---|---|
| Language | **Python 3.10+** | Development speed, researcher-friendly |
| ROS2 Client | **rclpy** | Native ROS2 subscriptions and publications |
| GUI Framework | **PySide6 6.6+** | Qt6 widgets, layouts, docking |
| 3D Rendering | **PyOpenGL 3.1+** | OpenGL for digital twin and point cloud |
| URDF Parsing | **yourdfpy 0.0.56+** | Parse URDF, compute forward kinematics |
| Mesh Loading | **trimesh 4.x** | Load STL/DAE meshes for OpenGL rendering |
| Real-Time Plots | **pyqtgraph 0.13+** | High-performance time-series graphs (IMU, telemetry) |
| Image Conversion | **cv_bridge + OpenCV** | ROS Image -> numpy -> QImage |
| Point Cloud | **sensor_msgs_py** | Decode PointCloud2 to structured numpy arrays |
| NumPy | **numpy 1.24+** | Array operations for point clouds, transforms |
| Transforms | **transforms3d** | Quaternion/Euler conversions |
| Testing | **pytest + pytest-qt** | Unit/widget tests |
| Linting | **ruff** | Fast Python linter + formatter |

### 2.3 Deployment

| Component | Tool | Purpose |
|---|---|---|
| Packaging | ROS2 `ament_python` package | Standard ROS2 Python package |
| Containerization | **Docker** (optional) | Reproducible environment |
| ROS2 Base Image | `osrf/ros:humble-desktop` | Prebuilt ROS2 with GUI support |
| Process Manager | ROS2 launch system | Orchestrate bridge + dashboard |

---

## 3. Project Directory Structure

```
unitree-g1-dashboard/
├── README.md
├── SPEC.md
├── LICENSE
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── ros2_ws/                                  # ROS2 colcon workspace
│   └── src/
│       ├── g1_dashboard/                     # Dashboard GUI package (Python)
│       │   ├── package.xml
│       │   ├── setup.py
│       │   ├── setup.cfg
│       │   ├── config/
│       │   │   ├── dashboard_params.yaml     # Topic names, rates, UI defaults
│       │   │   └── g1_joint_config.yaml      # Joint names, indices, limits, groups
│       │   ├── launch/
│       │   │   ├── dashboard.launch.py       # Full stack: bridge + dashboard
│       │   │   └── dashboard_only.launch.py  # Dashboard only (bridge running separately)
│       │   ├── resource/
│       │   │   ├── g1_dashboard               # ament resource index marker
│       │   │   ├── urdf/                      # URDF files
│       │   │   │   ├── g1_29dof_rev_1_0.urdf
│       │   │   │   └── g1_23dof_rev_1_0.urdf
│       │   │   ├── meshes/                    # STL/DAE mesh files
│       │   │   ├── icons/                     # UI icons (e-stop, battery, etc.)
│       │   │   └── styles/
│       │   │       └── dark_theme.qss         # Qt stylesheet (dark theme)
│       │   ├── g1_dashboard/                  # Python source package
│       │   │   ├── __init__.py
│       │   │   ├── main.py                    # Entry point: init rclpy, launch Qt app
│       │   │   ├── dashboard_node.py          # ROS2 node: subscriptions, publishers, signals
│       │   │   ├── main_window.py             # QMainWindow with dock layout
│       │   │   │
│       │   │   ├── config/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── ros_config.py          # Topic names, QoS profiles
│       │   │   │   └── robot_config.py        # Joint definitions, limits, groups
│       │   │   │
│       │   │   ├── panels/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── digital_twin_panel.py  # OpenGL 3D viewport with URDF model
│       │   │   │   ├── joint_control_panel.py # Joint sliders, command bar, gain editor
│       │   │   │   ├── status_panel.py        # IMU, battery, robot state, error log
│       │   │   │   ├── camera_panel.py        # Camera image display
│       │   │   │   └── lidar_panel.py         # Point cloud OpenGL viewport
│       │   │   │
│       │   │   ├── widgets/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── joint_slider.py        # Single joint: slider + value + input
│       │   │   │   ├── joint_group.py         # Collapsible joint group
│       │   │   │   ├── imu_cube.py            # 3D orientation cube (OpenGL)
│       │   │   │   ├── battery_gauge.py       # Circular battery gauge
│       │   │   │   ├── topic_indicator.py     # Connection status dot per topic
│       │   │   │   ├── error_log.py           # Scrolling error/warning log
│       │   │   │   └── estop_button.py        # Prominent emergency stop button
│       │   │   │
│       │   │   ├── rendering/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── gl_widget.py           # QOpenGLWidget base class
│       │   │   │   ├── robot_renderer.py      # URDF mesh loading + joint-driven rendering
│       │   │   │   ├── ghost_renderer.py      # Semi-transparent command preview overlay
│       │   │   │   ├── point_cloud_renderer.py# OpenGL point cloud rendering
│       │   │   │   ├── grid_renderer.py       # Ground plane grid
│       │   │   │   └── camera_controller.py   # Orbit/pan/zoom mouse controls
│       │   │   │
│       │   │   └── utils/
│       │   │       ├── __init__.py
│       │   │       ├── qt_ros_bridge.py       # Thread-safe ROS callback -> Qt signal bridge
│       │   │       ├── transforms.py          # Quaternion/Euler, forward kinematics helpers
│       │   │       ├── point_cloud_utils.py   # PointCloud2 decoding + decimation
│       │   │       ├── color_maps.py          # Viridis, jet, turbo for point cloud coloring
│       │   │       └── joint_limits.py        # Client-side limit validation
│       │   │
│       │   └── test/
│       │       ├── test_dashboard_node.py
│       │       ├── test_joint_limits.py
│       │       ├── test_point_cloud_utils.py
│       │       └── test_transforms.py
│       │
│       ├── g1_dashboard_bridge/              # Bridge node package (C++)
│       │   ├── CMakeLists.txt
│       │   ├── package.xml
│       │   ├── config/
│       │   │   ├── bridge_params.yaml
│       │   │   └── g1_joint_config.yaml
│       │   ├── launch/
│       │   │   └── bridge_only.launch.py
│       │   ├── src/
│       │   │   ├── bridge_node.cpp
│       │   │   ├── safety_monitor.cpp
│       │   │   ├── joint_command_handler.cpp
│       │   │   └── tf_broadcaster.cpp
│       │   ├── include/g1_dashboard_bridge/
│       │   │   ├── bridge_node.hpp
│       │   │   ├── safety_monitor.hpp
│       │   │   ├── joint_command_handler.hpp
│       │   │   ├── g1_joint_config.hpp
│       │   │   └── tf_broadcaster.hpp
│       │   └── test/
│       │       ├── test_safety_monitor.cpp
│       │       └── test_joint_limits.cpp
│       │
│       └── g1_dashboard_msgs/                # Custom message definitions
│           ├── CMakeLists.txt
│           ├── package.xml
│           ├── msg/
│           │   ├── JointCommand.msg
│           │   ├── RobotState.msg
│           │   └── SafetyStatus.msg
│           └── srv/
│               ├── SetControlMode.srv
│               └── EmergencyStop.srv
│
├── scripts/
│   ├── setup_network.sh                      # Configure 192.168.123.99 interface
│   └── launch_all.sh                         # Convenience: source + launch
│
└── docs/
    ├── architecture.md
    ├── setup-guide.md
    └── ros2-topics.md
```

---

## 4. Panel Specifications

The main window uses `QDockWidget` for each panel, providing native drag, dock, undock, tabify, and resize. Default layout arranges panels in a 2x2 grid with the digital twin spanning the left column.

### 4.1 Digital Twin Panel (OpenGL)

**Purpose:** 3D visualization of the G1 robot model driven by real-time joint states, with interactive joint selection and command preview.

**Implementation:**
- `QOpenGLWidget` subclass with custom OpenGL rendering
- URDF parsed with `yourdfpy`, meshes loaded with `trimesh`, converted to OpenGL vertex buffers at startup
- Forward kinematics computed per frame from joint state array using URDF joint definitions
- Each link rendered at its computed world transform

**Data Flow:**
- **Inbound**: `/joint_states` at 50 Hz -> joint positions update forward kinematics -> re-render
- **Inbound**: `/tf` (optional) for external transform updates

**Rendering:**
```
Scene
├── Ambient light + directional light with shadows
├── Ground grid (10x10m, subtle lines)
├── Axes indicator (corner overlay)
├── Robot model (current pose, solid materials)
├── Ghost model (commanded pose, transparent orange, conditional)
└── Orbit/pan/zoom via mouse (camera_controller.py)
```

**Interactions:**
- **Click-to-select**: OpenGL picking (color-based or ray-mesh intersection via `trimesh`) maps click to joint index
- **Bidirectional highlight**: Selected joint highlighted with emissive color; selection synced with Joint Control Panel via Qt signals
- **Ghost overlay**: When commanded positions differ from current, a semi-transparent orange model renders the target pose
- **Camera**: Perspective, initial position 2m back + 1.5m up, looking at waist (~0.8m). Reset view button.

### 4.2 Joint Angles & Control Panel (Qt Widgets)

**Data Flow:**
- **Inbound**: `/joint_states` (`sensor_msgs/JointState`) at 50 Hz
- **Outbound**: `/joint_commands` (`g1_dashboard_msgs/JointCommand`)

**UI Components:**

| Component | Qt Widget | Description |
|---|---|---|
| **Joint Group** | `QGroupBox` (collapsible) | Groups: Left Leg (0-5), Right Leg (6-11), Waist (12-14), Left Arm (15-21), Right Arm (22-28). Each group collapsible with header showing group name. |
| **Joint Slider** | `QSlider` + `QDoubleSpinBox` + `QProgressBar` | Per joint: name label, slider clamped to URDF limits, spin box for precise input, progress bar showing current (blue) vs commanded (orange), velocity/effort labels. Limit warning when within 5% of range boundary. |
| **Unit Toggle** | `QComboBox` / `QCheckBox` | Switch between radians and degrees display |
| **Command Bar** | `QHBoxLayout` with `QPushButton`s | "Send" (publish all modified joints), "Reset to Current" (snap sliders to current state), "Home" (zero/nominal), **E-Stop** (`QPushButton` styled red + bold). Toggle: "Live" vs "Staged" mode. |
| **Gain Editor** | Collapsible `QGroupBox` per joint | `QDoubleSpinBox` for kp/kd. Presets dropdown (`QComboBox`): Stiff, Compliant, Custom. |

**Interactions:**
- Clicking a joint in the 3D digital twin emits a signal -> auto-scrolls `QScrollArea` to that joint's slider
- Clicking/selecting a slider emits a signal -> highlights joint in 3D model
- In "Live" mode: slider `valueChanged` signal directly publishes `JointCommand`
- In "Staged" mode: slider changes buffered until "Send" is clicked

### 4.3 Status Panel (Qt Widgets + pyqtgraph)

**Topics:**
- `/imu/data` (`sensor_msgs/Imu`) at 50 Hz
- `/battery_state` (`sensor_msgs/BatteryState`) at 1 Hz
- `/robot_state` (`g1_dashboard_msgs/RobotState`) at 10 Hz
- `/safety_status` (`g1_dashboard_msgs/SafetyStatus`) at 10 Hz

**UI Components:**

| Component | Implementation | Description |
|---|---|---|
| **IMU Orientation Cube** | `QOpenGLWidget` (small) | Cube that rotates with IMU quaternion. Axes labeled X/Y/Z with R/G/B colors. |
| **Euler Angles** | `QLabel` readouts | Roll, Pitch, Yaw in degrees, updated live |
| **IMU Graphs** | `pyqtgraph.PlotWidget` | Two plots: angular velocity (3-axis) and linear acceleration (3-axis). Rolling 10-second window. High-performance: pyqtgraph handles 50 Hz updates natively. |
| **Battery Gauge** | Custom `QWidget` (painted) | Circular gauge, color-coded (green >50%, yellow 20-50%, red <20%). Numeric: voltage, current, temperature. Low battery warning banner at <15%. |
| **Robot Mode** | `QLabel` with colored badge | Idle/Standing/Walking/Low-Level/Damping/Emergency |
| **Motor Temperatures** | `QGridLayout` with colored `QLabel`s | 29-motor heatmap (green/yellow/red based on temperature thresholds) |
| **Foot Forces** | `QProgressBar` x4 | One bar per foot contact sensor |
| **Error Log** | `QTextEdit` (read-only) | Timestamped, severity-colored (red/yellow/white). Auto-scroll with manual scroll lock. Severity filter checkboxes. |
| **Topic Health** | `QHBoxLayout` of `TopicIndicator` widgets | Green/yellow/red dot per topic with Hz readout |

### 4.4 Camera Panel

**Data Flow:**
- Subscribes to `/camera/image_raw` (`sensor_msgs/Image`) or `/camera/image_raw/compressed` (`sensor_msgs/CompressedImage`) directly via rclpy
- Conversion: `cv_bridge.CvBridge().imgmsg_to_cv2()` -> numpy BGR -> `QImage` -> `QPixmap` -> `QLabel.setPixmap()`
- No `web_video_server` needed — images flow through ROS2 natively

**UI Components:**

| Component | Qt Widget | Description |
|---|---|---|
| **Image Display** | `QLabel` with `QPixmap` | Full-panel image, auto-scaled with aspect ratio via `Qt.KeepAspectRatio`. "No Signal" overlay if topic unavailable. |
| **Topic Selector** | `QComboBox` | Dropdown listing available image topics (discovered via `ros2 topic list` filtered by type). Switch between raw/compressed. |
| **Snapshot** | `QPushButton` | Save current frame as PNG with timestamp filename via `QFileDialog`. |
| **FPS Counter** | `QLabel` | Computed from message arrival rate |

**Performance:**
- For raw images at 30 FPS / 640x480: ~27 MB/s — handled easily by in-process rclpy (no serialization overhead)
- For compressed images: use `cv2.imdecode()` on the JPEG/PNG bytes
- Frame skipping: if GUI can't keep up, drop older frames (keep latest only)

### 4.5 LiDAR Panel (OpenGL)

**Data Flow:**
- Subscribes to `/lidar/points` (`sensor_msgs/PointCloud2`) directly via rclpy
- `sensor_msgs_py.point_cloud2.read_points_numpy()` decodes to structured numpy array with x, y, z, intensity fields — no manual binary parsing needed
- Decimation: `numpy` slicing (e.g., `points[::stride]`) to cap at configurable max points

**UI Components:**

| Component | Implementation | Description |
|---|---|---|
| **Point Cloud Viewport** | `QOpenGLWidget` | OpenGL `GL_POINTS` with VBO. Orbit/pan/zoom controls. Axes indicator. Ground grid. |
| **Color Mode** | `QComboBox` | Height (Z), Intensity, Distance, Flat. Colormap applied via numpy vectorized operations. |
| **Colormap** | `QComboBox` | Viridis, Jet, Turbo |
| **Point Size** | `QSlider` | 1-5 pixels (`glPointSize`) |
| **Point Budget** | `QSpinBox` | 10K - 500K max points |
| **Frame Mode** | `QCheckBox` | Latest only vs. accumulate N frames |
| **Distance Filter** | Two `QDoubleSpinBox` | Min/max distance from sensor origin |

**Performance:**
- `sensor_msgs_py` decodes PointCloud2 directly to numpy — much faster than manual struct unpacking
- VBO updated in-place via `glBufferSubData` to avoid reallocation
- Color computation vectorized with numpy (no Python loops)
- Target: 15-20 FPS at 100K points (better than web since no base64 encoding/decoding overhead)

---

## 5. ROS2 Node Design

### 5.1 g1_dashboard_bridge (C++)

The bridge between Unitree-native DDS topics and standard ROS2 messages.

**Subscriptions (from robot):**

| Topic | Type | Rate |
|---|---|---|
| `rt/lowstate` | `unitree_hg::msg::LowState` | 500 Hz |
| `rt/sportmodestate` | `unitree_hg::msg::SportModeState` | 50 Hz |

**Publications (to dashboard):**

| Topic | Type | Rate |
|---|---|---|
| `/joint_states` | `sensor_msgs/JointState` | 50 Hz |
| `/imu/data` | `sensor_msgs/Imu` | 50 Hz |
| `/battery_state` | `sensor_msgs/BatteryState` | 1 Hz |
| `/robot_state` | `g1_dashboard_msgs/RobotState` | 10 Hz |
| `/safety_status` | `g1_dashboard_msgs/SafetyStatus` | 10 Hz |
| `/tf` | `tf2_msgs/TFMessage` | 50 Hz |

**Subscriptions (from dashboard):**

| Topic | Type |
|---|---|
| `/joint_commands` | `g1_dashboard_msgs/JointCommand` |
| `/dashboard_heartbeat` | `std_msgs/Header` |

**Publications (to robot):**

| Topic | Type | Rate |
|---|---|---|
| `rt/lowcmd` | `unitree_hg::msg::LowCmd` | max 50 Hz |

**Key details:**
- `G1JointConfig` struct maps 29 joint indices to URDF names and limits
- 500 Hz subscription to `rt/lowstate`, downsampled to 50 Hz for `/joint_states`
- CRC calculation via `motor_crc_hg.cpp` from `unitree_ros2`
- All rates, topic names, safety params configurable via `bridge_params.yaml`

### 5.2 g1_dashboard (Python)

The dashboard GUI node.

**Subscriptions:**

| Topic | Type | Rate | Callback Behavior |
|---|---|---|---|
| `/joint_states` | `sensor_msgs/JointState` | 50 Hz | Emit `joint_states_received` signal |
| `/imu/data` | `sensor_msgs/Imu` | 50 Hz | Emit `imu_received` signal |
| `/battery_state` | `sensor_msgs/BatteryState` | 1 Hz | Emit `battery_received` signal |
| `/robot_state` | `g1_dashboard_msgs/RobotState` | 10 Hz | Emit `robot_state_received` signal |
| `/safety_status` | `g1_dashboard_msgs/SafetyStatus` | 10 Hz | Emit `safety_received` signal |
| `/camera/image_raw` | `sensor_msgs/Image` | 30 Hz | Emit `camera_received` signal |
| `/lidar/points` | `sensor_msgs/PointCloud2` | 10 Hz | Emit `pointcloud_received` signal |

**Publications:**

| Topic | Type | Rate |
|---|---|---|
| `/joint_commands` | `g1_dashboard_msgs/JointCommand` | On-demand (max 50 Hz) |
| `/dashboard_heartbeat` | `std_msgs/Header` | 10 Hz (timer) |

**Entry Point (`main.py`):**
```python
def main():
    rclpy.init()
    node = DashboardNode()

    # Start rclpy spin in background thread
    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()

    # Run Qt application on main thread
    app = QApplication(sys.argv)
    app.setStyleSheet(load_stylesheet('dark_theme.qss'))
    window = MainWindow(node)
    window.show()
    exit_code = app.exec()

    node.destroy_node()
    rclpy.shutdown()
    sys.exit(exit_code)
```

### 5.3 Supporting Nodes

| Node | Package | Purpose |
|---|---|---|
| `robot_state_publisher` | standard ROS2 | URDF + `/joint_states` -> TF tree |

### 5.4 Launch File (dashboard.launch.py)

Orchestrates all nodes:
1. Load G1 URDF (parameterized for 23/29 DOF variant)
2. Start `robot_state_publisher` with URDF
3. Start `g1_dashboard_bridge_node` with `bridge_params.yaml`
4. Start `g1_dashboard` with `dashboard_params.yaml`
5. Optionally start `rviz2` for debugging

---

## 6. Digital Twin Implementation

### 6.1 URDF Loading Pipeline

1. **Parse URDF**: `yourdfpy.URDF.load(urdf_path)` parses the URDF and provides the kinematic tree, joint definitions, and mesh file paths
2. **Load meshes**: `trimesh.load()` reads STL/DAE files referenced in the URDF, extracts vertices, normals, and faces
3. **Create OpenGL buffers**: At startup, each mesh is uploaded to a VBO/VAO. This is a one-time cost.
4. **Joint mapping**: `yourdfpy` provides `joint_names`, `joint_limits`, and `joint_types`. Mapped to Unitree indices via `robot_config.py`.

### 6.2 Real-Time Joint State Visualization

- `joint_states_received` signal delivers new positions to the digital twin panel
- `yourdfpy` computes forward kinematics: `urdf_model.update_cfg(joint_positions_dict)` updates all link transforms
- Each link's 4x4 world transform is read and applied as the OpenGL model matrix when rendering its mesh
- `QOpenGLWidget.update()` triggers `paintGL()` at display refresh rate

### 6.3 Interactive Joint Selection

- **OpenGL picking**: On click, render each link mesh with a unique flat color (color-based picking) into an offscreen framebuffer, read pixel at click position, map color back to link/joint index
- **Alternative**: Use `trimesh.ray` for CPU-based ray-mesh intersection (simpler, slightly slower)
- **Highlight**: Selected link rendered with additive emissive color
- **Bidirectional sync**: `joint_selected(int)` signal connected to both the 3D panel and the joint control panel

### 6.4 Ghost Overlay (Command Preview)

- When commanded positions differ from current: render robot model a second time with same meshes but transparent orange material (`glBlendFunc`, `glEnable(GL_BLEND)`)
- Ghost uses commanded joint positions for forward kinematics
- Solid model uses current joint positions
- Ghost visibility toggled by comparing commanded vs current arrays

### 6.5 Camera Controls

Implemented in `camera_controller.py`, tracking mouse events on the `QOpenGLWidget`:
- **Left drag**: Orbit (azimuth/elevation around target point)
- **Right drag**: Pan (translate target + camera position)
- **Scroll**: Zoom (move camera along view direction)
- **Middle click**: Reset to default view (2m back, 1.5m up, looking at waist)

---

## 7. Qt-ROS2 Thread Bridge

The critical integration pattern between rclpy callbacks and Qt GUI updates:

```python
class DashboardNode(Node):
    """ROS2 node with Qt signal emitters for thread-safe GUI updates."""

    class Signals(QObject):
        joint_states_received = Signal(object)   # sensor_msgs/JointState
        imu_received = Signal(object)            # sensor_msgs/Imu
        battery_received = Signal(object)        # sensor_msgs/BatteryState
        robot_state_received = Signal(object)    # g1_dashboard_msgs/RobotState
        safety_received = Signal(object)         # g1_dashboard_msgs/SafetyStatus
        camera_received = Signal(object)         # numpy array (BGR)
        pointcloud_received = Signal(object)     # numpy structured array

    def __init__(self):
        super().__init__('g1_dashboard')
        self.signals = self.Signals()

        self.joint_states_sub = self.create_subscription(
            JointState, '/joint_states',
            self._on_joint_states, 10)
        # ... other subscriptions

    def _on_joint_states(self, msg):
        # Called on spin thread — do NOT touch Qt widgets here
        self.signals.joint_states_received.emit(msg)
```

Panels connect to these signals:
```python
class JointControlPanel(QDockWidget):
    def __init__(self, node: DashboardNode):
        super().__init__("Joint Control")
        node.signals.joint_states_received.connect(self._update_joint_display)

    def _update_joint_display(self, msg: JointState):
        # Called on main thread via Qt signal — safe to update widgets
        for i, pos in enumerate(msg.position):
            self.sliders[i].setValue(pos)
```

---

## 8. Custom Message Definitions

### JointCommand.msg
```
uint8 joint_index           # 0-28 (see Appendix A)
float64 target_position     # radians
float64 target_velocity     # rad/s (0.0 for position-only)
float64 kp                  # proportional gain
float64 kd                  # derivative gain
float64 feedforward_torque  # N.m (0.0 for PD-only)
```

### RobotState.msg
```
std_msgs/Header header
uint8 mode                  # 0=unknown, 1=idle, 2=standing, 3=walking, 4=lowlevel, 5=damping, 6=emergency
uint32[] error_codes
float32[29] motor_temperatures   # Celsius per motor
float32[4] foot_forces           # N per foot contact sensor
string mode_name                 # Human-readable mode string
```

### SafetyStatus.msg
```
std_msgs/Header header
bool limits_active               # Joint limit enforcement enabled
bool estop_active                # Emergency stop engaged
bool command_forwarding_enabled  # Commands being sent to robot
bool heartbeat_ok                # Frontend heartbeat received recently
float32 heartbeat_age            # Seconds since last heartbeat
uint32 commands_rejected         # Count of rejected commands (limit violations)
```

### EmergencyStop.srv
```
bool activate    # true = engage E-stop, false = release
---
bool success
string message
```

### SetControlMode.srv
```
uint8 mode       # Target mode (see RobotState.msg mode values)
---
bool success
string message
```

---

## 9. Configuration

### bridge_params.yaml
```yaml
g1_dashboard_bridge:
  ros__parameters:
    robot_variant: "29dof"            # "23dof" or "29dof"
    joint_state_publish_rate: 50.0    # Hz
    imu_publish_rate: 50.0            # Hz
    battery_publish_rate: 1.0         # Hz
    command_max_rate: 50.0            # Hz (throttle incoming commands)
    heartbeat_timeout: 0.5            # seconds before safety stop
    enforce_joint_limits: true
    enable_command_forwarding: true    # false = read-only mode
```

### dashboard_params.yaml
```yaml
g1_dashboard:
  ros__parameters:
    robot_variant: "29dof"
    urdf_path: ""                     # auto-resolved from resource/ if empty
    default_unit_degrees: true
    default_live_mode: false          # staged mode by default (safer)
    heartbeat_rate: 10.0              # Hz
    point_cloud_max_points: 100000
    point_cloud_color_mode: "height"  # height, intensity, distance, flat
    camera_topic: "/camera/image_raw"
    lidar_topic: "/lidar/points"
```

---

## 10. Development Phases

| Phase | Weeks | Deliverable |
|-------|-------|-------------|
| **1. Foundation** | 1-2 | ROS2 Python package scaffold, `rclpy` + PySide6 integration (`main.py`, `dashboard_node.py`, thread bridge), `QMainWindow` with `QDockWidget` layout, dark theme stylesheet, connection status indicators |
| **2. Bridge + Status** | 3-4 | `g1_dashboard_bridge` C++ node, Status panel: IMU cube (OpenGL), pyqtgraph sparklines, battery gauge, robot mode badge, motor temp heatmap, error log, topic health indicators |
| **3. Digital Twin** | 5-7 | URDF loading (`yourdfpy` + `trimesh`), OpenGL mesh rendering, forward kinematics animation at 50 Hz, orbit/pan/zoom camera, color-based joint picking with bidirectional selection |
| **4. Joint Control** | 8-9 | Joint sliders with URDF limits, command publishing via rclpy, ghost overlay, gain editor, live/staged modes, E-stop button wired to service call |
| **5. Camera + LiDAR** | 10-11 | Camera: `cv_bridge` -> `QPixmap` display, topic selector, snapshot. LiDAR: `sensor_msgs_py` -> numpy -> OpenGL VBO, color modes, point budget, decimation |
| **6. Polish + Deploy** | 12-13 | End-to-end testing with real G1, keyboard shortcuts, layout save/restore, Docker with X11 forwarding, documentation |

---

## 11. Running the System

### Prerequisites

- Ubuntu 22.04
- ROS2 Humble (`ros-humble-desktop`)
- CycloneDDS 0.10.2
- Python 3.10+ with PySide6 (`pip install PySide6 pyqtgraph pyopengl yourdfpy trimesh`)
- Network access to G1 (Ethernet, 192.168.123.x subnet)

### Development Mode

```bash
# Source ROS2 and build workspace
source /opt/ros/humble/setup.bash
cd ros2_ws && colcon build --symlink-install && source install/setup.bash

# Configure network for Unitree robot
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI='<CycloneDDS><Domain><General>
  <NetworkInterfaceAddress>enp3s0</NetworkInterfaceAddress>
</General></Domain></CycloneDDS>'

# Launch everything (bridge + dashboard)
ros2 launch g1_dashboard dashboard.launch.py robot_model:=g1_29dof_rev_1_0
```

Or run dashboard separately:
```bash
# Terminal 1: Bridge
ros2 launch g1_dashboard_bridge bridge_only.launch.py

# Terminal 2: Dashboard
ros2 run g1_dashboard dashboard
```

### Testing Without a Robot

```bash
# Fake joint states
ros2 topic pub /joint_states sensor_msgs/msg/JointState \
  "{header: {stamp: {sec: 0}}, name: ['left_hip_pitch_joint'], position: [0.5]}" --rate 50

# Interactive GUI with URDF (joint_state_publisher_gui)
ros2 launch g1_dashboard dashboard_only.launch.py use_joint_state_publisher_gui:=true

# Rosbag playback
ros2 bag play g1_recording/
```

### Docker (with X11 forwarding)

```bash
docker build -t g1-dashboard .
xhost +local:docker
docker run -it --rm \
  --net=host \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  g1-dashboard
```

### Network Setup

```bash
sudo ip addr add 192.168.123.99/24 dev enp3s0
sudo ip link set enp3s0 up
ping 192.168.123.161  # verify robot reachable
```

---

## Appendix A: G1 Joint Index Reference

| Index | URDF Joint Name | Group | Limits (rad) |
|-------|----------------|-------|--------------|
| 0 | left_hip_pitch_joint | Left Leg | -2.5307 to 2.8798 |
| 1 | left_hip_roll_joint | Left Leg | -0.5236 to 2.9671 |
| 2 | left_hip_yaw_joint | Left Leg | -2.7576 to 2.7576 |
| 3 | left_knee_joint | Left Leg | -0.0873 to 2.8798 |
| 4 | left_ankle_pitch_joint | Left Leg | -0.8727 to 0.5236 |
| 5 | left_ankle_roll_joint | Left Leg | -0.2618 to 0.2618 |
| 6 | right_hip_pitch_joint | Right Leg | -2.5307 to 2.8798 |
| 7 | right_hip_roll_joint | Right Leg | -2.9671 to 0.5236 |
| 8 | right_hip_yaw_joint | Right Leg | -2.7576 to 2.7576 |
| 9 | right_knee_joint | Right Leg | -0.0873 to 2.8798 |
| 10 | right_ankle_pitch_joint | Right Leg | -0.8727 to 0.5236 |
| 11 | right_ankle_roll_joint | Right Leg | -0.2618 to 0.2618 |
| 12 | waist_yaw_joint | Waist | -2.618 to 2.618 |
| 13 | waist_roll_joint | Waist | -0.52 to 0.52 |
| 14 | waist_pitch_joint | Waist | -0.52 to 0.52 |
| 15 | left_shoulder_pitch_joint | Left Arm | -3.0892 to 2.6704 |
| 16 | left_shoulder_roll_joint | Left Arm | -1.5882 to 2.2515 |
| 17 | left_shoulder_yaw_joint | Left Arm | -2.618 to 2.618 |
| 18 | left_elbow_joint | Left Arm | -1.0472 to 2.0944 |
| 19 | left_wrist_roll_joint | Left Arm | -1.9722 to 1.9722 |
| 20 | left_wrist_pitch_joint | Left Arm | -1.6144 to 1.6144 |
| 21 | left_wrist_yaw_joint | Left Arm | -1.6144 to 1.6144 |
| 22 | right_shoulder_pitch_joint | Right Arm | -3.0892 to 2.6704 |
| 23 | right_shoulder_roll_joint | Right Arm | -2.2515 to 1.5882 |
| 24 | right_shoulder_yaw_joint | Right Arm | -2.618 to 2.618 |
| 25 | right_elbow_joint | Right Arm | -1.0472 to 2.0944 |
| 26 | right_wrist_roll_joint | Right Arm | -1.9722 to 1.9722 |
| 27 | right_wrist_pitch_joint | Right Arm | -1.6144 to 1.6144 |
| 28 | right_wrist_yaw_joint | Right Arm | -1.6144 to 1.6144 |

**Note**: For the 23 DOF variant, joints 13-14 (waist roll/pitch) and 19-21, 26-28 (wrist roll/pitch/yaw) are locked and should not be commanded.

---

## Appendix B: Design Rationale

1. **PySide6 + rclpy vs. web frontend**: Eliminates `rosbridge_suite`, `web_video_server`, and WebSocket serialization. The dashboard subscribes directly to ROS2 topics with zero translation overhead. Simpler architecture, lower latency, fewer moving parts.

2. **Custom bridge node vs. raw unitree_hg in Python**: Unitree messages are proprietary C++ types. The C++ bridge translates at 500 Hz with minimal overhead. The Python dashboard receives clean `sensor_msgs` at 50 Hz.

3. **QDockWidget vs. custom panel layout**: Qt's native dock system provides drag, undock to floating window, tabify, resize, and state save/restore out of the box. No third-party layout library needed.

4. **yourdfpy + trimesh vs. other URDF renderers**: `yourdfpy` provides both URDF parsing and forward kinematics computation. `trimesh` handles all mesh formats (STL, DAE, OBJ). Together they avoid heavyweight dependencies like PyBullet or RViz.

5. **pyqtgraph vs. matplotlib**: `pyqtgraph` is designed for real-time data — it handles 50 Hz updates without frame drops. Matplotlib is not suited for live streaming data.

6. **OpenGL via QOpenGLWidget vs. VTK**: VTK is powerful but heavyweight (~500MB). `QOpenGLWidget` + `PyOpenGL` gives direct GPU access with full control over rendering, at a fraction of the dependency size.

7. **sensor_msgs_py for PointCloud2**: Provides `read_points_numpy()` which decodes PointCloud2 binary data directly to numpy structured arrays. Much faster and simpler than manual `struct.unpack` loops.
