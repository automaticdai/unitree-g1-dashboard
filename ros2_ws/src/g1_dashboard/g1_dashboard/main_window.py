"""Main application window with dockable panels.

Phase 6 additions:
- Keyboard shortcuts (E-Stop, Send, Reset, Home, panel toggles, reset view).
- Layout save/restore via QSettings, with menu actions for named layouts.
"""

from PySide6.QtWidgets import (
    QMainWindow, QStatusBar, QLabel, QHBoxLayout, QWidget, QMenu,
    QInputDialog, QMessageBox,
)
from PySide6.QtCore import Qt, QTimer, QSettings, QByteArray
from PySide6.QtGui import QAction, QKeySequence, QShortcut

from g1_dashboard.dashboard_node import DashboardNode
from g1_dashboard.panels.digital_twin_panel import DigitalTwinPanel
from g1_dashboard.panels.joint_control_panel import JointControlPanel
from g1_dashboard.panels.status_panel import StatusPanel
from g1_dashboard.panels.camera_panel import CameraPanel
from g1_dashboard.panels.lidar_panel import LidarPanel
from g1_dashboard.widgets.topic_indicator import TopicIndicator
from g1_dashboard.config.ros_config import Topics


SETTINGS_ORG = 'unitree-g1-dashboard'
SETTINGS_APP = 'g1_dashboard'
LAYOUT_KEY_GEOMETRY = 'mainwindow/geometry'
LAYOUT_KEY_STATE = 'mainwindow/state'
NAMED_LAYOUTS_KEY = 'layouts/named'


