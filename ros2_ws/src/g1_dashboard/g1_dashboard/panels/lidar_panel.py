"""LiDAR panel — point cloud visualization with OpenGL."""

from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QLabel, QHBoxLayout,
    QComboBox, QSlider, QSpinBox,
)
from PySide6.QtCore import Qt

from g1_dashboard.dashboard_node import DashboardNode


class LidarPanel(QDockWidget):
    """Panel for 3D point cloud visualization.

    Phase 1: Placeholder widget.
    Phase 5: Full OpenGL point cloud rendering with color modes.
    """

    def __init__(self, node: DashboardNode, parent=None):
        super().__init__('LiDAR', parent)
        self._node = node

        container = QWidget()
        layout = QVBoxLayout(container)

        # Controls bar
        controls = QHBoxLayout()

        controls.addWidget(QLabel('Color:'))
        self._color_mode = QComboBox()
        self._color_mode.addItems(['Height (Z)', 'Intensity', 'Distance', 'Flat'])
        controls.addWidget(self._color_mode)

        controls.addWidget(QLabel('Pt Size:'))
        self._point_size = QSlider(Qt.Orientation.Horizontal)
        self._point_size.setRange(1, 5)
        self._point_size.setValue(2)
        self._point_size.setFixedWidth(80)
        controls.addWidget(self._point_size)

        controls.addWidget(QLabel('Budget:'))
        self._point_budget = QSpinBox()
        self._point_budget.setRange(10000, 500000)
        self._point_budget.setValue(100000)
        self._point_budget.setSingleStep(10000)
        self._point_budget.setSuffix(' pts')
        controls.addWidget(self._point_budget)

        controls.addStretch()
        layout.addLayout(controls)

        # Placeholder — will be replaced by QOpenGLWidget in Phase 5
        placeholder = QLabel('3D Point Cloud\n(OpenGL viewport — Phase 5)')
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet(
            'color: #888; font-size: 16px; border: 1px dashed #444; '
            'min-height: 240px;'
        )
        layout.addWidget(placeholder, stretch=1)

        self.setWidget(container)

        # Connect to point cloud updates
        self._node.signals.pointcloud_received.connect(self._on_pointcloud)

    def _on_pointcloud(self, msg) -> None:
        """Handle incoming point cloud — will render in Phase 5."""
        pass
