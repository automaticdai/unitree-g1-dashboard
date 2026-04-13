"""Vectorized colormaps for point cloud coloring.

Each colormap is a function (values: ndarray in [0, 1]) -> (N, 3) float32
RGB array in [0, 1]. Inputs outside [0, 1] are clipped.
"""

from __future__ import annotations

import numpy as np


def _clip01(values: np.ndarray) -> np.ndarray:
    return np.clip(values.astype(np.float32, copy=False), 0.0, 1.0)


def viridis(values: np.ndarray) -> np.ndarray:
    """Approximate Viridis colormap (perceptually uniform, dark->yellow)."""
    v = _clip01(values)
    # Polynomial approximation — close enough for visualization (no matplotlib dep)
    r = -0.002 + 1.20 * v - 0.41 * v**2
    g = 0.00873665 + 1.49 * v - 0.475 * v**2
    b = 0.32 + 1.55 * v - 2.40 * v**2 + 0.43 * v**3
    out = np.stack([r, g, b], axis=-1)
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def jet(values: np.ndarray) -> np.ndarray:
    """Classic Jet colormap (blue->cyan->yellow->red)."""
    v = _clip01(values)
    r = np.clip(1.5 - np.abs(4.0 * v - 3.0), 0.0, 1.0)
    g = np.clip(1.5 - np.abs(4.0 * v - 2.0), 0.0, 1.0)
    b = np.clip(1.5 - np.abs(4.0 * v - 1.0), 0.0, 1.0)
    return np.stack([r, g, b], axis=-1).astype(np.float32)


def turbo(values: np.ndarray) -> np.ndarray:
    """Turbo colormap (Google's improved Jet — better perceptual ordering)."""
    v = _clip01(values)
    r = np.clip(0.13 + v * (4.55 - v * (7.86 - v * 4.20)), 0.0, 1.0)
    g = np.clip(0.09 + v * (2.18 + v * (4.85 - v * 4.96)), 0.0, 1.0)
    b = np.clip(0.30 + v * (4.90 - v * (12.18 - v * 7.94)), 0.0, 1.0)
    return np.stack([r, g, b], axis=-1).astype(np.float32)


COLORMAPS = {
    'Viridis': viridis,
    'Jet': jet,
    'Turbo': turbo,
}


def normalize(values: np.ndarray, vmin: float | None = None,
              vmax: float | None = None) -> np.ndarray:
    """Min-max normalize an array to [0, 1]. Returns zeros if range is empty."""
    if values.size == 0:
        return values.astype(np.float32, copy=False)
    lo = float(np.nanmin(values)) if vmin is None else vmin
    hi = float(np.nanmax(values)) if vmax is None else vmax
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return np.zeros_like(values, dtype=np.float32)
    return ((values - lo) / (hi - lo)).astype(np.float32)
