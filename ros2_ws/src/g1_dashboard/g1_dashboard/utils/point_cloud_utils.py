"""PointCloud2 decoding and decimation helpers.

`decode_pointcloud2` returns an (N, K) float32 array with x, y, z and
optionally intensity. Falls back to a manual struct unpack if
sensor_msgs_py is unavailable so unit tests can run without it.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np


def decode_pointcloud2(msg) -> np.ndarray:
    """Decode a sensor_msgs/PointCloud2 to an (N, 4) float32 array.

    Columns: x, y, z, intensity. Intensity is 0.0 if the field is absent.
    NaN/Inf rows are filtered out.
    """
    try:
        from sensor_msgs_py import point_cloud2 as pc2
        field_names = {f.name for f in msg.fields}
        wanted = ['x', 'y', 'z']
        if 'intensity' in field_names:
            wanted.append('intensity')
        records = pc2.read_points(
            msg, field_names=wanted, skip_nans=True)
        # read_points returns a structured ndarray
        arr = np.asarray(records)
        n = arr.shape[0]
        out = np.zeros((n, 4), dtype=np.float32)
        out[:, 0] = arr['x']
        out[:, 1] = arr['y']
        out[:, 2] = arr['z']
        if 'intensity' in arr.dtype.names:
            out[:, 3] = arr['intensity']
        return out
    except ImportError:
        return _manual_decode(msg)


def _manual_decode(msg) -> np.ndarray:
    """Tiny fallback for the standard FLOAT32 xyz(+intensity) layout."""
    import struct
    n = msg.width * msg.height
    field_offsets = {f.name: f.offset for f in msg.fields}
    point_step = msg.point_step
    has_int = 'intensity' in field_offsets
    out = np.zeros((n, 4), dtype=np.float32)
    data = bytes(msg.data)
    fmt = '<f'
    for i in range(n):
        base = i * point_step
        out[i, 0] = struct.unpack_from(fmt, data, base + field_offsets['x'])[0]
        out[i, 1] = struct.unpack_from(fmt, data, base + field_offsets['y'])[0]
        out[i, 2] = struct.unpack_from(fmt, data, base + field_offsets['z'])[0]
        if has_int:
            out[i, 3] = struct.unpack_from(
                fmt, data, base + field_offsets['intensity'])[0]
    finite = np.all(np.isfinite(out[:, :3]), axis=1)
    return out[finite]


def decimate(points: np.ndarray, max_points: int) -> np.ndarray:
    """Return at most max_points rows. Uses simple stride-based decimation."""
    n = points.shape[0]
    if n <= max_points or max_points <= 0:
        return points
    stride = int(np.ceil(n / max_points))
    return points[::stride][:max_points]


def filter_distance(points: np.ndarray, dmin: float, dmax: float) -> np.ndarray:
    """Keep points whose Euclidean distance from origin is in [dmin, dmax]."""
    if points.size == 0:
        return points
    d = np.linalg.norm(points[:, :3], axis=1)
    mask = (d >= dmin) & (d <= dmax)
    return points[mask]
