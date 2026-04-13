"""LiDAR panel — point cloud visualization with OpenGL."""

from __future__ import annotations

import numpy as np

from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QLabel, QHBoxLayout,
    QComboBox, QSlider, QSpinBox, QDoubleSpinBox, QCheckBox, QPushButton,
)
from PySide6.QtCore import Qt

from g1_dashboard.dashboard_node import DashboardNode
from g1_dashboard.utils import color_maps
from g1_dashboard.utils.point_cloud_utils import (
    decode_pointcloud2, decimate, filter_distance,
)


COLOR_MODES = ['Height (Z)', 'Intensity', 'Distance', 'Flat']


class LidarPanel(QDockWidget):
    """3D point cloud viewport with color modes and filters."""

    def __init__(self, node: DashboardNode, parent=None):
        super().__init__('LiDAR', parent)
        self._node = node
        self._gl_widget = None

        # Accumulated frames buffer (used when frame mode != latest)
        self._accum_frames: list[np.ndarray] = []
        self._accum_max = 1

        container = QWidget()
        layout = QVBoxLayout(container)

        layout.addLayout(self._build_controls())

        viewport = self._create_viewport()
        layout.addWidget(viewport, stretch=1)

        self._stats_label = QLabel('Points: 0')
        self._stats_label.setStyleSheet('font-family: monospace; color: #888;')
        layout.addWidget(self._stats_label)

        self.setWidget(container)

        self._node.signals.pointcloud_received.connect(self._on_pointcloud)

    # --- UI ---

    def _build_controls(self) -> QHBoxLayout:
        controls = QHBoxLayout()

        controls.addWidget(QLabel('Color:'))
        self._color_mode = QComboBox()
        self._color_mode.addItems(COLOR_MODES)
        controls.addWidget(self._color_mode)

        controls.addWidget(QLabel('Map:'))
        self._colormap = QComboBox()
        self._colormap.addItems(list(color_maps.COLORMAPS.keys()))
        controls.addWidget(self._colormap)

        controls.addWidget(QLabel('Pt Size:'))
        self._point_size = QSlider(Qt.Orientation.Horizontal)
        self._point_size.setRange(1, 5)
        self._point_size.setValue(2)
        self._point_size.setFixedWidth(80)
        self._point_size.valueChanged.connect(self._on_point_size)
        controls.addWidget(self._point_size)

        controls.addWidget(QLabel('Budget:'))
        self._point_budget = QSpinBox()
        self._point_budget.setRange(10000, 500000)
        self._point_budget.setValue(100000)
        self._point_budget.setSingleStep(10000)
        self._point_budget.setSuffix(' pts')
        controls.addWidget(self._point_budget)

        controls.addWidget(QLabel('Min:'))
        self._dmin = QDoubleSpinBox()
        self._dmin.setDecimals(1)
        self._dmin.setRange(0.0, 100.0)
        self._dmin.setValue(0.0)
        self._dmin.setSuffix(' m')
        controls.addWidget(self._dmin)

        controls.addWidget(QLabel('Max:'))
        self._dmax = QDoubleSpinBox()
        self._dmax.setDecimals(1)
        self._dmax.setRange(0.1, 200.0)
        self._dmax.setValue(30.0)
        self._dmax.setSuffix(' m')
        controls.addWidget(self._dmax)

        self._accumulate = QCheckBox('Accumulate')
        self._accumulate.setToolTip('Stack the last N frames instead of showing only the latest')
        self._accumulate.toggled.connect(self._on_accum_toggled)
        controls.addWidget(self._accumulate)

        self._accum_n = QSpinBox()
        self._accum_n.setRange(2, 20)
        self._accum_n.setValue(5)
        self._accum_n.setEnabled(False)
        self._accum_n.valueChanged.connect(lambda v: setattr(self, '_accum_max', v))
        controls.addWidget(self._accum_n)

        reset_btn = QPushButton('Reset View')
        reset_btn.clicked.connect(self._on_reset_view)
        controls.addWidget(reset_btn)

        controls.addStretch()
        return controls

    def _create_viewport(self) -> QWidget:
        try:
            from g1_dashboard.rendering.point_cloud_renderer import PointCloudGLWidget
        except ImportError as exc:
            placeholder = QLabel(
                f'Point cloud viewport unavailable\n\nReason: {exc}\n\n'
                'Install PyOpenGL to enable.')
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet(
                'color: #888; font-size: 13px; border: 1px dashed #444; '
                'padding: 20px; min-height: 240px;')
            return placeholder

        self._gl_widget = PointCloudGLWidget()
        return self._gl_widget

    # --- Slots ---

    def _on_point_size(self, value: int) -> None:
        if self._gl_widget is not None:
            self._gl_widget.set_point_size(float(value))

    def _on_accum_toggled(self, checked: bool) -> None:
        self._accum_n.setEnabled(checked)
        if not checked:
            self._accum_frames.clear()

    def _on_reset_view(self) -> None:
        if self._gl_widget is not None:
            self._gl_widget.reset_view()

    def _on_pointcloud(self, msg) -> None:
        if self._gl_widget is None:
            return
        try:
            points = decode_pointcloud2(msg)  # (N, 4) xyz+intensity
        except Exception as exc:
            self._node.get_logger().warn(f'PointCloud2 decode failed: {exc}')
            return
        if points.size == 0:
            return

        # Accumulate or replace
        if self._accumulate.isChecked():
            self._accum_frames.append(points)
            while len(self._accum_frames) > self._accum_max:
                self._accum_frames.pop(0)
            points = np.concatenate(self._accum_frames, axis=0)

        # Filter then decimate
        points = filter_distance(points, self._dmin.value(), self._dmax.value())
        points = decimate(points, self._point_budget.value())

        if points.shape[0] == 0:
            self._gl_widget.set_cloud(
                np.zeros((0, 3), dtype=np.float32),
                np.zeros((0, 3), dtype=np.float32))
            self._stats_label.setText('Points: 0')
            return

        xyz = np.ascontiguousarray(points[:, :3], dtype=np.float32)
        colors = self._colorize(points)
        self._gl_widget.set_cloud(xyz, colors)
        self._stats_label.setText(f'Points: {xyz.shape[0]:,}')

    # --- Coloring ---

    def _colorize(self, points: np.ndarray) -> np.ndarray:
        mode = self._color_mode.currentText()
        if mode == 'Flat':
            colors = np.empty((points.shape[0], 3), dtype=np.float32)
            colors[:] = (0.7, 0.85, 1.0)
            return colors

        if mode == 'Height (Z)':
            scalar = points[:, 2]
        elif mode == 'Intensity':
            scalar = points[:, 3]
        else:  # Distance
            scalar = np.linalg.norm(points[:, :3], axis=1)

        cmap = color_maps.COLORMAPS[self._colormap.currentText()]
        return cmap(color_maps.normalize(scalar))
