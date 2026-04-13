"""Joint Control panel — clickable joint rows, live values, command bar."""

from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QScrollArea, QGroupBox,
    QHBoxLayout, QPushButton, QCheckBox,
)
from PySide6.QtCore import Qt

from g1_dashboard.config.robot_config import (
    JOINT_GROUPS, JOINT_BY_NAME, joints_in_group,
)
from g1_dashboard.dashboard_node import DashboardNode
from g1_dashboard.widgets.joint_row import JointRow


class JointControlPanel(QDockWidget):
    """Joint positions panel with clickable rows.

    Phase 3: Clickable rows showing live values, bidirectional selection with 3D viewport.
    Phase 4 will add sliders, gain editors, and command publishing.
    """

    def __init__(self, node: DashboardNode, parent=None):
        super().__init__('Joint Control', parent)
        self._node = node
        self._rows: dict[int, JointRow] = {}
        self._unit_degrees = False

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        main_layout = QVBoxLayout(container)

        # Command bar (will become functional in Phase 4)
        cmd_bar = QHBoxLayout()

        self._deg_toggle = QCheckBox('degrees')
        self._deg_toggle.toggled.connect(self._on_unit_toggle)
        cmd_bar.addWidget(self._deg_toggle)

        self._live_mode = QCheckBox('Live send')
        self._live_mode.setToolTip('Send commands immediately as sliders move (Phase 4)')
        self._live_mode.setEnabled(False)
        cmd_bar.addWidget(self._live_mode)

        cmd_bar.addStretch()

        for text, tip in [
            ('Send',  'Send modified joint commands (Phase 4)'),
            ('Reset', 'Snap commanded positions to current (Phase 4)'),
            ('Home',  'Command zero pose (Phase 4)'),
        ]:
            btn = QPushButton(text)
            btn.setToolTip(tip)
            btn.setEnabled(False)
            cmd_bar.addWidget(btn)

        estop = QPushButton('E-STOP')
        estop.setToolTip('Emergency stop — engage damping mode (Phase 4)')
        estop.setEnabled(False)
        estop.setStyleSheet(
            'QPushButton { background-color: #d32f2f; color: white; '
            'font-weight: bold; padding: 6px 16px; } '
            'QPushButton:disabled { background-color: #6a1818; color: #bbb; }'
        )
        cmd_bar.addWidget(estop)

        main_layout.addLayout(cmd_bar)

        # Joint groups
        for group_name in JOINT_GROUPS:
            group_box = QGroupBox(group_name)
            group_layout = QVBoxLayout()
            group_layout.setSpacing(2)
            group_layout.setContentsMargins(6, 14, 6, 6)

            for joint in joints_in_group(group_name):
                row = JointRow(joint.index, joint.name, joint.lower, joint.upper)
                row.clicked.connect(self._on_row_clicked)
                group_layout.addWidget(row)
                self._rows[joint.index] = row

            group_box.setLayout(group_layout)
            main_layout.addWidget(group_box)

        main_layout.addStretch()
        scroll.setWidget(container)
        self.setWidget(scroll)

        # Signal wiring
        self._node.signals.joint_states_received.connect(self._on_joint_states)
        self._node.selection.selection_changed.connect(self._on_selection_changed)

    # --- Handlers ---

    def _on_joint_states(self, msg) -> None:
        for name, pos in zip(msg.name, msg.position):
            joint = JOINT_BY_NAME.get(name)
            if joint is None:
                continue
            row = self._rows.get(joint.index)
            if row is not None:
                row.set_value(float(pos), unit_degrees=self._unit_degrees)

    def _on_row_clicked(self, joint_index: int) -> None:
        # Toggle selection if clicking already-selected row
        current = self._node.selection.selected
        new_sel = None if current == joint_index else joint_index
        self._node.selection.set_selected(new_sel)

    def _on_selection_changed(self, index: int) -> None:
        selected = None if index < 0 else index
        for idx, row in self._rows.items():
            row.set_selected(idx == selected)

    def _on_unit_toggle(self, checked: bool) -> None:
        self._unit_degrees = checked
        # Re-render values in new unit on next joint_states message; no cached state
