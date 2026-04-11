"""Joint Control panel — sliders, command bar, gain editor."""

from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QScrollArea, QGroupBox,
    QHBoxLayout, QPushButton, QLabel, QCheckBox,
)
from PySide6.QtCore import Qt

from g1_dashboard.dashboard_node import DashboardNode
from g1_dashboard.config.robot_config import JOINT_GROUPS, joints_in_group


class JointControlPanel(QDockWidget):
    """Panel for visualizing and commanding joint angles.

    Phase 1: Shows joint group structure with placeholder labels.
    Phase 4: Full sliders, command publishing, gain editor.
    """

    def __init__(self, node: DashboardNode, parent=None):
        super().__init__('Joint Control', parent)
        self._node = node

        # Scroll area for the joint list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        main_layout = QVBoxLayout(container)

        # Command bar at top
        cmd_bar = QHBoxLayout()
        self._live_mode = QCheckBox('Live')
        self._live_mode.setToolTip('Send commands immediately as sliders move')
        cmd_bar.addWidget(self._live_mode)

        send_btn = QPushButton('Send')
        send_btn.setToolTip('Send all modified joint commands')
        cmd_bar.addWidget(send_btn)

        reset_btn = QPushButton('Reset')
        reset_btn.setToolTip('Reset sliders to current joint positions')
        cmd_bar.addWidget(reset_btn)

        home_btn = QPushButton('Home')
        home_btn.setToolTip('Command all joints to home position')
        cmd_bar.addWidget(home_btn)

        estop_btn = QPushButton('E-STOP')
        estop_btn.setStyleSheet(
            'QPushButton { background-color: #d32f2f; color: white; '
            'font-weight: bold; padding: 6px 16px; } '
            'QPushButton:hover { background-color: #f44336; }'
        )
        estop_btn.setToolTip('Emergency stop — engage damping mode')
        cmd_bar.addWidget(estop_btn)

        main_layout.addLayout(cmd_bar)

        # Joint groups
        for group_name in JOINT_GROUPS:
            group_box = QGroupBox(group_name)
            group_box.setCheckable(True)
            group_box.setChecked(True)
            group_layout = QVBoxLayout()

            joints = joints_in_group(group_name)
            for joint in joints:
                # Placeholder — will be replaced by JointSlider widget in Phase 4
                joint_label = QLabel(
                    f'  [{joint.index:2d}] {joint.name}  '
                    f'({joint.lower:.2f} to {joint.upper:.2f} rad)'
                )
                joint_label.setStyleSheet('font-family: monospace; font-size: 12px;')
                group_layout.addWidget(joint_label)

            group_box.setLayout(group_layout)
            main_layout.addWidget(group_box)

        main_layout.addStretch()
        scroll.setWidget(container)
        self.setWidget(scroll)

        # Connect to joint state updates
        self._node.signals.joint_states_received.connect(self._on_joint_states)

    def _on_joint_states(self, msg) -> None:
        """Handle incoming joint states — will update sliders in Phase 4."""
        pass
