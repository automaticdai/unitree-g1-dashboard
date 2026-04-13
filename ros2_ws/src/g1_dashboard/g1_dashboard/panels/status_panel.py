"""Status panel — IMU, battery, robot state, motor temperatures, error log."""

import math
import time

from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QTextEdit, QScrollArea,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette

from g1_dashboard.dashboard_node import DashboardNode
from g1_dashboard.widgets.battery_gauge import BatteryGauge
from g1_dashboard.widgets.motor_temp_heatmap import MotorTempHeatmap
from g1_dashboard.widgets.rolling_plot import RollingPlot


# Robot mode enum -> (label, color)
MODE_INFO = {
    0: ('Unknown', '#757575'),
    1: ('Idle', '#607d8b'),
    2: ('Standing', '#4caf50'),
    3: ('Walking', '#2196f3'),
    4: ('Low-Level', '#ff9800'),
    5: ('Damping', '#9c27b0'),
    6: ('Emergency', '#f44336'),
}


class StatusPanel(QDockWidget):
    """Live robot telemetry: IMU plots, battery, mode, motor temps, log."""

    def __init__(self, node: DashboardNode, parent=None):
        super().__init__('Status', parent)
        self._node = node

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(8)

        # --- Row 1: Battery gauge + Robot mode badge ---
        top_row = QHBoxLayout()

        battery_group = QGroupBox('Battery')
        battery_layout = QVBoxLayout(battery_group)
        self._battery_gauge = BatteryGauge()
        battery_layout.addWidget(self._battery_gauge,
                                 alignment=Qt.AlignmentFlag.AlignCenter)
        top_row.addWidget(battery_group)

        state_group = QGroupBox('Robot State')
        state_layout = QVBoxLayout(state_group)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel('Mode:'))
        self._mode_badge = QLabel('--')
        self._mode_badge.setStyleSheet(self._mode_badge_style('#444'))
        self._mode_badge.setMinimumWidth(120)
        self._mode_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mode_row.addWidget(self._mode_badge)
        mode_row.addStretch()
        state_layout.addLayout(mode_row)

        # Foot forces (4 bars side-by-side)
        foot_row = QHBoxLayout()
        foot_row.addWidget(QLabel('Foot forces:'))
        self._foot_labels: list[QLabel] = []
        for foot in ('FL', 'FR', 'RL', 'RR'):
            lbl = QLabel(f'{foot} --')
            lbl.setStyleSheet(
                'font-family: monospace; font-size: 11px; '
                'padding: 2px 6px; background-color: #2a2a2a; border-radius: 3px;')
            foot_row.addWidget(lbl)
            self._foot_labels.append(lbl)
        foot_row.addStretch()
        state_layout.addLayout(foot_row)

        # Safety indicators
        safety_row = QHBoxLayout()
        self._estop_label = QLabel('E-Stop: off')
        self._estop_label.setStyleSheet('font-size: 11px; padding: 2px 6px;')
        safety_row.addWidget(self._estop_label)
        self._limits_label = QLabel('Limits: --')
        self._limits_label.setStyleSheet('font-size: 11px; padding: 2px 6px;')
        safety_row.addWidget(self._limits_label)
        self._heartbeat_label = QLabel('HB: --')
        self._heartbeat_label.setStyleSheet('font-size: 11px; padding: 2px 6px;')
        safety_row.addWidget(self._heartbeat_label)
        safety_row.addStretch()
        state_layout.addLayout(safety_row)

        state_layout.addStretch()
        top_row.addWidget(state_group, stretch=1)

        layout.addLayout(top_row)

        # --- Row 2: IMU Euler readout ---
        imu_group = QGroupBox('IMU')
        imu_layout = QVBoxLayout(imu_group)

        euler_row = QGridLayout()
        self._imu_labels: dict[str, QLabel] = {}
        for col, name in enumerate(('Roll', 'Pitch', 'Yaw')):
            header = QLabel(name)
            header.setStyleSheet('font-size: 10px; color: #888;')
            header.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value = QLabel('--')
            value.setStyleSheet(
                'font-size: 18px; font-family: monospace; font-weight: bold;')
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            euler_row.addWidget(header, 0, col)
            euler_row.addWidget(value, 1, col)
            self._imu_labels[name] = value
        imu_layout.addLayout(euler_row)

        # pyqtgraph plots for angular velocity + linear acceleration
        self._ang_vel_plot = RollingPlot(
            title='Angular Velocity (rad/s)',
            trace_names=['x', 'y', 'z'],
            y_label='rad/s',
            window_seconds=10.0,
        )
        self._ang_vel_plot.setMinimumHeight(140)
        imu_layout.addWidget(self._ang_vel_plot)

        self._lin_acc_plot = RollingPlot(
            title='Linear Acceleration (m/s\u00b2)',
            trace_names=['x', 'y', 'z'],
            y_label='m/s\u00b2',
            window_seconds=10.0,
        )
        self._lin_acc_plot.setMinimumHeight(140)
        imu_layout.addWidget(self._lin_acc_plot)

        layout.addWidget(imu_group)

        # --- Row 3: Motor temperature heatmap ---
        temp_group = QGroupBox('Motor Temperatures')
        temp_layout = QVBoxLayout(temp_group)
        self._temp_heatmap = MotorTempHeatmap()
        temp_layout.addWidget(self._temp_heatmap)
        layout.addWidget(temp_group)

        # --- Row 4: Error log ---
        log_group = QGroupBox('Log')
        log_layout = QVBoxLayout(log_group)
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMaximumHeight(120)
        self._log_text.setStyleSheet(
            'font-family: monospace; font-size: 11px; background-color: #1a1a1a;')
        self._log_text.setPlaceholderText('No messages yet...')
        log_layout.addWidget(self._log_text)
        layout.addWidget(log_group)

        layout.addStretch()
        scroll.setWidget(container)
        self.setWidget(scroll)

        # --- Connect signals ---
        self._node.signals.imu_received.connect(self._on_imu)
        self._node.signals.battery_received.connect(self._on_battery)
        self._node.signals.robot_state_received.connect(self._on_robot_state)
        self._node.signals.safety_received.connect(self._on_safety)

    @staticmethod
    def _mode_badge_style(bg: str) -> str:
        return (
            f'font-size: 13px; font-weight: bold; padding: 4px 10px; '
            f'border-radius: 4px; background-color: {bg}; color: white;'
        )

    # --- Slot handlers (main thread) ---

    def _on_imu(self, msg) -> None:
        q = msg.orientation
        sinr_cosp = 2.0 * (q.w * q.x + q.y * q.z)
        cosr_cosp = 1.0 - 2.0 * (q.x * q.x + q.y * q.y)
        roll = math.atan2(sinr_cosp, cosr_cosp)
        sinp = 2.0 * (q.w * q.y - q.z * q.x)
        pitch = math.asin(max(-1.0, min(1.0, sinp)))
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        yaw = math.atan2(siny_cosp, cosy_cosp)

        self._imu_labels['Roll'].setText(f'{math.degrees(roll):+6.1f}\u00b0')
        self._imu_labels['Pitch'].setText(f'{math.degrees(pitch):+6.1f}\u00b0')
        self._imu_labels['Yaw'].setText(f'{math.degrees(yaw):+6.1f}\u00b0')

        av = msg.angular_velocity
        self._ang_vel_plot.append([av.x, av.y, av.z])

        la = msg.linear_acceleration
        self._lin_acc_plot.append([la.x, la.y, la.z])

    def _on_battery(self, msg) -> None:
        # ROS convention: percentage is 0.0-1.0; some publishers use 0-100
        pct = msg.percentage
        if pct <= 1.0:
            pct *= 100.0
        self._battery_gauge.set_state(
            percentage=pct,
            voltage=msg.voltage,
            current=msg.current,
            temperature=msg.temperature,
        )

    def _on_robot_state(self, msg) -> None:
        mode = int(msg.mode)
        label, color = MODE_INFO.get(mode, ('Unknown', '#757575'))
        name = msg.mode_name if msg.mode_name else label
        self._mode_badge.setText(name)
        self._mode_badge.setStyleSheet(self._mode_badge_style(color))

        # Motor temperatures
        temps = list(msg.motor_temperatures)
        self._temp_heatmap.set_temperatures(temps)

        # Foot forces
        for i, lbl in enumerate(self._foot_labels):
            name = ('FL', 'FR', 'RL', 'RR')[i]
            if i < len(msg.foot_forces):
                lbl.setText(f'{name} {msg.foot_forces[i]:5.0f}N')

        # Surface new error codes to the log
        if msg.error_codes:
            stamp = time.strftime('%H:%M:%S')
            for code in msg.error_codes:
                self._append_log(f'[{stamp}] error 0x{code:08x}', severity='error')

    def _on_safety(self, msg) -> None:
        self._estop_label.setText(
            'E-Stop: ACTIVE' if msg.estop_active else 'E-Stop: off')
        self._estop_label.setStyleSheet(
            'font-size: 11px; padding: 2px 6px; color: '
            + ('#f44336' if msg.estop_active else '#bbb') + ';'
        )

        self._limits_label.setText(
            f'Limits: {"on" if msg.limits_active else "OFF"}')
        self._limits_label.setStyleSheet(
            'font-size: 11px; padding: 2px 6px; color: '
            + ('#4caf50' if msg.limits_active else '#ff9800') + ';'
        )

        hb_ok = msg.heartbeat_ok
        self._heartbeat_label.setText(
            f'HB: {"ok" if hb_ok else "LOST"} ({msg.heartbeat_age*1000:.0f}ms)')
        self._heartbeat_label.setStyleSheet(
            'font-size: 11px; padding: 2px 6px; color: '
            + ('#4caf50' if hb_ok else '#f44336') + ';'
        )

    def _append_log(self, text: str, severity: str = 'info') -> None:
        color = {'error': '#f44336', 'warn': '#ff9800', 'info': '#e0e0e0'}.get(
            severity, '#e0e0e0')
        self._log_text.append(f'<span style="color:{color}">{text}</span>')
