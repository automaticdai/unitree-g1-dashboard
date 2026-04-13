"""Tests for the orbit/pan/zoom camera controller.

Camera logic is pure math — fully testable without Qt or OpenGL.
"""

import math

import numpy as np
import pytest

from g1_dashboard.rendering.camera_controller import CameraController


def test_default_eye_position_above_and_behind():
    cam = CameraController()
    eye = cam.eye_position()
    # Default camera is above and offset from target; verify radius is preserved
    d = np.linalg.norm(eye - cam.target)
    assert d == pytest.approx(cam.DEFAULT_RADIUS, abs=1e-9)


def test_reset_restores_defaults():
    cam = CameraController()
    cam.azimuth = 1.0
    cam.elevation = 0.5
    cam.radius = 5.0
    cam.target = np.array([1.0, 2.0, 3.0])
    cam.reset()
    assert cam.azimuth == cam.DEFAULT_AZIMUTH
    assert cam.elevation == cam.DEFAULT_ELEVATION
    assert cam.radius == cam.DEFAULT_RADIUS


def test_zoom_increases_and_clamps():
    cam = CameraController()
    initial = cam.radius
    cam.zoom(-10.0)   # Zoom way out
    assert cam.radius > initial
    assert cam.radius <= cam.MAX_RADIUS

    cam.zoom(100.0)   # Zoom way in
    assert cam.radius >= cam.MIN_RADIUS


def test_orbit_clamps_elevation():
    cam = CameraController()
    # Drag way up
    cam.orbit(0, -100000)
    assert cam.elevation <= cam.MAX_ELEVATION
    # Drag way down
    cam.orbit(0, 100000)
    assert cam.elevation >= cam.MIN_ELEVATION


def test_pan_moves_target():
    cam = CameraController()
    initial = cam.target.copy()
    cam.pan(50, 0)
    assert not np.allclose(cam.target, initial)


def test_view_matrix_shape():
    cam = CameraController()
    m = cam.view_matrix()
    assert m.shape == (4, 4)


def test_projection_matrix_shape():
    cam = CameraController()
    m = cam.projection_matrix(1.5)
    assert m.shape == (4, 4)


def test_screen_to_ray_center_points_forward():
    cam = CameraController()
    origin, direction = cam.screen_to_ray(320, 240, 640, 480)
    # Direction at the center of the screen should point roughly toward the target
    to_target = cam.target - origin
    to_target /= np.linalg.norm(to_target)
    assert np.dot(direction, to_target) > 0.99   # nearly parallel


def test_screen_to_ray_unit_direction():
    cam = CameraController()
    _, direction = cam.screen_to_ray(100, 100, 640, 480)
    assert abs(np.linalg.norm(direction) - 1.0) < 1e-9
