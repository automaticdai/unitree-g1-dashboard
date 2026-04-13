"""Tests for JointRow dirty tracking and command behavior.

Requires PySide6 + a QApplication.
"""

import importlib.util

import pytest

_HAS_PYSIDE = importlib.util.find_spec('PySide6') is not None
pytestmark = pytest.mark.skipif(not _HAS_PYSIDE, reason='PySide6 required')


@pytest.fixture(scope='module')
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def test_initial_state(qapp):
    from g1_dashboard.widgets.joint_row import JointRow
    row = JointRow(0, 'test_joint', -1.0, 1.0)
    assert row.joint_index == 0
    assert row.is_dirty is False
    assert row.command == 0.0
    assert row.current == 0.0


def test_set_current_updates_command_when_clean(qapp):
    from g1_dashboard.widgets.joint_row import JointRow
    row = JointRow(0, 'test_joint', -1.0, 1.0)
    row.set_current(0.5)
    assert row.current == 0.5
    assert row.is_dirty is False
    assert row.command == 0.5  # tracks current when clean


def test_user_edit_marks_dirty(qapp):
    from g1_dashboard.widgets.joint_row import JointRow
    row = JointRow(0, 'test_joint', -1.0, 1.0)
    row.set_current(0.2)
    emitted = []
    row.command_edited.connect(lambda idx, v: emitted.append((idx, v)))
    # Simulate user typing a value into the spin box
    row._on_user_edit(0.7)
    assert row.is_dirty is True
    assert row.command == 0.7
    assert emitted == [(0, 0.7)]
    # New current should NOT overwrite command while dirty
    row.set_current(0.3)
    assert row.command == 0.7


def test_clear_dirty_snaps_to_current(qapp):
    from g1_dashboard.widgets.joint_row import JointRow
    row = JointRow(0, 'test_joint', -1.0, 1.0)
    row.set_current(0.4)
    row._on_user_edit(0.9)
    row.clear_dirty()
    assert row.is_dirty is False
    assert row.command == 0.4


def test_set_command_clamps_to_limits(qapp):
    from g1_dashboard.widgets.joint_row import JointRow
    row = JointRow(0, 'test_joint', -1.0, 1.0)
    row.set_command(5.0)
    assert row.command == 1.0
    row.set_command(-5.0)
    assert row.command == -1.0


def test_user_edit_clamped(qapp):
    from g1_dashboard.widgets.joint_row import JointRow
    row = JointRow(0, 'test_joint', -1.0, 1.0)
    row._on_user_edit(2.0)
    assert row.command == 1.0
    assert row.is_dirty is True
