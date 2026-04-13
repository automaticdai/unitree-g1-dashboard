"""Shared selection state with Qt signal for cross-panel coordination.

The digital twin panel and joint control panel both observe and mutate
`selected_joint_index`. Whichever panel changes the value, the other
receives a signal and updates its own visual state.
"""

from PySide6.QtCore import QObject, Signal


class SelectionState(QObject):
    """Holds the currently selected joint index (0-28), or None."""

    # Emitted when the selection changes. Argument: new index, or -1 if None.
    selection_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected: int | None = None

    @property
    def selected(self) -> int | None:
        return self._selected

    def set_selected(self, joint_index: int | None) -> None:
        """Update the selection. Emits selection_changed if it differs."""
        if joint_index is not None and not (0 <= joint_index <= 28):
            raise ValueError(f'joint index {joint_index} out of range 0..28')
        if joint_index == self._selected:
            return
        self._selected = joint_index
        self.selection_changed.emit(-1 if joint_index is None else joint_index)

    def clear(self) -> None:
        self.set_selected(None)
