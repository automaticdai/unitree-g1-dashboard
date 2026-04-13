"""Tests for 4x4 transformation matrix helpers."""

import math

import numpy as np
import pytest

from g1_dashboard.utils.transforms import (
    identity, translation, rotation_axis, rotation_x, rotation_y, rotation_z,
    compose, transform_point, quaternion_to_matrix, ray_point_distance,
    perspective, look_at,
)


def test_identity_is_4x4():
    m = identity()
    assert m.shape == (4, 4)
    assert np.allclose(m, np.eye(4))


def test_translation_moves_point():
    m = translation(1.0, 2.0, 3.0)
    p = transform_point(m, np.array([0.0, 0.0, 0.0]))
    assert np.allclose(p, [1.0, 2.0, 3.0])


def test_rotation_x_90_degrees():
    m = rotation_x(math.pi / 2)
    # Y axis should rotate into Z axis
    p = transform_point(m, np.array([0.0, 1.0, 0.0]))
    assert np.allclose(p, [0.0, 0.0, 1.0], atol=1e-9)


def test_rotation_y_90_degrees():
    m = rotation_y(math.pi / 2)
    # Z axis should rotate into X axis
    p = transform_point(m, np.array([0.0, 0.0, 1.0]))
    assert np.allclose(p, [1.0, 0.0, 0.0], atol=1e-9)


def test_rotation_z_90_degrees():
    m = rotation_z(math.pi / 2)
    # X axis should rotate into Y axis
    p = transform_point(m, np.array([1.0, 0.0, 0.0]))
    assert np.allclose(p, [0.0, 1.0, 0.0], atol=1e-9)


def test_rotation_axis_identity_when_angle_zero():
    m = rotation_axis(np.array([0.5, 0.3, 0.8]), 0.0)
    assert np.allclose(m, np.eye(4))


def test_rotation_axis_unnormalized_input():
    # Passing a non-unit axis should still produce a valid rotation
    m = rotation_axis(np.array([0.0, 0.0, 10.0]), math.pi / 2)
    p = transform_point(m, np.array([1.0, 0.0, 0.0]))
    assert np.allclose(p, [0.0, 1.0, 0.0], atol=1e-9)


def test_compose_order():
    # Translate then rotate: (T @ R) @ p != (R @ T) @ p in general
    t = translation(1.0, 0.0, 0.0)
    r = rotation_z(math.pi / 2)
    # compose(T, R) applied to origin: T*R*[0,0,0,1] -> T*[0,0,0,1] -> [1,0,0]
    tr_origin = transform_point(compose(t, r), np.array([0.0, 0.0, 0.0]))
    assert np.allclose(tr_origin, [1.0, 0.0, 0.0])
    # compose(R, T) applied to origin: R*T*[0,0,0,1] -> R*[1,0,0,1] -> [0,1,0]
    rt_origin = transform_point(compose(r, t), np.array([0.0, 0.0, 0.0]))
    assert np.allclose(rt_origin, [0.0, 1.0, 0.0], atol=1e-9)


def test_quaternion_identity():
    m = quaternion_to_matrix(0.0, 0.0, 0.0, 1.0)
    assert np.allclose(m, np.eye(4))


def test_quaternion_90_degrees_around_z():
    # Quaternion for 90 degrees around Z: (0, 0, sin(pi/4), cos(pi/4))
    s = math.sin(math.pi / 4)
    c = math.cos(math.pi / 4)
    m = quaternion_to_matrix(0.0, 0.0, s, c)
    p = transform_point(m, np.array([1.0, 0.0, 0.0]))
    assert np.allclose(p, [0.0, 1.0, 0.0], atol=1e-9)


def test_quaternion_unnormalized():
    # Unnormalized quaternion should be normalized internally
    m = quaternion_to_matrix(0.0, 0.0, 10.0, 0.0)  # 180 rotation around Z, length 10
    p = transform_point(m, np.array([1.0, 0.0, 0.0]))
    assert np.allclose(p, [-1.0, 0.0, 0.0], atol=1e-9)


def test_ray_point_distance_on_ray():
    # Point lies on the ray -> distance is zero
    d = ray_point_distance(
        np.array([0.0, 0.0, 0.0]),
        np.array([1.0, 0.0, 0.0]),
        np.array([5.0, 0.0, 0.0]),
    )
    assert d == pytest.approx(0.0, abs=1e-9)


def test_ray_point_distance_perpendicular():
    d = ray_point_distance(
        np.array([0.0, 0.0, 0.0]),
        np.array([1.0, 0.0, 0.0]),
        np.array([3.0, 2.0, 0.0]),
    )
    assert d == pytest.approx(2.0, abs=1e-9)


def test_ray_point_distance_behind_origin():
    # Point behind ray origin -> returns distance to origin
    d = ray_point_distance(
        np.array([0.0, 0.0, 0.0]),
        np.array([1.0, 0.0, 0.0]),
        np.array([-3.0, 4.0, 0.0]),
    )
    assert d == pytest.approx(5.0, abs=1e-9)


def test_perspective_matrix_shape():
    m = perspective(math.pi / 3, 16.0 / 9.0, 0.1, 100.0)
    assert m.shape == (4, 4)
    assert m[3, 2] == -1.0   # OpenGL projection convention


def test_look_at_basic():
    # Camera at (0, -5, 0) looking at origin, up = Z
    m = look_at(
        np.array([0.0, -5.0, 0.0]),
        np.array([0.0, 0.0, 0.0]),
        np.array([0.0, 0.0, 1.0]),
    )
    # Point at origin should map to (0, 0, -5) in camera space (behind camera)
    p = transform_point(m, np.array([0.0, 0.0, 0.0]))
    assert np.allclose(p, [0.0, 0.0, -5.0], atol=1e-9)
