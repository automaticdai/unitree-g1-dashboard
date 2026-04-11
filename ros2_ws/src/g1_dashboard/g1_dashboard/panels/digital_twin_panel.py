"""Digital Twin panel — 3D URDF model visualization with OpenGL."""

from PySide6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

from g1_dashboard.dashboard_node import DashboardNode


class DigitalTwinPanel(QDockWidget):
    """3D viewport showing the G1 robot model driven by joint states.

    Phase 1: Placeholder widget.
    Phase 3: Full OpenGL rendering with URDF, joint animation, picking.
    """

    def __init__(self, node: DashboardNode, parent=None):
        super().__init__('Digital Twin', parent)
        self._node = node

        container = QWidget()
        layout = QVBoxLayout(container)

        # Placeholder — will be replaced by QOpenGLWidget in Phase 3
        placeholder = QLabel('3D Digital Twin\n(OpenGL viewport — Phase 3)')
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet(
            'color: #888; font-size: 16px; border: 1px dashed #444; '
            'min-height: 300px;'
        )
        layout.addWidget(placeholder)

        self.setWidget(container)

        # Connect to joint state updates (for future use)
        self._node.signals.joint_states_received.connect(self._on_joint_states)

    def _on_joint_states(self, msg) -> None:
        """Handle incoming joint states — will drive 3D model in Phase 3."""
        pass
