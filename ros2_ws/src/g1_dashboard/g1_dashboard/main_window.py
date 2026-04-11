"""Main application window with dockable panels."""

from PySide6.QtWidgets import (
    QMainWindow, QStatusBar, QLabel, QHBoxLayout, QWidget, QMenuBar, QMenu,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction

from g1_dashboard.dashboard_node import DashboardNode
from g1_dashboard.panels.digital_twin_panel import DigitalTwinPanel
from g1_dashboard.panels.joint_control_panel import JointControlPanel
from g1_dashboard.panels.status_panel import StatusPanel
from g1_dashboard.panels.camera_panel import CameraPanel
from g1_dashboard.panels.lidar_panel import LidarPanel
from g1_dashboard.widgets.topic_indicator import TopicIndicator
from g1_dashboard.config.ros_config import Topics


class MainWindow(QMainWindow):
    """Main dashboard window with dockable panels and status bar."""

    def __init__(self, node: DashboardNode):
        super().__init__()
        self._node = node

        self.setWindowTitle('Unitree G1 Dashboard')
        self.setMinimumSize(1280, 720)
        self.resize(1600, 900)

        self._setup_menu_bar()
        self._setup_panels()
        self._setup_status_bar()
        self._arrange_default_layout()

    def _setup_menu_bar(self) -> None:
        menu_bar = self.menuBar()

        # View menu — toggle panel visibility
        view_menu = menu_bar.addMenu('&View')
        self._panel_actions: list[QAction] = []
        # Populated after panels are created

        # Layout menu
        layout_menu = menu_bar.addMenu('&Layout')
        reset_action = layout_menu.addAction('Reset to Default')
        reset_action.triggered.connect(self._arrange_default_layout)

    def _setup_panels(self) -> None:
        """Create all dock widget panels."""

        # Digital Twin — 3D robot model
        self.digital_twin = DigitalTwinPanel(self._node)
        self.digital_twin.setObjectName('DigitalTwinPanel')
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.digital_twin)

        # Joint Control — sliders and command bar
        self.joint_control = JointControlPanel(self._node)
        self.joint_control.setObjectName('JointControlPanel')
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.joint_control)

        # Status — IMU, battery, robot state
        self.status = StatusPanel(self._node)
        self.status.setObjectName('StatusPanel')
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.status)

        # Camera — live image display
        self.camera = CameraPanel(self._node)
        self.camera.setObjectName('CameraPanel')
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.camera)

        # LiDAR — point cloud visualization
        self.lidar = LidarPanel(self._node)
        self.lidar.setObjectName('LidarPanel')
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.lidar)

        # Add view menu toggle actions for each panel
        view_menu = self.menuBar().findChild(QMenu, '', Qt.FindChildOption.FindDirectChildrenOnly)
        if view_menu is None:
            view_menu = self.menuBar().actions()[0].menu()
        for panel in [self.digital_twin, self.joint_control, self.status,
                      self.camera, self.lidar]:
            action = panel.toggleViewAction()
            view_menu.addAction(action)

    def _setup_status_bar(self) -> None:
        """Create the bottom status bar with connection indicators."""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        # ROS2 node status
        self._ros_status_label = QLabel('ROS2: starting...')
        status_bar.addWidget(self._ros_status_label)

        # Topic health indicators
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

        # Periodic status update (1 Hz)
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._update_status)
        self._status_timer.start(1000)

    def _update_status(self) -> None:
        """Update status bar indicators based on topic activity."""
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

    def _arrange_default_layout(self) -> None:
        """Arrange panels in the default 2x2-ish layout.

        Left column:  Digital Twin (top) | Camera (bottom)
        Right column: Joint Control (top) | Status (bottom)
        LiDAR tabbed with Camera
        """
        # Reset all to visible
        for panel in [self.digital_twin, self.joint_control, self.status,
                      self.camera, self.lidar]:
            panel.setVisible(True)
            panel.setFloating(False)

        # Left: Digital Twin on top
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.digital_twin)

        # Right top: Joint Control
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.joint_control)

        # Right bottom: Status (split vertically with joint control)
        self.splitDockWidget(self.joint_control, self.status, Qt.Orientation.Vertical)

        # Bottom left: Camera
        self.splitDockWidget(self.digital_twin, self.camera, Qt.Orientation.Vertical)

        # Tab LiDAR with Camera
        self.tabifyDockWidget(self.camera, self.lidar)
        self.camera.raise_()  # Show camera tab by default

    def closeEvent(self, event) -> None:
        """Clean up on window close."""
        self._status_timer.stop()
        super().closeEvent(event)
