"""4x4 transformation matrix helpers.

All matrices are column-major consistent with OpenGL convention when passed
to `glLoadMatrix` / `glMultMatrix`. Numpy arrays are stored in row-major
(C) layout and transposed at the GL boundary.
"""

from __future__ import annotations

import math

import numpy as np

Mat4 = np.ndarray   # shape (4, 4), float64


def identity() -> Mat4:
    return np.eye(4, dtype=np.float64)


def translation(x: float, y: float, z: float) -> Mat4:
    m = np.eye(4, dtype=np.float64)
    m[0, 3] = x
    m[1, 3] = y
    m[2, 3] = z
    return m


def rotation_axis(axis: np.ndarray, angle: float) -> Mat4:
    """Rotation matrix around a normalized axis vector (Rodrigues' formula)."""
    axis = np.asarray(axis, dtype=np.float64)
    norm = np.linalg.norm(axis)
    if norm < 1e-12:
        return np.eye(4, dtype=np.float64)
    x, y, z = axis / norm
    c = math.cos(angle)
    s = math.sin(angle)
    t = 1.0 - c
    m = np.eye(4, dtype=np.float64)
    m[0, 0] = t * x * x + c
    m[0, 1] = t * x * y - s * z
    m[0, 2] = t * x * z + s * y
    m[1, 0] = t * x * y + s * z
    m[1, 1] = t * y * y + c
    m[1, 2] = t * y * z - s * x
    m[2, 0] = t * x * z - s * y
    m[2, 1] = t * y * z + s * x
    m[2, 2] = t * z * z + c
    return m


def rotation_x(angle: float) -> Mat4:
    return rotation_axis(np.array([1.0, 0.0, 0.0]), angle)


def rotation_y(angle: float) -> Mat4:
    return rotation_axis(np.array([0.0, 1.0, 0.0]), angle)


def rotation_z(angle: float) -> Mat4:
    return rotation_axis(np.array([0.0, 0.0, 1.0]), angle)


def compose(*matrices: Mat4) -> Mat4:
    """Multiply matrices in order: compose(A, B, C) = A @ B @ C."""
    result = matrices[0]
    for m in matrices[1:]:
        result = result @ m
    return result


def transform_point(m: Mat4, p: np.ndarray) -> np.ndarray:
    """Apply a 4x4 transform to a 3D point."""
    p = np.asarray(p, dtype=np.float64)
    v = np.array([p[0], p[1], p[2], 1.0])
    out = m @ v
    if abs(out[3]) > 1e-12:
        out = out / out[3]
    return out[:3]


def quaternion_to_matrix(x: float, y: float, z: float, w: float) -> Mat4:
    """Convert quaternion (x, y, z, w) to a 4x4 rotation matrix."""
    norm = math.sqrt(x * x + y * y + z * z + w * w)
    if norm < 1e-12:
        return np.eye(4, dtype=np.float64)
    x, y, z, w = x / norm, y / norm, z / norm, w / norm

    m = np.eye(4, dtype=np.float64)
    m[0, 0] = 1.0 - 2.0 * (y * y + z * z)
    m[0, 1] = 2.0 * (x * y - z * w)
    m[0, 2] = 2.0 * (x * z + y * w)
    m[1, 0] = 2.0 * (x * y + z * w)
    m[1, 1] = 1.0 - 2.0 * (x * x + z * z)
    m[1, 2] = 2.0 * (y * z - x * w)
    m[2, 0] = 2.0 * (x * z - y * w)
    m[2, 1] = 2.0 * (y * z + x * w)
    m[2, 2] = 1.0 - 2.0 * (x * x + y * y)
    return m


def look_at(eye: np.ndarray, target: np.ndarray, up: np.ndarray) -> Mat4:
    """Build a view matrix (camera facing from eye toward target)."""
    eye = np.asarray(eye, dtype=np.float64)
    target = np.asarray(target, dtype=np.float64)
    up = np.asarray(up, dtype=np.float64)

    forward = target - eye
    forward /= np.linalg.norm(forward)

    right = np.cross(forward, up)
    right_norm = np.linalg.norm(right)
    if right_norm < 1e-12:
        # Up and forward are parallel — pick an arbitrary right
        right = np.array([1.0, 0.0, 0.0])
    else:
        right = right / right_norm

    new_up = np.cross(right, forward)

    m = np.eye(4, dtype=np.float64)
    m[0, 0:3] = right
    m[1, 0:3] = new_up
    m[2, 0:3] = -forward
    m[0, 3] = -np.dot(right, eye)
    m[1, 3] = -np.dot(new_up, eye)
    m[2, 3] = np.dot(forward, eye)
    return m


def perspective(fov_y_rad: float, aspect: float, z_near: float, z_far: float) -> Mat4:
    """Build a perspective projection matrix (OpenGL convention)."""
    f = 1.0 / math.tan(fov_y_rad / 2.0)
    m = np.zeros((4, 4), dtype=np.float64)
    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (z_far + z_near) / (z_near - z_far)
    m[2, 3] = (2.0 * z_far * z_near) / (z_near - z_far)
    m[3, 2] = -1.0
    return m


def ray_point_distance(ray_origin: np.ndarray, ray_dir: np.ndarray,
                       point: np.ndarray) -> float:
    """Minimum distance from a point to an infinite ray."""
    ray_origin = np.asarray(ray_origin, dtype=np.float64)
    ray_dir = np.asarray(ray_dir, dtype=np.float64)
    point = np.asarray(point, dtype=np.float64)

    ray_dir = ray_dir / np.linalg.norm(ray_dir)
    to_point = point - ray_origin
    projected_len = np.dot(to_point, ray_dir)
    if projected_len < 0:
        return float(np.linalg.norm(to_point))
    closest = ray_origin + projected_len * ray_dir
    return float(np.linalg.norm(point - closest))
