"""Tests for CommandedState."""

import importlib.util

import pytest

_HAS_PYSIDE = importlib.util.find_spec('PySide6') is not None
pytestmark = pytest.mark.skipif(not _HAS_PYSIDE, reason='PySide6 required')


def test_initial_state_is_clean():
    from g1_dashboard.utils.commanded_state import CommandedState
    c = CommandedState()
    assert c.positions == [0.0] * 29
    assert c.dirty == [False] * 29
    assert c.any_dirty() is False


def test_update_emits_signal():
    from g1_dashboard.utils.commanded_state import CommandedState
    c = CommandedState()
    received = []
    c.commands_changed.connect(lambda p, d: received.append((list(p), list(d))))

    positions = [0.1] * 29
    dirty = [False] * 29
    dirty[3] = True
    c.update(positions, dirty)

    assert len(received) == 1
    assert received[0][0][3] == 0.1
    assert received[0][1][3] is True
    assert c.any_dirty() is True


def test_update_length_mismatch_raises():
    from g1_dashboard.utils.commanded_state import CommandedState
    c = CommandedState()
    with pytest.raises(ValueError):
        c.update([0.0] * 10, [False] * 29)
    with pytest.raises(ValueError):
        c.update([0.0] * 29, [False] * 10)
