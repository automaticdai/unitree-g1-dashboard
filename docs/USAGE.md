# Dashboard Usage

## Launch

```bash
source /opt/ros/humble/setup.bash
cd ros2_ws && colcon build --symlink-install && source install/setup.bash
ros2 run g1_dashboard dashboard
```

For hardware-free testing, run the simulator in another terminal:

```bash
ros2 run g1_dashboard simulator
```

## Panels

| Panel | What it shows |
|-------|---------------|
| Digital Twin | 3D stick-figure G1, driven by `/joint_states`. Click joints to select. Ghost overlay (orange) shows the commanded pose when at least one joint is dirty. |
| Joint Control | 29 sliders + spinboxes. Per-joint dirty tracking. Live or staged sending. Gain editor for the selected joint. E-stop calls the `/emergency_stop` service. |
| Status | Battery gauge, motor temperature heatmap, IMU/state plots, topic health. |
| Camera | `/camera/image_raw` or `/camera/image_raw/compressed` via cv_bridge. Snapshot saves PNG. FPS shown in the top right. |
| LiDAR | OpenGL point cloud from `/lidar/points`. Color modes: Height (Z), Intensity, Distance, Flat. Distance filter and accumulate-N-frames mode for sparse LiDARs. |

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Emergency stop |
| `Ctrl+Enter` | Send queued joint commands |
| `Ctrl+R` | Reset commands to current pose |
| `Ctrl+H` | Home pose (zero all joints) |
| `Ctrl+L` | Toggle live-send mode |
| `Ctrl+0` | Reset 3D camera view |
| `F2`..`F6` | Toggle Digital Twin / Joint Control / Status / Camera / LiDAR panels |

`Help → Shortcuts` re-prints this list inside the app.

## Layouts

- The current dock layout is saved on close and restored on next launch.
- `Layout → Save Current...` saves the current arrangement under a name; `Layout → Load` lists saved layouts. `Layout → Manage...` deletes one.
- `Layout → Reset to Default` re-applies the built-in 2x2 arrangement.

Layouts are stored via `QSettings` (Linux: `~/.config/unitree-g1-dashboard/g1_dashboard.conf`).

## Joint Control Workflow

1. **Live mode** publishes a `JointCommand` on every slider edit. Use it for tuning a single joint at a time.
2. **Staged mode** (default) lets you adjust multiple joints, then `Ctrl+Enter` (or *Send*) publishes one command per dirty joint.
3. **Reset** (`Ctrl+R`) clears the dirty flag on all joints and snaps commands back to the current state — the ghost overlay disappears.
4. **Home** (`Ctrl+H`) commands the zero pose. In staged mode you still need *Send* to publish.
5. **E-Stop** (`Space`) calls the `/emergency_stop` service. The bridge is expected to engage damping mode on receipt.

## Gain Editor

The footer of the Joint Control panel shows the selected joint's `kp`/`kd` and a preset dropdown:

- **Default** = 1.0× / 1.0× of the per-joint defaults in `robot_config.py`.
- **Stiff** = 1.5× kp, 1.2× kd.
- **Compliant** = 0.3× kp, 0.8× kd.
- **Custom** is auto-selected when you edit either spinbox directly.

Overrides are per-joint and applied on every `JointCommand` you publish.

## Docker

See [README.md](../README.md#docker) for the X11-forwarded run command.
