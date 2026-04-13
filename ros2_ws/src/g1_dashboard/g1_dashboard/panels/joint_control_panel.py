"""Joint Control panel — sliders, gain editor, command publishing."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QScrollArea, QGroupBox,
    QHBoxLayout, QPushButton, QCheckBox, QLabel, QComboBox, QDoubleSpinBox,
)
from PySide6.QtCore import Qt

from g1_dashboard.config.robot_config import (
    JOINTS, JOINT_GROUPS, JOINT_BY_NAME, JOINT_BY_INDEX, joints_in_group,
)
from g1_dashboard.dashboard_node import DashboardNode
from g1_dashboard.widgets.joint_row import JointRow


N_JOINTS = 29


# Gain presets — multipliers applied to the per-joint default kp/kd.
GAIN_PRESETS: dict[str, tuple[float, float]] = {
    'Stiff':     (1.5, 1.2),
    'Default':   (1.0, 1.0),
    'Compliant': (0.3, 0.8),
}


class JointControlPanel(QDockWidget):
    """29 joint rows with sliders, plus a command bar and gain editor."""

    def __init__(self, node: DashboardNode, parent=None):
        super().__init__('Joint Control', parent)
        self._node = node
        self._rows: dict[int, JointRow] = {}
        self._unit_degrees = False

        # Per-joint gain overrides (index -> (kp, kd)). Fall back to JointDef defaults.
        self._gain_overrides: dict[int, tuple[float, float]] = {}

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        main_layout = QVBoxLayout(container)

        main_layout.addLayout(self._build_command_bar())

        # Joint groups with rows
        for group_name in JOINT_GROUPS:
            group_box = QGroupBox(group_name)
            group_layout = QVBoxLayout()
            group_layout.setSpacing(2)
            group_layout.setContentsMargins(6, 14, 6, 6)

            for joint in joints_in_group(group_name):
                row = JointRow(joint.index, joint.name, joint.lower, joint.upper)
                row.clicked.connect(self._on_row_clicked)
                row.command_edited.connect(self._on_command_edited)
                group_layout.addWidget(row)
                self._rows[joint.index] = row

            group_box.setLayout(group_layout)
            main_layout.addWidget(group_box)

        main_layout.addWidget(self._build_gain_editor())
        main_layout.addStretch()

        scroll.setWidget(container)
        self.setWidget(scroll)

        # Signal wiring
        self._node.signals.joint_states_received.connect(self._on_joint_states)
        self._node.selection.selection_changed.connect(self._on_selection_changed)

    # --- UI builders ---

    def _build_command_bar(self) -> QHBoxLayout:
        cmd_bar = QHBoxLayout()

        self._deg_toggle = QCheckBox('degrees')
        self._deg_toggle.toggled.connect(self._on_unit_toggle)
        cmd_bar.addWidget(self._deg_toggle)

        self._live_mode = QCheckBox('Live send')
        self._live_mode.setToolTip('Send a command immediately on every slider edit')
        cmd_bar.addWidget(self._live_mode)

        cmd_bar.addStretch()

        self._send_btn = QPushButton('Send')
        self._send_btn.setToolTip('Publish commands for all modified joints')
        self._send_btn.clicked.connect(self._on_send_clicked)
        cmd_bar.addWidget(self._send_btn)

        self._reset_btn = QPushButton('Reset')
        self._reset_btn.setToolTip('Snap all commanded positions to current')
        self._reset_btn.clicked.connect(self._on_reset_clicked)
        cmd_bar.addWidget(self._reset_btn)

        self._home_btn = QPushButton('Home')
        self._home_btn.setToolTip('Command zero pose for all joints')
        self._home_btn.clicked.connect(self._on_home_clicked)
        cmd_bar.addWidget(self._home_btn)

        self._estop_btn = QPushButton('E-STOP')
        self._estop_btn.setToolTip('Engage emergency stop (damping mode)')
        self._estop_btn.setStyleSheet(
            'QPushButton { background-color: #d32f2f; color: white; '
            'font-weight: bold; padding: 6px 16px; }'
            'QPushButton:hover { background-color: #b71c1c; }'
        )
        self._estop_btn.clicked.connect(self._on_estop_clicked)
        cmd_bar.addWidget(self._estop_btn)

        return cmd_bar

    def _build_gain_editor(self) -> QGroupBox:
        box = QGroupBox('Gain Editor (selected joint)')
        outer = QVBoxLayout()

        self._gain_joint_lbl = QLabel('No joint selected')
        self._gain_joint_lbl.setStyleSheet('color: #aaa;')
        outer.addWidget(self._gain_joint_lbl)

        row = QHBoxLayout()

        row.addWidget(QLabel('kp'))
        self._kp_spin = QDoubleSpinBox()
        self._kp_spin.setDecimals(2)
        self._kp_spin.setRange(0.0, 1000.0)
        self._kp_spin.setKeyboardTracking(False)
        self._kp_spin.valueChanged.connect(self._on_kp_changed)
        row.addWidget(self._kp_spin)

        row.addWidget(QLabel('kd'))
        self._kd_spin = QDoubleSpinBox()
        self._kd_spin.setDecimals(2)
        self._kd_spin.setRange(0.0, 100.0)
        self._kd_spin.setKeyboardTracking(False)
        self._kd_spin.valueChanged.connect(self._on_kd_changed)
        row.addWidget(self._kd_spin)

        row.addWidget(QLabel('Preset'))
        self._preset_combo = QComboBox()
        self._preset_combo.addItems(['Custom'] + list(GAIN_PRESETS.keys()))
        self._preset_combo.currentTextChanged.connect(self._on_preset_changed)
        row.addWidget(self._preset_combo)

        row.addStretch()
        outer.addLayout(row)

        box.setLayout(outer)
        self._gain_editor_enabled(False)
        return box

    def _gain_editor_enabled(self, enabled: bool) -> None:
        for w in (self._kp_spin, self._kd_spin, self._preset_combo):
            w.setEnabled(enabled)

    # --- Row / selection handlers ---

    def _on_joint_states(self, msg) -> None:
        for name, pos in zip(msg.name, msg.position):
            joint = JOINT_BY_NAME.get(name)
            if joint is None:
                continue
            row = self._rows.get(joint.index)
            if row is not None:
                row.set_current(float(pos))
        self._emit_commanded_state()

    def _on_row_clicked(self, joint_index: int) -> None:
        current = self._node.selection.selected
        new_sel = None if current == joint_index else joint_index
        self._node.selection.set_selected(new_sel)

    def _on_selection_changed(self, index: int) -> None:
        selected = None if index < 0 else index
        for idx, row in self._rows.items():
            row.set_selected(idx == selected)
        self._refresh_gain_editor(selected)

    def _on_unit_toggle(self, checked: bool) -> None:
        self._unit_degrees = checked
        for row in self._rows.values():
            row.set_unit_degrees(checked)

    def _on_command_edited(self, joint_index: int, radians: float) -> None:
        self._emit_commanded_state()
        if self._live_mode.isChecked():
            self._publish_single(joint_index, radians)

    # --- Command bar handlers ---

    def _on_send_clicked(self) -> None:
        self._publish_dirty()

    def _on_reset_clicked(self) -> None:
        for row in self._rows.values():
            row.clear_dirty()
        self._emit_commanded_state()

    def _on_home_clicked(self) -> None:
        for row in self._rows.values():
            row.set_command(0.0, mark_dirty=True)
        self._emit_commanded_state()
        if self._live_mode.isChecked():
            self._publish_dirty()

    def _on_estop_clicked(self) -> None:
        result = self._node.trigger_estop(activate=True)
        if result is None:
            self._node.get_logger().warn('E-STOP: service unreachable')

    # --- Gain editor ---

    def _refresh_gain_editor(self, selected: int | None) -> None:
        if selected is None:
            self._gain_joint_lbl.setText('No joint selected')
            self._gain_editor_enabled(False)
            return
        joint = JOINT_BY_INDEX[selected]
        kp, kd = self._gain_overrides.get(selected, (joint.default_kp, joint.default_kd))
        self._gain_joint_lbl.setText(f'{joint.name}  (defaults: kp={joint.default_kp}, kd={joint.default_kd})')
        for spin, value in ((self._kp_spin, kp), (self._kd_spin, kd)):
            spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(False)
        self._gain_editor_enabled(True)

    def _on_kp_changed(self, value: float) -> None:
        idx = self._node.selection.selected
        if idx is None:
            return
        _, kd = self._gain_overrides.get(
            idx, (JOINT_BY_INDEX[idx].default_kp, JOINT_BY_INDEX[idx].default_kd))
        self._gain_overrides[idx] = (value, kd)
        self._preset_combo.blockSignals(True)
        self._preset_combo.setCurrentText('Custom')
        self._preset_combo.blockSignals(False)

    def _on_kd_changed(self, value: float) -> None:
        idx = self._node.selection.selected
        if idx is None:
            return
        kp, _ = self._gain_overrides.get(
            idx, (JOINT_BY_INDEX[idx].default_kp, JOINT_BY_INDEX[idx].default_kd))
        self._gain_overrides[idx] = (kp, value)
        self._preset_combo.blockSignals(True)
        self._preset_combo.setCurrentText('Custom')
        self._preset_combo.blockSignals(False)

    def _on_preset_changed(self, name: str) -> None:
        if name == 'Custom':
            return
        idx = self._node.selection.selected
        if idx is None:
            return
        kp_mul, kd_mul = GAIN_PRESETS[name]
        joint = JOINT_BY_INDEX[idx]
        kp = joint.default_kp * kp_mul
        kd = joint.default_kd * kd_mul
        self._gain_overrides[idx] = (kp, kd)
        for spin, value in ((self._kp_spin, kp), (self._kd_spin, kd)):
            spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(False)

    # --- Publish / state emit ---

    def _publish_dirty(self) -> int:
        commands = []
        for idx, row in self._rows.items():
            if row.is_dirty:
                commands.append(self._make_cmd(idx, row.command))
        return self._send(commands)

    def _publish_single(self, joint_index: int, radians: float) -> int:
        return self._send([self._make_cmd(joint_index, radians)])

    def _make_cmd(self, joint_index: int, position: float):
        from g1_dashboard_msgs.msg import JointCommand
        joint = JOINT_BY_INDEX[joint_index]
        kp, kd = self._gain_overrides.get(joint_index, (joint.default_kp, joint.default_kd))
        cmd = JointCommand()
        cmd.joint_index = joint_index
        cmd.target_position = float(position)
        cmd.target_velocity = 0.0
        cmd.kp = float(kp)
        cmd.kd = float(kd)
        cmd.feedforward_torque = 0.0
        return cmd

    def _send(self, commands: list) -> int:
        if not commands:
            return 0
        try:
            return self._node.publish_joint_commands(commands)
        except ImportError:
            self._node.get_logger().error('JointCommand msg unavailable — commands dropped')
            return 0

    def _emit_commanded_state(self) -> None:
        positions = [0.0] * N_JOINTS
        dirty = [False] * N_JOINTS
        for idx in range(N_JOINTS):
            row = self._rows.get(idx)
            if row is None:
                continue
            positions[idx] = row.command
            dirty[idx] = row.is_dirty
        self._node.commanded.update(positions, dirty)
