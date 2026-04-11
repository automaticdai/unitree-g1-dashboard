"""Small colored dot widget indicating topic health status."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPainter, QColor, QPaintEvent


class StatusDot(QWidget):
    """A small colored circle."""

    COLORS = {
        'active': QColor(0, 200, 83),      # Green
        'stale': QColor(255, 193, 7),       # Yellow/amber
        'inactive': QColor(117, 117, 117),  # Grey
        'error': QColor(244, 67, 54),       # Red
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._status = 'inactive'
        self.setFixedSize(10, 10)

    def set_status(self, status: str) -> None:
        if status != self._status:
            self._status = status
            self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = self.COLORS.get(self._status, self.COLORS['inactive'])
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(1, 1, 8, 8)


class TopicIndicator(QWidget):
    """A label + colored dot indicating topic health."""

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._dot = StatusDot()
        self._label = QLabel(label)
        self._label.setStyleSheet('font-size: 11px;')

        layout.addWidget(self._dot)
        layout.addWidget(self._label)

    def set_status(self, status: str) -> None:
        self._dot.set_status(status)
