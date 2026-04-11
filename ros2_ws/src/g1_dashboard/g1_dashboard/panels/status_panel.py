"""Status panel — IMU, battery, robot state, error log."""

from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QGroupBox, QLabel,
    QGridLayout, QTextEdit, QHBoxLayout,
)
from PySide6.QtCore import Qt

from g1_dashboard.dashboard_node import DashboardNode


class StatusPanel(QDockWidget):
    """Panel showing IMU, battery, robot state, and error log.

    Phase 1: Layout with placeholder values.
    Phase 2: Live data from ROS2 topics, pyqtgraph plots, IMU cube.
    """

    def __init__(self, node: DashboardNode, parent=None):
        super().__init__('Status', parent)
        self._node = node

        container = QWidget()
        layout = QVBoxLayout(container)

        # --- IMU Section ---
        imu_group = QGroupBox('IMU')
        imu_layout = QGridLayout()

        self._imu_labels = {}
        imu_fields = [
            ('Roll', 0, 0), ('Pitch', 0, 1), ('Yaw', 0, 2),
            ('Ang Vel X', 1, 0), ('Ang Vel Y', 1, 1), ('Ang Vel Z', 1, 2),
            ('Lin Acc X', 2, 0), ('Lin Acc Y', 2, 1), ('Lin Acc Z', 2, 2),
        ]
        for name, row, col in imu_fields:
            label = QLabel(f'{name}:')
            label.setStyleSheet('font-size: 11px; color: #aaa;')
            value = QLabel('--')
            value.setStyleSheet('font-size: 13px; font-family: monospace;')
            value.setAlignment(Qt.AlignmentFlag.AlignRight)
            imu_layout.addWidget(label, row * 2, col)
            imu_layout.addWidget(value, row * 2 + 1, col)
            self._imu_labels[name] = value

        imu_group.setLayout(imu_layout)
        layout.addWidget(imu_group)

        # --- Battery Section ---
        battery_group = QGroupBox('Battery')
        battery_layout = QGridLayout()

        self._battery_labels = {}
        battery_fields = [
            ('Level', 0, 0), ('Voltage', 0, 1),
            ('Current', 1, 0), ('Temp', 1, 1),
        ]
        for name, row, col in battery_fields:
            label = QLabel(f'{name}:')
            label.setStyleSheet('font-size: 11px; color: #aaa;')
            value = QLabel('--')
            value.setStyleSheet('font-size: 14px; font-family: monospace;')
            value.setAlignment(Qt.AlignmentFlag.AlignRight)
            battery_layout.addWidget(label, row * 2, col)
            battery_layout.addWidget(value, row * 2 + 1, col)
            self._battery_labels[name] = value

        battery_group.setLayout(battery_layout)
        layout.addWidget(battery_group)

        # --- Robot State ---
        state_group = QGroupBox('Robot State')
        state_layout = QHBoxLayout()

        mode_label = QLabel('Mode:')
        mode_label.setStyleSheet('font-size: 11px; color: #aaa;')
        self._mode_value = QLabel('--')
        self._mode_value.setStyleSheet(
            'font-size: 14px; font-weight: bold; padding: 2px 8px; '
            'border-radius: 4px; background-color: #444;'
        )
        state_layout.addWidget(mode_label)
        state_layout.addWidget(self._mode_value)
        state_layout.addStretch()

        state_group.setLayout(state_layout)
        layout.addWidget(state_group)

        # --- Error Log ---
        log_group = QGroupBox('Log')
        log_layout = QVBoxLayout()

        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMaximumHeight(150)
        self._log_text.setStyleSheet(
            'font-family: monospace; font-size: 11px; background-color: #1a1a1a;'
        )
        self._log_text.setPlaceholderText('No messages yet...')
        log_layout.addWidget(self._log_text)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        layout.addStretch()
        self.setWidget(container)

        # Connect signals
        self._node.signals.imu_received.connect(self._on_imu)
        self._node.signals.battery_received.connect(self._on_battery)

    def _on_imu(self, msg) -> None:
        """Update IMU display values."""
        import math
        q = msg.orientation
        # Quaternion to Euler (simplified)
        sinr_cosp = 2.0 * (q.w * q.x + q.y * q.z)
        cosr_cosp = 1.0 - 2.0 * (q.x * q.x + q.y * q.y)
        roll = math.atan2(sinr_cosp, cosr_cosp)

        sinp = 2.0 * (q.w * q.y - q.z * q.x)
        pitch = math.asin(max(-1.0, min(1.0, sinp)))

        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        yaw = math.atan2(siny_cosp, cosy_cosp)

        self._imu_labels['Roll'].setText(f'{math.degrees(roll):.1f}\u00b0')
        self._imu_labels['Pitch'].setText(f'{math.degrees(pitch):.1f}\u00b0')
        self._imu_labels['Yaw'].setText(f'{math.degrees(yaw):.1f}\u00b0')

        av = msg.angular_velocity
        self._imu_labels['Ang Vel X'].setText(f'{av.x:.3f}')
        self._imu_labels['Ang Vel Y'].setText(f'{av.y:.3f}')
        self._imu_labels['Ang Vel Z'].setText(f'{av.z:.3f}')

        la = msg.linear_acceleration
        self._imu_labels['Lin Acc X'].setText(f'{la.x:.2f}')
        self._imu_labels['Lin Acc Y'].setText(f'{la.y:.2f}')
        self._imu_labels['Lin Acc Z'].setText(f'{la.z:.2f}')

    def _on_battery(self, msg) -> None:
        """Update battery display values."""
        self._battery_labels['Level'].setText(f'{msg.percentage:.0f}%')
        self._battery_labels['Voltage'].setText(f'{msg.voltage:.1f} V')
        self._battery_labels['Current'].setText(f'{msg.current:.1f} A')
        if msg.temperature > 0:
            self._battery_labels['Temp'].setText(f'{msg.temperature:.0f} \u00b0C')
