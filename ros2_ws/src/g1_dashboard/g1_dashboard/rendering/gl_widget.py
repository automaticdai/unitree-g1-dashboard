"""QOpenGLWidget scene for the digital twin viewport.

Uses legacy OpenGL (fixed-function pipeline) for simplicity. Fine for the
target polygon count (~30 spheres + 30 cylinders).
"""

from __future__ import annotations

import numpy as np

from OpenGL import GL

from PySide6.QtCore import Qt, Signal, QPoint, QTimer
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from g1_dashboard.rendering.camera_controller import CameraController
from g1_dashboard.rendering.grid_renderer import draw_grid, draw_axes
from g1_dashboard.rendering.robot_renderer import RobotRenderer, RenderOptions
from g1_dashboard.utils.kinematics import FKResult, RobotSkeleton, zero_pose


class DigitalTwinGLWidget(QOpenGLWidget):
    """OpenGL viewport showing the G1 robot driven by joint angles."""

    joint_picked = Signal(int)     # Emitted when a joint is clicked (-1 = cleared)

    def __init__(self, skeleton: RobotSkeleton | None = None, parent=None):
        super().__init__(parent)
        self._skeleton = skeleton or RobotSkeleton()
        self._renderer: RobotRenderer | None = None
        self._camera = CameraController()
        self._fk: FKResult = self._skeleton.compute_fk(zero_pose())
        self._ghost_fk: FKResult | None = None
        self._selected_joint: int | None = None

        # Mouse interaction state
        self._last_mouse_pos: QPoint | None = None
        self._drag_button: Qt.MouseButton | None = None

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(320, 240)

        # Throttle repaints — re-render at ~30 FPS max even if joint states
        # arrive at 50 Hz.
        self._dirty = False
        self._redraw_timer = QTimer(self)
        self._redraw_timer.timeout.connect(self._maybe_update)
        self._redraw_timer.start(33)

    # --- Public API ---

    def update_joint_positions(self, positions: list[float]) -> None:
        """Recompute FK from a list of joint angles and schedule a redraw."""
        self._fk = self._skeleton.compute_fk(positions)
        self._dirty = True

    def set_commanded_pose(self, positions: list[float] | None) -> None:
        """Set the commanded (ghost) pose. Pass None to hide the ghost."""
        if positions is None:
            if self._ghost_fk is not None:
                self._ghost_fk = None
                self._dirty = True
            return
        self._ghost_fk = self._skeleton.compute_fk(positions)
        self._dirty = True

    def set_selected_joint(self, joint_index: int | None) -> None:
        if joint_index != self._selected_joint:
            self._selected_joint = joint_index
            self._dirty = True

    def reset_view(self) -> None:
        self._camera.reset()
        self._dirty = True

    # --- Qt OpenGL lifecycle ---

    def initializeGL(self) -> None:
        GL.glClearColor(0.12, 0.12, 0.14, 1.0)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_CULL_FACE)
        GL.glCullFace(GL.GL_BACK)

        # Light setup
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_POSITION, [5.0, 5.0, 10.0, 1.0])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, [0.9, 0.9, 0.9, 1.0])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])

        self._renderer = RobotRenderer(self._skeleton, RenderOptions())

    def resizeGL(self, w: int, h: int) -> None:
        GL.glViewport(0, 0, w, h)

    def paintGL(self) -> None:
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

        # Projection
        proj = self._camera.projection_matrix(self.width() / max(self.height(), 1))
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadMatrixf(proj.T.astype(np.float32))

        # View
        view = self._camera.view_matrix()
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadMatrixf(view.T.astype(np.float32))

        draw_grid()
        draw_axes()
        if self._renderer is not None:
            self._renderer.draw(self._fk, selected_joint=self._selected_joint)
            if self._ghost_fk is not None:
                self._renderer.draw_ghost(self._ghost_fk)

    # --- Mouse input ---

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._last_mouse_pos = event.pos()
        self._drag_button = event.button()
        # Click-to-pick on press (not on release) feels more responsive
        if event.button() == Qt.MouseButton.LeftButton:
            # Tentative click — actual pick happens in mouseReleaseEvent
            # if the mouse didn't move (to avoid picking during orbit)
            self._press_pos = event.pos()

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
        # Pick only on a click (no drag)
        if (event.button() == Qt.MouseButton.LeftButton
                and getattr(self, '_press_pos', None) is not None):
            dx = event.pos().x() - self._press_pos.x()
            dy = event.pos().y() - self._press_pos.y()
            if abs(dx) < 3 and abs(dy) < 3:
                self._pick_at(event.pos().x(), event.pos().y())
        self._press_pos = None
        self._last_mouse_pos = None
        self._drag_button = None

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y() / 120.0
        self._camera.zoom(delta)
        self._dirty = True
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self.reset_view()

    # --- Picking ---

    def _pick_at(self, x: int, y: int) -> None:
        if self._renderer is None:
            return
        origin, direction = self._camera.screen_to_ray(
            float(x), float(y), self.width(), self.height())
        picked = self._renderer.pick_joint(self._fk, origin, direction)
        if picked is None:
            self.joint_picked.emit(-1)
        else:
            self.joint_picked.emit(picked)

    # --- Timer ---

    def _maybe_update(self) -> None:
        if self._dirty:
            self._dirty = False
            self.update()
