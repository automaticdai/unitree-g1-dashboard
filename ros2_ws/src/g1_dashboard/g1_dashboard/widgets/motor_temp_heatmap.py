"""Motor temperature heatmap widget — 29 motors color-coded by group."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QGroupBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette

from g1_dashboard.config.robot_config import JOINTS, JOINT_GROUPS, joints_in_group


# Temperature color thresholds (Celsius)
TEMP_OK = 50.0     # below = green
TEMP_WARN = 65.0   # below = yellow, above = red
TEMP_MAX = 80.0    # for gradient scaling


def _temp_color(temp: float) -> QColor:
    """Map temperature to a color (green -> yellow -> red)."""
    if temp <= 0.0:
        return QColor(60, 60, 60)  # unknown
    if temp < TEMP_OK:
        return QColor(46, 125, 50)   # green
    if temp < TEMP_WARN:
        # Yellow/amber gradient
        t = (temp - TEMP_OK) / (TEMP_WARN - TEMP_OK)
        r = int(76 + (255 - 76) * t)
        g = int(175 + (193 - 175) * t)
        b = int(80 + (7 - 80) * t)
        return QColor(r, g, b)
    # Red gradient above warning
    t = min(1.0, (temp - TEMP_WARN) / (TEMP_MAX - TEMP_WARN))
    r = int(255 + (244 - 255) * t)
    g = int(193 + (67 - 193) * t)
    b = int(7 + (54 - 7) * t)
    return QColor(r, g, b)


class _MotorCell(QLabel):
    """A single motor temperature cell."""

    def __init__(self, index: int, name: str, parent=None):
        super().__init__(parent)
        self._index = index
        self._short_name = _short_joint_name(name)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAutoFillBackground(True)
        self.setMinimumSize(58, 34)
        self.setToolTip(f'[{index}] {name}')
        self.set_temperature(0.0)

    def set_temperature(self, temp: float) -> None:
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, _temp_color(temp))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(20, 20, 20))
        self.setPalette(palette)
        if temp > 0.0:
            self.setText(f'{self._short_name}\n{temp:.0f}\u00b0')
        else:
            self.setText(f'{self._short_name}\n--')
        self.setStyleSheet('font-size: 10px; font-weight: bold; border-radius: 3px;')


def _short_joint_name(name: str) -> str:
    """Abbreviate joint names for compact display (e.g., left_hip_pitch_joint -> LHP)."""
    name = name.replace('_joint', '')
    parts = name.split('_')
    if not parts:
        return name
    # Side initial + first letters of remaining parts (uppercase)
    side = parts[0][0].upper() if parts[0] in ('left', 'right') else ''
    rest = ''.join(p[0].upper() for p in parts[1:]) if side else ''.join(p[0].upper() for p in parts)
    return (side + rest)[:4]


class MotorTempHeatmap(QWidget):
    """Grid of 29 motor temperature cells grouped by body part."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cells: dict[int, _MotorCell] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)

        for group_name in JOINT_GROUPS:
            group_box = QGroupBox(group_name)
            group_layout = QGridLayout()
            group_layout.setSpacing(3)
            group_layout.setContentsMargins(6, 14, 6, 6)

            joints = joints_in_group(group_name)
            for col, joint in enumerate(joints):
                cell = _MotorCell(joint.index, joint.name)
                self._cells[joint.index] = cell
                group_layout.addWidget(cell, 0, col)

            group_box.setLayout(group_layout)
            outer.addWidget(group_box)

    def set_temperatures(self, temps: list[float]) -> None:
        """Update all motor temperatures.

        Args:
            temps: List of 29 temperatures in Celsius (0 = unknown)
        """
        for i, temp in enumerate(temps[:29]):
            cell = self._cells.get(i)
            if cell is not None:
                cell.set_temperature(float(temp))
