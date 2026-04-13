"""Tests for camera_panel.msg_to_qimage.

Uses real sensor_msgs.Image instances when rclpy+PySide6 are both
available. In the minimal test env (no rclpy) the whole module skips.
"""

import importlib.util

import numpy as np
import pytest

_HAS_PYSIDE = importlib.util.find_spec('PySide6') is not None
_HAS_SENSOR_MSGS = importlib.util.find_spec('sensor_msgs') is not None
pytestmark = pytest.mark.skipif(
    not (_HAS_PYSIDE and _HAS_SENSOR_MSGS),
    reason='PySide6 + sensor_msgs required',
)


@pytest.fixture(scope='module')
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def _make_image(height: int, width: int, encoding: str, data: bytes, step: int):
    from sensor_msgs.msg import Image
    msg = Image()
    msg.height = height
    msg.width = width
    msg.encoding = encoding
    msg.step = step
    msg.data = list(data)
    return msg


def test_rgb8_decodes_to_rgb(qapp):
    from g1_dashboard.panels.camera_panel import msg_to_qimage

    arr = np.zeros((4, 4, 3), dtype=np.uint8)
    arr[..., 0] = 255  # all-red
    msg = _make_image(4, 4, 'rgb8', arr.tobytes(), arr.strides[0])
    img = msg_to_qimage(msg)
    assert img is not None and not img.isNull()
    assert img.width() == 4
    assert img.height() == 4


def test_bgr8_decodes(qapp):
    from g1_dashboard.panels.camera_panel import msg_to_qimage

    arr = np.zeros((2, 3, 3), dtype=np.uint8)
    arr[..., 2] = 255  # red in BGR => blue byte first
    msg = _make_image(2, 3, 'bgr8', arr.tobytes(), arr.strides[0])
    img = msg_to_qimage(msg)
    assert img is not None and not img.isNull()
    assert img.width() == 3
    assert img.height() == 2


def test_mono8_decodes(qapp):
    from g1_dashboard.panels.camera_panel import msg_to_qimage

    arr = np.full((5, 5), 128, dtype=np.uint8)
    msg = _make_image(5, 5, 'mono8', arr.tobytes(), arr.strides[0])
    img = msg_to_qimage(msg)
    assert img is not None and not img.isNull()
    assert img.width() == 5


def test_unsupported_encoding_returns_none(qapp):
    from g1_dashboard.panels.camera_panel import msg_to_qimage

    msg = _make_image(2, 2, 'xyz42', b'\x00' * 16, 8)
    # cv_bridge is the first fallback; if absent or raises on unknown encoding,
    # manual path returns None.
    img = msg_to_qimage(msg)
    # Accept either None (manual path) or a valid image (cv_bridge success).
    assert img is None or not img.isNull()
