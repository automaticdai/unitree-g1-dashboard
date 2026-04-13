"""Ground plane grid and world-axes renderer (legacy OpenGL)."""

from OpenGL import GL


def draw_grid(size: float = 5.0, step: float = 0.5) -> None:
    """Draw a ground plane grid centered at origin on the XY plane (Z=0)."""
    GL.glDisable(GL.GL_LIGHTING)
    GL.glColor3f(0.28, 0.28, 0.30)
    GL.glLineWidth(1.0)
    GL.glBegin(GL.GL_LINES)
    n = int(size / step)
    for i in range(-n, n + 1):
        x = i * step
        GL.glVertex3f(x, -size, 0.0)
        GL.glVertex3f(x,  size, 0.0)
        GL.glVertex3f(-size, x, 0.0)
        GL.glVertex3f( size, x, 0.0)
    GL.glEnd()


def draw_axes(length: float = 0.3) -> None:
    """Draw world X (red), Y (green), Z (blue) axes at the origin."""
    GL.glDisable(GL.GL_LIGHTING)
    GL.glLineWidth(2.0)
    GL.glBegin(GL.GL_LINES)
    GL.glColor3f(0.9, 0.2, 0.2)  # X
    GL.glVertex3f(0, 0, 0); GL.glVertex3f(length, 0, 0)
    GL.glColor3f(0.2, 0.8, 0.3)  # Y
    GL.glVertex3f(0, 0, 0); GL.glVertex3f(0, length, 0)
    GL.glColor3f(0.3, 0.5, 0.9)  # Z
    GL.glVertex3f(0, 0, 0); GL.glVertex3f(0, 0, length)
    GL.glEnd()
    GL.glLineWidth(1.0)
