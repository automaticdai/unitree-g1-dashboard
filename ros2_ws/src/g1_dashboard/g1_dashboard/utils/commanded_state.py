"""Shared commanded-pose state for cross-panel coordination.

The joint control panel owns the commanded position for each of the 29
joints and a "dirty" mask indicating which joints have user-edited
commands differing from the current state. The digital twin panel
observes this to render a ghost overlay of the target pose.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class CommandedState(QObject):
    """Per-joint commanded pose and dirty mask."""

    # Emitted on any change. Payload: (positions[29], dirty_mask[29] as bools).
    commands_changed = Signal(list, list)

    def __init__(self, n_joints: int = 29, parent=None):
        super().__init__(parent)
        self._positions: list[float] = [0.0] * n_joints
        self._dirty: list[bool] = [False] * n_joints

    @property
    def positions(self) -> list[float]:
        return list(self._positions)

    @property
    def dirty(self) -> list[bool]:
        return list(self._dirty)

    def any_dirty(self) -> bool:
        return any(self._dirty)

    def update(self, positions: list[float], dirty: list[bool]) -> None:
        if len(positions) != len(self._positions) or len(dirty) != len(self._dirty):
            raise ValueError('length mismatch in CommandedState.update')
        self._positions = list(positions)
        self._dirty = list(dirty)
        self.commands_changed.emit(self._positions, self._dirty)
