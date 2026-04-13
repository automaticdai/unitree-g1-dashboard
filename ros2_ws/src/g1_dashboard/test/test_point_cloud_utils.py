"""Tests for decimate / filter_distance helpers."""

import numpy as np
import pytest

from g1_dashboard.utils.point_cloud_utils import decimate, filter_distance


def test_decimate_passthrough_when_under_budget():
    pts = np.zeros((100, 4), dtype=np.float32)
    out = decimate(pts, 200)
    assert out.shape[0] == 100


def test_decimate_caps_at_budget():
    pts = np.arange(1000 * 4, dtype=np.float32).reshape(1000, 4)
    out = decimate(pts, 100)
    assert out.shape[0] <= 100


def test_decimate_zero_budget_returns_input_unchanged():
    pts = np.zeros((10, 4), dtype=np.float32)
    out = decimate(pts, 0)
    assert out.shape[0] == 10


def test_filter_distance_keeps_only_in_range():
    pts = np.array([
        [1.0, 0.0, 0.0, 0.0],   # d=1
        [3.0, 0.0, 0.0, 0.0],   # d=3
        [10.0, 0.0, 0.0, 0.0],  # d=10
        [0.1, 0.0, 0.0, 0.0],   # d=0.1
    ], dtype=np.float32)
    out = filter_distance(pts, 0.5, 5.0)
    distances = np.linalg.norm(out[:, :3], axis=1)
    assert distances.min() >= 0.5
    assert distances.max() <= 5.0
    assert out.shape[0] == 2


def test_filter_distance_empty_input_passes_through():
    pts = np.zeros((0, 4), dtype=np.float32)
    out = filter_distance(pts, 0.0, 10.0)
    assert out.shape == (0, 4)
