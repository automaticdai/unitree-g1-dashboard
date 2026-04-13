"""Clickable joint row widget.

Shown as a label in Phase 1-3; Phase 4 will replace the right-hand area
with a live slider. The row is clickable to update shared selection.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class JointRow(QWidget):
    """A single joint displayed as a compact, clickable row."""

    clicked = Signal(int)  # Emits joint index

    def __init__(self, joint_index: int, joint_name: str,
                 lower: float, upper: float, parent=None):
        super().__init__(parent)
        self._joint_index = joint_index
        self._selected = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(10)

        index_lbl = QLabel(f'[{joint_index:2d}]')
        index_lbl.setStyleSheet('font-family: monospace; color: #888;')
        index_lbl.setMinimumWidth(34)
        layout.addWidget(index_lbl)

        self._name_lbl = QLabel(joint_name)
        self._name_lbl.setStyleSheet('font-family: monospace; font-size: 12px;')
        layout.addWidget(self._name_lbl, stretch=1)

        self._value_lbl = QLabel('--')
        self._value_lbl.setStyleSheet(
            'font-family: monospace; font-size: 12px; color: #aaa;')
        self._value_lbl.setMinimumWidth(70)
        self._value_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._value_lbl)

        limits_lbl = QLabel(f'[{lower:+.2f}, {upper:+.2f}]')
        limits_lbl.setStyleSheet(
            'font-family: monospace; font-size: 10px; color: #666;')
        layout.addWidget(limits_lbl)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style()

    @property
    def joint_index(self) -> int:
        return self._joint_index

    def set_value(self, radians: float, unit_degrees: bool = False) -> None:
        if unit_degrees:
            import math
            self._value_lbl.setText(f'{math.degrees(radians):+6.1f}\u00b0')
        else:
            self._value_lbl.setText(f'{radians:+6.3f}')

    def set_selected(self, selected: bool) -> None:
        if selected != self._selected:
            self._selected = selected
            self._apply_style()

    def _apply_style(self) -> None:
        if self._selected:
            self.setStyleSheet(
                'JointRow { background-color: #3a4a62; border-left: 3px solid #ff8c1a; }')
        else:
            self.setStyleSheet(
                'JointRow { background-color: transparent; border-left: 3px solid transparent; }'
                'JointRow:hover { background-color: #2a2a30; }')

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._joint_index)
        super().mousePressEvent(event)
