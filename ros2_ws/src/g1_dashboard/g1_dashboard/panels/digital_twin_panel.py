"""Digital Twin panel — 3D stick-figure robot driven by joint states."""

from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
)
from PySide6.QtCore import Qt

from g1_dashboard.config.robot_config import JOINT_BY_NAME
from g1_dashboard.dashboard_node import DashboardNode


class DigitalTwinPanel(QDockWidget):
    """3D viewport showing the G1 robot driven by /joint_states.

    Uses the stick-figure renderer (no URDF meshes required). If PyOpenGL
    is unavailable, falls back to a placeholder label.
    """

    def __init__(self, node: DashboardNode, parent=None):
        super().__init__('Digital Twin', parent)
        self._node = node
        self._current_positions: list[float] = [0.0] * 29

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel('Drag: orbit | Right: pan | Scroll: zoom | Double-middle: reset'))
        toolbar.addStretch()

        reset_btn = QPushButton('Reset View')
        reset_btn.setMaximumWidth(100)
        toolbar.addWidget(reset_btn)
        layout.addLayout(toolbar)

        # GL viewport (with fallback)
        self._gl_widget = None
        viewport = self._create_viewport(reset_btn)
        layout.addWidget(viewport, stretch=1)

        self.setWidget(container)

        # Subscribe to joint states
        self._node.signals.joint_states_received.connect(self._on_joint_states)
        # React to selection changes from other panels
        self._node.selection.selection_changed.connect(self._on_selection)

    def _create_viewport(self, reset_btn: QPushButton) -> QWidget:
        try:
            from g1_dashboard.rendering.gl_widget import DigitalTwinGLWidget
        except ImportError as exc:
            placeholder = QLabel(
                '3D Digital Twin unavailable\n\n'
                f'Reason: {exc}\n\n'
                'Install PyOpenGL (pip install PyOpenGL PyOpenGL_accelerate) '
                'and PySide6 with OpenGL support to enable the viewport.')
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet(
                'color: #888; font-size: 13px; border: 1px dashed #444; '
                'padding: 20px; min-height: 300px;')
            reset_btn.setEnabled(False)
            return placeholder

        self._gl_widget = DigitalTwinGLWidget()
        self._gl_widget.joint_picked.connect(self._on_joint_picked)
        reset_btn.clicked.connect(self._gl_widget.reset_view)
        return self._gl_widget

    # --- Signal handlers ---

    def _on_joint_states(self, msg) -> None:
        """Map incoming JointState names to our 29-index vector and update FK."""
        if self._gl_widget is None:
            return
        positions = list(self._current_positions)
        for name, pos in zip(msg.name, msg.position):
            joint = JOINT_BY_NAME.get(name)
            if joint is not None:
                positions[joint.index] = float(pos)
        self._current_positions = positions
        self._gl_widget.update_joint_positions(positions)

    def _on_joint_picked(self, index: int) -> None:
        """A joint was clicked in the 3D viewport — update shared selection."""
        self._node.selection.set_selected(None if index < 0 else index)

    def _on_selection(self, index: int) -> None:
        """Shared selection changed (from any panel) — update our highlight."""
        if self._gl_widget is None:
            return
        self._gl_widget.set_selected_joint(None if index < 0 else index)
