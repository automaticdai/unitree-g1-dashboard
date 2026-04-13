"""Tests for color maps and value normalization."""

import numpy as np
import pytest

from g1_dashboard.utils import color_maps


@pytest.mark.parametrize('name', list(color_maps.COLORMAPS.keys()))
def test_colormap_returns_rgb_in_unit_range(name):
    cmap = color_maps.COLORMAPS[name]
    values = np.linspace(0.0, 1.0, 50, dtype=np.float32)
    rgb = cmap(values)
    assert rgb.shape == (50, 3)
    assert rgb.dtype == np.float32
    assert rgb.min() >= 0.0
    assert rgb.max() <= 1.0


@pytest.mark.parametrize('name', list(color_maps.COLORMAPS.keys()))
def test_colormap_handles_out_of_range(name):
    cmap = color_maps.COLORMAPS[name]
    rgb = cmap(np.array([-1.0, 0.0, 0.5, 1.0, 5.0], dtype=np.float32))
    assert rgb.min() >= 0.0
    assert rgb.max() <= 1.0


def test_normalize_basic():
    out = color_maps.normalize(np.array([0.0, 5.0, 10.0]))
    assert pytest.approx(out.tolist()) == [0.0, 0.5, 1.0]


def test_normalize_constant_returns_zeros():
    out = color_maps.normalize(np.array([2.0, 2.0, 2.0]))
    assert (out == 0.0).all()


def test_normalize_empty_returns_empty():
    out = color_maps.normalize(np.array([], dtype=np.float32))
    assert out.size == 0


def test_normalize_with_explicit_bounds():
    out = color_maps.normalize(np.array([0.0, 5.0, 10.0]), vmin=0.0, vmax=20.0)
    assert pytest.approx(out.tolist()) == [0.0, 0.25, 0.5]
