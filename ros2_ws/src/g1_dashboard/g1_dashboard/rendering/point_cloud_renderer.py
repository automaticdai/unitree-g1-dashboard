"""Point cloud OpenGL viewport.

Renders an (N, 3) xyz array with per-point colors via legacy OpenGL
vertex/color arrays. Uses the same `CameraController` as the digital
twin viewport so navigation feels identical.
"""

from __future__ import annotations

import numpy as np

from OpenGL import GL

from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from g1_dashboard.rendering.camera_controller import CameraController
from g1_dashboard.rendering.grid_renderer import draw_grid, draw_axes


class PointCloudGLWidget(QOpenGLWidget):
    """OpenGL viewport for a single-frame XYZ+color point cloud."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._camera = CameraController()
        self._points: np.ndarray = np.zeros((0, 3), dtype=np.float32)
        self._colors: np.ndarray = np.zeros((0, 3), dtype=np.float32)
        self._point_size = 2.0

        self._dirty = False
        self._last_mouse_pos: QPoint | None = None

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(320, 240)

        self._redraw_timer = QTimer(self)
        self._redraw_timer.timeout.connect(self._maybe_update)
        self._redraw_timer.start(33)  # ~30 FPS cap

    # --- Public API ---

    def set_cloud(self, points: np.ndarray, colors: np.ndarray) -> None:
        """Replace the displayed cloud. `points` (N,3) and `colors` (N,3) float32."""
        if points.dtype != np.float32:
            points = points.astype(np.float32, copy=False)
        if colors.dtype != np.float32:
            colors = colors.astype(np.float32, copy=False)
        if points.shape[0] != colors.shape[0]:
            raise ValueError('points and colors length mismatch')
        self._points = np.ascontiguousarray(points)
        self._colors = np.ascontiguousarray(colors)
        self._dirty = True

    def set_point_size(self, size: float) -> None:
        self._point_size = float(max(1.0, size))
        self._dirty = True

    def reset_view(self) -> None:
        self._camera.reset()
        self._dirty = True

    # --- Qt OpenGL ---

    def initializeGL(self) -> None:
        GL.glClearColor(0.10, 0.10, 0.12, 1.0)
        GL.glEnable(GL.GL_DEPTH_TEST)

    def resizeGL(self, w: int, h: int) -> None:
        GL.glViewport(0, 0, w, h)

    def paintGL(self) -> None:
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

        proj = self._camera.projection_matrix(self.width() / max(self.height(), 1))
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadMatrixf(proj.T.astype(np.float32))

        view = self._camera.view_matrix()
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadMatrixf(view.T.astype(np.float32))

        draw_grid()
        draw_axes()

        n = self._points.shape[0]
        if n == 0:
            return

        GL.glPointSize(self._point_size)
        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glEnableClientState(GL.GL_COLOR_ARRAY)
        GL.glVertexPointer(3, GL.GL_FLOAT, 0, self._points)
        GL.glColorPointer(3, GL.GL_FLOAT, 0, self._colors)
        GL.glDrawArrays(GL.GL_POINTS, 0, n)
        GL.glDisableClientState(GL.GL_COLOR_ARRAY)
        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)

    # --- Mouse ---

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._last_mouse_pos = event.pos()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._last_mouse_pos is None:
            return
        dx = event.pos().x() - self._last_mouse_pos.x()
        dy = event.pos().y() - self._last_mouse_pos.y()
        self._last_mouse_pos = event.pos()
        buttons = event.buttons()
        if buttons & Qt.MouseButton.LeftButton:
            self._camera.orbit(dx, dy)
        elif buttons & Qt.MouseButton.RightButton:
            self._camera.pan(dx, dy)
        elif buttons & Qt.MouseButton.MiddleButton:
            self._camera.zoom(-dy * 0.05)
        self._dirty = True

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._last_mouse_pos = None

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y() / 120.0
        self._camera.zoom(delta)
        self._dirty = True
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self.reset_view()

    def _maybe_update(self) -> None:
        if self._dirty:
            self._dirty = False
            self.update()
