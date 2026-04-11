"""Camera panel — live image display from ROS2 Image topics."""

from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QLabel, QHBoxLayout,
    QPushButton, QComboBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap

from g1_dashboard.dashboard_node import DashboardNode


class CameraPanel(QDockWidget):
    """Panel displaying live camera images from ROS2 Image topics.

    Phase 1: Placeholder with "No Signal".
    Phase 5: Full cv_bridge image conversion and display.
    """

    def __init__(self, node: DashboardNode, parent=None):
        super().__init__('Camera', parent)
        self._node = node

        container = QWidget()
        layout = QVBoxLayout(container)

        # Controls bar
        controls = QHBoxLayout()
        self._topic_combo = QComboBox()
        self._topic_combo.addItem('/camera/image_raw')
        self._topic_combo.setMinimumWidth(200)
        controls.addWidget(QLabel('Topic:'))
        controls.addWidget(self._topic_combo)
        controls.addStretch()

        self._fps_label = QLabel('FPS: --')
        self._fps_label.setStyleSheet('font-family: monospace; font-size: 11px;')
        controls.addWidget(self._fps_label)

        snapshot_btn = QPushButton('Snapshot')
        controls.addWidget(snapshot_btn)
        layout.addLayout(controls)

        # Image display
        self._image_label = QLabel('No Signal')
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setStyleSheet(
            'color: #666; font-size: 18px; background-color: #111; min-height: 240px;'
        )
        self._image_label.setScaledContents(False)
        layout.addWidget(self._image_label, stretch=1)

        self.setWidget(container)

        # Frame counter for FPS
        self._frame_count = 0
        self._last_fps_time = 0.0

        # Connect to camera updates
        self._node.signals.camera_received.connect(self._on_camera)

    def _on_camera(self, msg) -> None:
        """Convert ROS Image to QPixmap and display.

        Full implementation in Phase 5 with cv_bridge.
        """
        pass
