"""Camera panel — live image display from ROS2 Image topics."""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QLabel, QHBoxLayout,
    QPushButton, QComboBox, QFileDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap

from g1_dashboard.dashboard_node import DashboardNode


def msg_to_qimage(msg) -> QImage | None:
    """Convert a sensor_msgs/Image (or CompressedImage) to QImage.

    Tries cv_bridge first; falls back to manual decoding for common
    raw encodings so the panel still works in environments without
    cv_bridge installed.
    """
    encoding = getattr(msg, 'encoding', None)
    if encoding is None and hasattr(msg, 'format'):
        # CompressedImage path
        try:
            import cv2
            import numpy as np
            arr = np.frombuffer(bytes(msg.data), dtype=np.uint8)
            cv_img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if cv_img is None:
                return None
            h, w = cv_img.shape[:2]
            return QImage(
                cv_img.tobytes(), w, h, cv_img.strides[0],
                QImage.Format.Format_BGR888,
            ).copy()
        except ImportError:
            return None

    try:
        from cv_bridge import CvBridge
        bridge = CvBridge()
        cv_img = bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        h, w = cv_img.shape[:2]
        return QImage(
            cv_img.tobytes(), w, h, cv_img.strides[0],
            QImage.Format.Format_BGR888,
        ).copy()
    except ImportError:
        pass

    # Manual fallback for the simplest raw encodings
    h = msg.height
    w = msg.width
    step = msg.step
    data = bytes(msg.data) if not isinstance(msg.data, bytes) else msg.data
    if encoding == 'rgb8':
        fmt = QImage.Format.Format_RGB888
    elif encoding == 'bgr8':
        fmt = QImage.Format.Format_BGR888
    elif encoding in ('mono8', '8UC1'):
        fmt = QImage.Format.Format_Grayscale8
    else:
        return None
    return QImage(data, w, h, step, fmt).copy()


class CameraPanel(QDockWidget):
    """Live camera image with snapshot and FPS counter."""

    def __init__(self, node: DashboardNode, parent=None):
        super().__init__('Camera', parent)
        self._node = node
        self._last_pixmap: QPixmap | None = None

        container = QWidget()
        layout = QVBoxLayout(container)

        controls = QHBoxLayout()
        self._topic_combo = QComboBox()
        self._topic_combo.addItem('/camera/image_raw')
        self._topic_combo.addItem('/camera/image_raw/compressed')
        self._topic_combo.setMinimumWidth(220)
        controls.addWidget(QLabel('Topic:'))
        controls.addWidget(self._topic_combo)
        controls.addStretch()

        self._fps_label = QLabel('FPS: --')
        self._fps_label.setStyleSheet('font-family: monospace; font-size: 11px;')
        controls.addWidget(self._fps_label)

        snapshot_btn = QPushButton('Snapshot')
        snapshot_btn.clicked.connect(self._on_snapshot)
        controls.addWidget(snapshot_btn)

        layout.addLayout(controls)

        self._image_label = QLabel('No Signal')
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setStyleSheet(
            'color: #666; font-size: 18px; background-color: #111; min-height: 240px;'
        )
        self._image_label.setMinimumSize(320, 240)
        self._image_label.setScaledContents(False)
        layout.addWidget(self._image_label, stretch=1)

        self.setWidget(container)

        # FPS state
        self._frame_times: list[float] = []

        self._node.signals.camera_received.connect(self._on_camera)

    # --- Slots ---

    def _on_camera(self, msg) -> None:
        qimg = msg_to_qimage(msg)
        if qimg is None or qimg.isNull():
            return
        pix = QPixmap.fromImage(qimg)
        self._last_pixmap = pix
        self._image_label.setPixmap(self._scaled_pixmap(pix))
        self._tick_fps()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._last_pixmap is not None:
            self._image_label.setPixmap(self._scaled_pixmap(self._last_pixmap))

    def _scaled_pixmap(self, pix: QPixmap) -> QPixmap:
        return pix.scaled(
            self._image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def _tick_fps(self) -> None:
        now = time.monotonic()
        self._frame_times.append(now)
        # Keep only the last 1 second of timestamps
        cutoff = now - 1.0
        self._frame_times = [t for t in self._frame_times if t >= cutoff]
        self._fps_label.setText(f'FPS: {len(self._frame_times):3d}')

    def _on_snapshot(self) -> None:
        if self._last_pixmap is None:
            return
        default = Path.home() / f'g1_snapshot_{datetime.now():%Y%m%d_%H%M%S}.png'
        path, _ = QFileDialog.getSaveFileName(
            self, 'Save snapshot', str(default), 'PNG (*.png);;JPEG (*.jpg)')
        if not path:
            return
        self._last_pixmap.save(path)
