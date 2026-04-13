"""Stick-figure robot renderer using legacy OpenGL.

Draws spheres at each joint and cylinders along parent-child link connections.
This is a development-grade visualization that avoids needing the G1 URDF
meshes. Swap in a `MeshRenderer` once URDF+glTF are integrated.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from OpenGL import GL, GLU

from g1_dashboard.utils.kinematics import FKResult, Link, RobotSkeleton


# Colors (R, G, B, alpha) in [0, 1]
COLOR_LINK = (0.55, 0.65, 0.80, 1.0)
COLOR_JOINT = (0.30, 0.55, 0.85, 1.0)
COLOR_JOINT_SELECTED = (1.00, 0.55, 0.10, 1.0)
COLOR_ROOT = (0.85, 0.85, 0.85, 1.0)
COLOR_GHOST = (1.00, 0.55, 0.10, 0.45)  # semi-transparent orange for commanded pose


@dataclass
class RenderOptions:
    joint_radius: float = 0.03
    link_radius: float = 0.018
    sphere_slices: int = 12
    sphere_stacks: int = 8
    cylinder_slices: int = 10


class RobotRenderer:
    """Renders a stick-figure robot from FK results.

    Use inside a `QOpenGLWidget.paintGL()` after the modelview/projection
    matrices are set.
    """

    def __init__(self, skeleton: RobotSkeleton, options: RenderOptions | None = None):
        self._skeleton = skeleton
        self._options = options or RenderOptions()
        self._quadric = None  # lazy-init on first draw (needs GL context)

    def _ensure_quadric(self) -> None:
        if self._quadric is None:
            self._quadric = GLU.gluNewQuadric()
            GLU.gluQuadricNormals(self._quadric, GLU.GLU_SMOOTH)

    def draw(self, fk: FKResult, selected_joint: int | None = None) -> None:
        """Draw the robot given a forward-kinematics result."""
        self._ensure_quadric()

        GL.glEnable(GL.GL_LIGHTING)
        GL.glEnable(GL.GL_LIGHT0)
        GL.glEnable(GL.GL_COLOR_MATERIAL)
        GL.glColorMaterial(GL.GL_FRONT_AND_BACK, GL.GL_AMBIENT_AND_DIFFUSE)

        # Draw links (cylinders between parent & child)
        GL.glColor4f(*COLOR_LINK)
        for link in self._skeleton.links:
            if link.parent is None:
                continue
            p_pos = fk.link_positions.get(link.parent)
            c_pos = fk.link_positions.get(link.name)
            if p_pos is None or c_pos is None:
                continue
            self._draw_cylinder(p_pos, c_pos, self._options.link_radius)

        # Draw joint spheres
        for link in self._skeleton.links:
            pos = fk.link_positions.get(link.name)
            if pos is None:
                continue
            is_selected = (selected_joint is not None
                           and link.joint_index == selected_joint)
            if is_selected:
                GL.glColor4f(*COLOR_JOINT_SELECTED)
            elif link.parent is None:
                GL.glColor4f(*COLOR_ROOT)
            elif link.joint_index is None:
                GL.glColor4f(*COLOR_LINK)
            else:
                GL.glColor4f(*COLOR_JOINT)
            self._draw_sphere(pos, self._options.joint_radius * (1.3 if is_selected else 1.0))

        GL.glDisable(GL.GL_LIGHTING)

    def _draw_sphere(self, position: np.ndarray, radius: float) -> None:
        GL.glPushMatrix()
        GL.glTranslatef(float(position[0]), float(position[1]), float(position[2]))
        GLU.gluSphere(
            self._quadric, radius,
            self._options.sphere_slices, self._options.sphere_stacks)
        GL.glPopMatrix()

    def _draw_cylinder(self, p0: np.ndarray, p1: np.ndarray, radius: float) -> None:
        direction = p1 - p0
        length = float(np.linalg.norm(direction))
        if length < 1e-6:
            return
        direction = direction / length

        GL.glPushMatrix()
        GL.glTranslatef(float(p0[0]), float(p0[1]), float(p0[2]))

        # gluCylinder draws along +Z by default; rotate to align with `direction`.
        z_axis = np.array([0.0, 0.0, 1.0])
        axis = np.cross(z_axis, direction)
        axis_norm = np.linalg.norm(axis)
        if axis_norm > 1e-9:
            angle_deg = np.degrees(np.arccos(np.clip(np.dot(z_axis, direction), -1.0, 1.0)))
            GL.glRotatef(float(angle_deg),
                         float(axis[0] / axis_norm),
                         float(axis[1] / axis_norm),
                         float(axis[2] / axis_norm))
        elif direction[2] < 0:
            # Pointing straight down — 180-degree flip around X
            GL.glRotatef(180.0, 1.0, 0.0, 0.0)

        GLU.gluCylinder(
            self._quadric, radius, radius, length,
            self._options.cylinder_slices, 1)
        GL.glPopMatrix()

    def draw_ghost(self, fk: FKResult) -> None:
        """Overlay a semi-transparent skeleton at a commanded pose."""
        self._ensure_quadric()

        GL.glDisable(GL.GL_LIGHTING)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glDepthMask(GL.GL_FALSE)  # don't occlude the real robot

        GL.glColor4f(*COLOR_GHOST)
        r = self._options.link_radius * 1.3
        for link in self._skeleton.links:
            if link.parent is None:
                continue
            p_pos = fk.link_positions.get(link.parent)
            c_pos = fk.link_positions.get(link.name)
            if p_pos is None or c_pos is None:
                continue
            self._draw_cylinder(p_pos, c_pos, r)

        sphere_r = self._options.joint_radius * 1.25
        for link in self._skeleton.links:
            pos = fk.link_positions.get(link.name)
            if pos is None:
                continue
            self._draw_sphere(pos, sphere_r)

        GL.glDepthMask(GL.GL_TRUE)
        GL.glDisable(GL.GL_BLEND)

    def pick_joint(self, fk: FKResult, ray_origin: np.ndarray,
                   ray_dir: np.ndarray, max_distance: float = 0.08) -> int | None:
        """Find the joint closest to a ray, within `max_distance` meters.

        Returns the joint index, or None if no joint is close enough.
        """
        from g1_dashboard.utils.transforms import ray_point_distance

        best_idx: int | None = None
        best_dist = max_distance
        for idx, pos in fk.joint_positions.items():
            d = ray_point_distance(ray_origin, ray_dir, pos)
            if d < best_dist:
                best_dist = d
                best_idx = idx
        return best_idx
