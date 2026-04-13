"""Clickable joint row with slider + spinbox for command input.

Each row is clickable to update shared selection, displays the current
joint position (from /joint_states), and lets the user set a commanded
position via slider or numeric entry. The row tracks a "dirty" flag:
a row becomes dirty when the user edits the command; non-dirty rows
have their command track the current position on every update.
"""

from __future__ import annotations

import math

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QWidget, QSlider, QDoubleSpinBox,
)


SLIDER_STEPS = 1000  # int ticks between lower/upper


class JointRow(QWidget):
    """A single joint row with slider + spinbox."""

    clicked = Signal(int)                    # joint index — row clicked anywhere non-interactive
    command_edited = Signal(int, float)      # joint index, new commanded value (radians)

    def __init__(self, joint_index: int, joint_name: str,
                 lower: float, upper: float, parent=None):
        super().__init__(parent)
        self._joint_index = joint_index
        self._lower = lower
        self._upper = upper
        self._selected = False
        self._dirty = False
        self._current_rad = 0.0
        self._command_rad = 0.0
        self._unit_degrees = False
        self._suppress_edit = False  # guard against programmatic/update-driven edits

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(8)

        index_lbl = QLabel(f'[{joint_index:2d}]')
        index_lbl.setStyleSheet('font-family: monospace; color: #888;')
        index_lbl.setMinimumWidth(34)
        layout.addWidget(index_lbl)

        self._name_lbl = QLabel(joint_name)
        self._name_lbl.setStyleSheet('font-family: monospace; font-size: 12px;')
        self._name_lbl.setMinimumWidth(180)
        layout.addWidget(self._name_lbl)

        self._current_lbl = QLabel('--')
        self._current_lbl.setStyleSheet(
            'font-family: monospace; font-size: 11px; color: #6aa2ff;')
        self._current_lbl.setMinimumWidth(70)
        self._current_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._current_lbl.setToolTip('Current position (from /joint_states)')
        layout.addWidget(self._current_lbl)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, SLIDER_STEPS)
        self._slider.setSingleStep(1)
        self._slider.setPageStep(20)
        self._slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self._slider, stretch=1)

        self._spin = QDoubleSpinBox()
        self._spin.setDecimals(3)
        self._spin.setSingleStep(0.01)
        self._spin.setRange(lower, upper)
        self._spin.setMinimumWidth(80)
        self._spin.setKeyboardTracking(False)
        self._spin.valueChanged.connect(self._on_spin_changed)
        layout.addWidget(self._spin)

        self._limits_lbl = QLabel(f'[{lower:+.2f}, {upper:+.2f}]')
        self._limits_lbl.setStyleSheet(
            'font-family: monospace; font-size: 10px; color: #666;')
        layout.addWidget(self._limits_lbl)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._sync_slider_from_command()
        self._apply_style()

    # --- Properties ---

    @property
    def joint_index(self) -> int:
        return self._joint_index

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    @property
    def current(self) -> float:
        return self._current_rad

    @property
    def command(self) -> float:
        return self._command_rad

    # --- Public setters ---

    def set_current(self, radians: float) -> None:
        """Update the current position display. If not dirty, command tracks it."""
        self._current_rad = float(radians)
        self._update_current_label()
        if not self._dirty:
            self._set_command_internal(self._current_rad)

    def set_command(self, radians: float, mark_dirty: bool = True) -> None:
        """Set the commanded position programmatically (e.g., Home button)."""
        clamped = max(self._lower, min(self._upper, float(radians)))
        self._dirty = mark_dirty and not math.isclose(clamped, self._current_rad, abs_tol=1e-6)
        self._set_command_internal(clamped)
        self._apply_style()

    def clear_dirty(self) -> None:
        """Mark the row clean — command now tracks current again."""
        self._dirty = False
        self._set_command_internal(self._current_rad)
        self._apply_style()

    def set_selected(self, selected: bool) -> None:
        if selected != self._selected:
            self._selected = selected
            self._apply_style()

    def set_unit_degrees(self, degrees: bool) -> None:
        self._unit_degrees = degrees
        self._update_current_label()

    # --- Internal ---

    def _set_command_internal(self, radians: float) -> None:
        self._command_rad = radians
        self._suppress_edit = True
        try:
            self._spin.setValue(radians)
            self._sync_slider_from_command()
        finally:
            self._suppress_edit = False

    def _sync_slider_from_command(self) -> None:
        span = self._upper - self._lower
        if span <= 0:
            tick = 0
        else:
            tick = int(round((self._command_rad - self._lower) / span * SLIDER_STEPS))
        tick = max(0, min(SLIDER_STEPS, tick))
        self._slider.blockSignals(True)
        self._slider.setValue(tick)
        self._slider.blockSignals(False)

    def _update_current_label(self) -> None:
        if self._unit_degrees:
            self._current_lbl.setText(f'{math.degrees(self._current_rad):+6.1f}\u00b0')
        else:
            self._current_lbl.setText(f'{self._current_rad:+6.3f}')

    def _on_slider_changed(self, tick: int) -> None:
        if self._suppress_edit:
            return
        span = self._upper - self._lower
        value = self._lower + (tick / SLIDER_STEPS) * span
        self._on_user_edit(value)

    def _on_spin_changed(self, value: float) -> None:
        if self._suppress_edit:
            return
        self._on_user_edit(value)

    def _on_user_edit(self, radians: float) -> None:
        clamped = max(self._lower, min(self._upper, float(radians)))
        self._command_rad = clamped
        self._dirty = True
        self._suppress_edit = True
        try:
            self._spin.setValue(clamped)
            self._sync_slider_from_command()
        finally:
            self._suppress_edit = False
        self._apply_style()
        self.command_edited.emit(self._joint_index, clamped)

    def _apply_style(self) -> None:
        if self._selected:
            bg = '#3a4a62'
            border = '3px solid #ff8c1a'
            hover_rule = ''  # don't hover-shift the selected row
        elif self._dirty:
            bg = 'transparent'
            border = '3px solid #c87600'
            hover_rule = 'JointRow:hover { background-color: #2a2a30; }'
        else:
            bg = 'transparent'
            border = '3px solid transparent'
            hover_rule = 'JointRow:hover { background-color: #2a2a30; }'
        self.setStyleSheet(
            f'JointRow {{ background-color: {bg}; border-left: {border}; }}'
            f'{hover_rule}'
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        # Only select when clicking outside the interactive widgets
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.pos())
            if child in (None, self._name_lbl, self._current_lbl, self._limits_lbl):
                self.clicked.emit(self._joint_index)
        super().mousePressEvent(event)