class MainWindow(QMainWindow):
    """Main dashboard window."""

    def __init__(self, node: DashboardNode):
        super().__init__()
        self._node = node
        self._settings = QSettings(SETTINGS_ORG, SETTINGS_APP)

        self.setWindowTitle('Unitree G1 Dashboard')
        self.setMinimumSize(1280, 720)
        self.resize(1600, 900)

        self._setup_panels()
        self._setup_menu_bar()
        self._setup_status_bar()
        self._setup_shortcuts()

        if not self._restore_layout():
            self._arrange_default_layout()

    def _setup_panels(self) -> None:
        self.digital_twin = DigitalTwinPanel(self._node)
        self.digital_twin.setObjectName('DigitalTwinPanel')
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.digital_twin)

        self.joint_control = JointControlPanel(self._node)
        self.joint_control.setObjectName('JointControlPanel')
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.joint_control)

        self.status = StatusPanel(self._node)
        self.status.setObjectName('StatusPanel')
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.status)

        self.camera = CameraPanel(self._node)
        self.camera.setObjectName('CameraPanel')
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.camera)

        self.lidar = LidarPanel(self._node)
        self.lidar.setObjectName('LidarPanel')
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.lidar)

    def _setup_menu_bar(self) -> None:
        menu_bar = self.menuBar()

        view_menu = menu_bar.addMenu('&View')
        for panel in self._all_panels():
            view_menu.addAction(panel.toggleViewAction())

        layout_menu = menu_bar.addMenu('&Layout')
        layout_menu.addAction('Reset to &Default', self._arrange_default_layout)
        layout_menu.addAction('&Save Current...', self._save_named_layout)
        self._load_layout_menu = layout_menu.addMenu('&Load')
        layout_menu.addAction('&Manage...', self._manage_layouts)
        self._refresh_layout_menu()

        help_menu = menu_bar.addMenu('&Help')
        help_menu.addAction('&Shortcuts', self._show_shortcuts)

    def _setup_status_bar(self) -> None:
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        self._ros_status_label = QLabel('ROS2: starting...')
        status_bar.addWidget(self._ros_status_label)

        self._topic_indicators: dict[str, TopicIndicator] = {}
        indicator_container = QWidget()
        indicator_layout = QHBoxLayout(indicator_container)
        indicator_layout.setContentsMargins(0, 0, 0, 0)
        indicator_layout.setSpacing(12)

        topic_labels = {
            Topics.JOINT_STATES: 'Joints',
            Topics.IMU: 'IMU',
            Topics.BATTERY: 'Battery',
            Topics.CAMERA_IMAGE: 'Camera',
            Topics.LIDAR_POINTS: 'LiDAR',
        }
        for topic, label in topic_labels.items():
            indicator = TopicIndicator(label)
            self._topic_indicators[topic] = indicator
            indicator_layout.addWidget(indicator)

        status_bar.addPermanentWidget(indicator_container)

        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._update_status)
        self._status_timer.start(1000)

    def _setup_shortcuts(self) -> None:
        # Each binding: (key, slot, label).
        bindings = [
            ('Space',     self._shortcut_estop,         'Emergency stop'),
            ('Ctrl+Return', self._shortcut_send,        'Send commands'),
            ('Ctrl+R',    self._shortcut_reset,         'Reset commands to current'),
            ('Ctrl+H',    self._shortcut_home,          'Home pose'),
            ('Ctrl+L',    self._shortcut_toggle_live,   'Toggle live-send mode'),
            ('F2',        lambda: self._toggle_panel(self.digital_twin),  'Toggle Digital Twin'),
            ('F3',        lambda: self._toggle_panel(self.joint_control), 'Toggle Joint Control'),
            ('F4',        lambda: self._toggle_panel(self.status),        'Toggle Status'),
            ('F5',        lambda: self._toggle_panel(self.camera),        'Toggle Camera'),
            ('F6',        lambda: self._toggle_panel(self.lidar),         'Toggle LiDAR'),
            ('Ctrl+0',    self._reset_3d_view,          'Reset 3D view'),
        ]
        self._shortcuts: list[tuple[str, str]] = []
        for key, slot, label in bindings:
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(slot)
            self._shortcuts.append((key, label))

    # --- Layout management ---

    def _all_panels(self) -> list:
        return [self.digital_twin, self.joint_control, self.status,
                self.camera, self.lidar]

    def _arrange_default_layout(self) -> None:
        for panel in self._all_panels():
            panel.setVisible(True)
            panel.setFloating(False)

        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.digital_twin)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.joint_control)
        self.splitDockWidget(self.joint_control, self.status, Qt.Orientation.Vertical)
        self.splitDockWidget(self.digital_twin, self.camera, Qt.Orientation.Vertical)
        self.tabifyDockWidget(self.camera, self.lidar)
        self.camera.raise_()

    def _restore_layout(self) -> bool:
        geom = self._settings.value(LAYOUT_KEY_GEOMETRY)
        state = self._settings.value(LAYOUT_KEY_STATE)
        if isinstance(geom, QByteArray) and isinstance(state, QByteArray):
            self.restoreGeometry(geom)
            self.restoreState(state)
            return True
        return False

    def _save_named_layout(self) -> None:
        name, ok = QInputDialog.getText(self, 'Save Layout', 'Layout name:')
        if not ok or not name.strip():
            return
        layouts = self._named_layouts()
        layouts[name.strip()] = bytes(self.saveState())
        self._settings.beginGroup(NAMED_LAYOUTS_KEY)
        for k, v in layouts.items():
            self._settings.setValue(k, QByteArray(v))
        self._settings.endGroup()
        self._refresh_layout_menu()

    def _named_layouts(self) -> dict[str, bytes]:
        result: dict[str, bytes] = {}
        self._settings.beginGroup(NAMED_LAYOUTS_KEY)
        for k in self._settings.childKeys():
            v = self._settings.value(k)
            if isinstance(v, QByteArray):
                result[k] = bytes(v)
        self._settings.endGroup()
        return result

    def _refresh_layout_menu(self) -> None:
        self._load_layout_menu.clear()
        layouts = self._named_layouts()
        if not layouts:
            empty = self._load_layout_menu.addAction('(none saved)')
            empty.setEnabled(False)
            return
        for name in sorted(layouts):
            self._load_layout_menu.addAction(
                name, lambda n=name: self._load_named_layout(n))

    def _load_named_layout(self, name: str) -> None:
        layouts = self._named_layouts()
        data = layouts.get(name)
        if data is not None:
            self.restoreState(QByteArray(data))

    def _manage_layouts(self) -> None:
        layouts = self._named_layouts()
        if not layouts:
            QMessageBox.information(self, 'Layouts', 'No named layouts saved yet.')
            return
        items = list(sorted(layouts))
        name, ok = QInputDialog.getItem(
            self, 'Delete Layout', 'Pick a layout to delete:', items, 0, False)
        if not ok:
            return
        self._settings.beginGroup(NAMED_LAYOUTS_KEY)
        self._settings.remove(name)
        self._settings.endGroup()
        self._refresh_layout_menu()

    # --- Shortcut slots ---

    def _shortcut_estop(self) -> None:
        self.joint_control._on_estop_clicked()

    def _shortcut_send(self) -> None:
        self.joint_control._on_send_clicked()

    def _shortcut_reset(self) -> None:
        self.joint_control._on_reset_clicked()

    def _shortcut_home(self) -> None:
        self.joint_control._on_home_clicked()

    def _shortcut_toggle_live(self) -> None:
        cb = self.joint_control._live_mode
        cb.setChecked(not cb.isChecked())

    def _toggle_panel(self, panel) -> None:
        panel.setVisible(not panel.isVisible())

    def _reset_3d_view(self) -> None:
        gl = getattr(self.digital_twin, '_gl_widget', None)
        if gl is not None:
            gl.reset_view()

    def _show_shortcuts(self) -> None:
        rows = '\n'.join(f'  {k:<14}  {label}' for k, label in self._shortcuts)
        QMessageBox.information(self, 'Keyboard Shortcuts', f'Shortcuts:\n\n{rows}')

    # --- Periodic ---

    def _update_status(self) -> None:
        self._ros_status_label.setText('ROS2: active')
        for topic, indicator in self._topic_indicators.items():
            age = self._node.get_topic_age(topic)
            if age is None:
                indicator.set_status('inactive')
            elif age < 2.0:
                indicator.set_status('active')
            elif age < 5.0:
                indicator.set_status('stale')
            else:
                indicator.set_status('inactive')

    def closeEvent(self, event) -> None:
        self._settings.setValue(LAYOUT_KEY_GEOMETRY, self.saveGeometry())
        self._settings.setValue(LAYOUT_KEY_STATE, self.saveState())
        self._status_timer.stop()
        super().closeEvent(event)
