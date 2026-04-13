"""Tests for SelectionState.

Requires PySide6 since the class is a QObject with signals.
"""

import importlib.util

import pytest

_HAS_PYSIDE = importlib.util.find_spec('PySide6') is not None
pytestmark = pytest.mark.skipif(not _HAS_PYSIDE, reason='PySide6 required')


def test_initial_state_is_none():
    from g1_dashboard.utils.selection import SelectionState
    s = SelectionState()
    assert s.selected is None


def test_set_selected_updates_value():
    from g1_dashboard.utils.selection import SelectionState
    s = SelectionState()
    s.set_selected(5)
    assert s.selected == 5


def test_clear_resets_to_none():
    from g1_dashboard.utils.selection import SelectionState
    s = SelectionState()
    s.set_selected(5)
    s.clear()
    assert s.selected is None


def test_invalid_index_raises():
    from g1_dashboard.utils.selection import SelectionState
    s = SelectionState()
    with pytest.raises(ValueError):
        s.set_selected(99)
    with pytest.raises(ValueError):
        s.set_selected(-1)


def test_signal_emits_on_change():
    from g1_dashboard.utils.selection import SelectionState
    s = SelectionState()
    received = []
    s.selection_changed.connect(lambda idx: received.append(idx))
    s.set_selected(3)
    s.set_selected(None)
    assert received == [3, -1]


def test_no_signal_on_unchanged_value():
    from g1_dashboard.utils.selection import SelectionState
    s = SelectionState()
    received = []
    s.selection_changed.connect(lambda idx: received.append(idx))
    s.set_selected(3)
    s.set_selected(3)  # same value
    assert received == [3]
