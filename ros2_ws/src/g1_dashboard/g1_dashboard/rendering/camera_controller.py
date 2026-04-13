"""Orbit/pan/zoom camera controller for the 3D viewports.

State is represented in spherical coordinates around a target point:
    eye = target + radius * [cos(elev)*sin(azim), cos(elev)*cos(azim), sin(elev)]
with Z up and X forward by default.
"""

from __future__ import annotations

import math

import numpy as np

from g1_dashboard.utils.transforms import Mat4, look_at, perspective


class CameraController:
    """Orbit camera around a target point."""

    # Initial camera pose: 2m back, 1.5m up, looking at waist height
    DEFAULT_AZIMUTH = math.radians(30.0)    # Around Z axis (yaw)
    DEFAULT_ELEVATION = math.radians(20.0)  # From XY plane up
    DEFAULT_RADIUS = 2.8                    # meters
    DEFAULT_TARGET = np.array([0.0, 0.0, 0.8])

    MIN_RADIUS = 0.3
    MAX_RADIUS = 10.0
    MIN_ELEVATION = math.radians(-80.0)
    MAX_ELEVATION = math.radians(89.0)

    def __init__(self):
        self.azimuth = self.DEFAULT_AZIMUTH
        self.elevation = self.DEFAULT_ELEVATION
        self.radius = self.DEFAULT_RADIUS
        self.target = self.DEFAULT_TARGET.copy()

        self.fov_y = math.radians(45.0)
        self.z_near = 0.05
        self.z_far = 50.0

    def reset(self) -> None:
        self.azimuth = self.DEFAULT_AZIMUTH
        self.elevation = self.DEFAULT_ELEVATION
        self.radius = self.DEFAULT_RADIUS
        self.target = self.DEFAULT_TARGET.copy()

    def eye_position(self) -> np.ndarray:
        """Compute camera eye position from spherical coordinates."""
        ce = math.cos(self.elevation)
        se = math.sin(self.elevation)
        ca = math.cos(self.azimuth)
        sa = math.sin(self.azimuth)
        offset = self.radius * np.array([ce * sa, ce * ca, se])
        return self.target + offset

    def view_matrix(self) -> Mat4:
        return look_at(self.eye_position(), self.target, np.array([0.0, 0.0, 1.0]))

    def projection_matrix(self, aspect: float) -> Mat4:
        return perspective(self.fov_y, aspect, self.z_near, self.z_far)

    # --- Mouse gestures ---

    def orbit(self, dx_pixels: float, dy_pixels: float,
              sensitivity: float = 0.01) -> None:
        """Rotate camera around target. dx -> azimuth, dy -> elevation."""
        self.azimuth -= dx_pixels * sensitivity
        self.elevation += dy_pixels * sensitivity
        self.elevation = max(self.MIN_ELEVATION, min(self.MAX_ELEVATION, self.elevation))

    def pan(self, dx_pixels: float, dy_pixels: float,
            sensitivity: float = 0.003) -> None:
        """Translate target point in the camera's view plane."""
        # Camera-space right/up vectors
        eye = self.eye_position()
        forward = self.target - eye
        forward_norm = np.linalg.norm(forward)
        if forward_norm < 1e-9:
            return
        forward /= forward_norm
        right = np.cross(forward, np.array([0.0, 0.0, 1.0]))
        right_norm = np.linalg.norm(right)
        if right_norm > 1e-9:
            right /= right_norm
        up = np.cross(right, forward)
        self.target = (self.target
                       - right * dx_pixels * sensitivity * self.radius
                       + up * dy_pixels * sensitivity * self.radius)

    def zoom(self, delta: float, sensitivity: float = 0.1) -> None:
        """Zoom in/out. Positive delta zooms in (scroll up)."""
        factor = math.exp(-delta * sensitivity)
        self.radius = max(self.MIN_RADIUS, min(self.MAX_RADIUS, self.radius * factor))

    def screen_to_ray(self, screen_x: float, screen_y: float,
                      viewport_w: int, viewport_h: int) -> tuple[np.ndarray, np.ndarray]:
        """Convert screen pixel coordinates to a world-space ray.

        Args:
            screen_x, screen_y: pixel coords (top-left origin, Qt convention)
            viewport_w, viewport_h: viewport size in pixels

        Returns:
            (ray_origin, ray_direction) — both world-space 3-vectors.
        """
        # Normalize to NDC [-1, 1], flipping Y (Qt is top-down; NDC is bottom-up)
        ndc_x = (2.0 * screen_x / viewport_w) - 1.0
        ndc_y = 1.0 - (2.0 * screen_y / viewport_h)

        # Camera frame vectors
        eye = self.eye_position()
        forward = self.target - eye
        forward_norm = np.linalg.norm(forward)
        if forward_norm < 1e-9:
            return eye, np.array([0.0, 1.0, 0.0])
        forward /= forward_norm
        right = np.cross(forward, np.array([0.0, 0.0, 1.0]))
        right_norm = np.linalg.norm(right)
        if right_norm < 1e-9:
            right = np.array([1.0, 0.0, 0.0])
        else:
            right /= right_norm
        up = np.cross(right, forward)

        aspect = viewport_w / max(viewport_h, 1)
        tan_half_fov = math.tan(self.fov_y / 2.0)
        dir_world = (forward
                     + right * ndc_x * tan_half_fov * aspect
                     + up * ndc_y * tan_half_fov)
        dir_world = dir_world / np.linalg.norm(dir_world)
        return eye, dir_world
