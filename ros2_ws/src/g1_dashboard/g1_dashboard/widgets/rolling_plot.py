"""Rolling time-series plot widget using pyqtgraph.

Displays up to N traces on a shared time axis with a sliding window.
Handles high-rate (50 Hz) updates without frame drops.
"""

import time
from collections import deque

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QTimer


# Sensible pyqtgraph defaults for dark theme
pg.setConfigOption('background', (30, 30, 30))
pg.setConfigOption('foreground', (200, 200, 200))
pg.setConfigOption('antialias', True)


# Per-axis colors (R, G, B)
AXIS_COLORS = [
    (244, 67, 54),   # red — X
    (76, 175, 80),   # green — Y
    (33, 150, 243),  # blue — Z
]


class RollingPlot(pg.PlotWidget):
    """A pyqtgraph plot showing multiple traces over a sliding time window."""

    def __init__(
        self,
        title: str,
        trace_names: list[str],
        y_label: str = '',
        window_seconds: float = 10.0,
        max_samples: int = 600,
        parent=None,
    ):
        super().__init__(parent)

        self._window = window_seconds
        self._max_samples = max_samples
        self._start_time = time.monotonic()

        self.setTitle(title, size='10pt')
        self.setLabel('left', y_label)
        self.setLabel('bottom', 'time (s)')
        self.showGrid(x=True, y=True, alpha=0.2)
        self.setMenuEnabled(False)
        self.setMouseEnabled(x=False, y=False)
        self.addLegend(offset=(5, 5), labelTextSize='8pt')

        self._times: deque[float] = deque(maxlen=max_samples)
        self._traces: list[deque[float]] = [
            deque(maxlen=max_samples) for _ in trace_names
        ]
        self._curves: list[pg.PlotDataItem] = []
        for i, name in enumerate(trace_names):
            color = AXIS_COLORS[i % len(AXIS_COLORS)]
            pen = pg.mkPen(color=color, width=1.5)
            curve = self.plot([], [], pen=pen, name=name)
            self._curves.append(curve)

        # Throttled redraw — sample rate (50 Hz) exceeds useful screen
        # refresh; redraw at ~30 Hz max to save CPU.
        self._dirty = False
        self._redraw_timer = QTimer(self)
        self._redraw_timer.timeout.connect(self._redraw)
        self._redraw_timer.start(33)  # ~30 FPS

    def append(self, values: list[float]) -> None:
        """Append a new data point (one value per trace) at the current time."""
        t = time.monotonic() - self._start_time
        self._times.append(t)
        for i, v in enumerate(values[:len(self._traces)]):
            self._traces[i].append(float(v))
        self._dirty = True

    def _redraw(self) -> None:
        if not self._dirty or not self._times:
            return
        self._dirty = False

        times = np.fromiter(self._times, dtype=float)
        t_now = times[-1]
        t_min = t_now - self._window
        mask = times >= t_min
        if not mask.any():
            return
        visible_times = times[mask]

        for curve, trace in zip(self._curves, self._traces):
            data = np.fromiter(trace, dtype=float)
            curve.setData(visible_times, data[mask])

        self.setXRange(t_min, t_now, padding=0)

    def clear_data(self) -> None:
        """Clear all traces."""
        self._times.clear()
        for trace in self._traces:
            trace.clear()
        for curve in self._curves:
            curve.setData([], [])
