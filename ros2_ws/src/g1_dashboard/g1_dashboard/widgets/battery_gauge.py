"""Circular battery gauge widget."""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRectF, QSize
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QPaintEvent


class BatteryGauge(QWidget):
    """Circular arc gauge showing battery percentage with color coding."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._percentage = 0.0
        self._voltage = 0.0
        self._current = 0.0
        self._temperature = 0.0
        self._has_data = False
        self.setMinimumSize(140, 140)

    def sizeHint(self) -> QSize:
        return QSize(160, 160)

    def set_state(self, percentage: float, voltage: float,
                  current: float, temperature: float) -> None:
        """Update gauge values.

        Args:
            percentage: Battery level 0-100
            voltage: Volts
            current: Amps (negative = discharging)
            temperature: Celsius
        """
        self._percentage = max(0.0, min(100.0, percentage))
        self._voltage = voltage
        self._current = current
        self._temperature = temperature
        self._has_data = True
        self.update()

    def _level_color(self) -> QColor:
        if self._percentage >= 50.0:
            return QColor(76, 175, 80)    # green
        if self._percentage >= 20.0:
            return QColor(255, 193, 7)    # amber
        return QColor(244, 67, 54)        # red

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        side = min(self.width(), self.height())
        padding = 12
        rect = QRectF(
            (self.width() - side) / 2 + padding,
            (self.height() - side) / 2 + padding,
            side - 2 * padding,
            side - 2 * padding,
        )

        # Track arc (background)
        pen = QPen(QColor(60, 60, 60), 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        # Qt angles are in 1/16 of a degree; start at 135, span 270 CW (negative sweep)
        start_angle = 225 * 16
        full_span = -270 * 16
        painter.drawArc(rect, start_angle, full_span)

        # Value arc
        if self._has_data:
            pen.setColor(self._level_color())
            painter.setPen(pen)
            span = int(full_span * (self._percentage / 100.0))
            painter.drawArc(rect, start_angle, span)

        # Center text
        painter.setPen(QColor(220, 220, 220))
        center_font = QFont()
        center_font.setPointSize(22)
        center_font.setBold(True)
        painter.setFont(center_font)
        if self._has_data:
            text = f'{self._percentage:.0f}%'
        else:
            text = '--'
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

        # Sub-readouts below center
        if self._has_data:
            sub_font = QFont()
            sub_font.setPointSize(9)
            painter.setFont(sub_font)
            painter.setPen(QColor(160, 160, 160))
            sub_text = f'{self._voltage:.1f}V  {self._current:+.1f}A'
            sub_rect = QRectF(rect.left(), rect.center().y() + 14,
                              rect.width(), 18)
            painter.drawText(sub_rect, Qt.AlignmentFlag.AlignCenter, sub_text)

            if self._temperature > 0.0:
                temp_rect = QRectF(rect.left(), rect.center().y() + 30,
                                   rect.width(), 16)
                painter.drawText(temp_rect, Qt.AlignmentFlag.AlignCenter,
                                 f'{self._temperature:.0f}\u00b0C')
