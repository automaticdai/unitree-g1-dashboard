"""Thread-safe bridge between rclpy callbacks and Qt GUI updates.

rclpy.spin() runs on a background thread. ROS subscription callbacks execute
on that thread and must NOT touch Qt widgets directly. This module provides
a signal-based bridge: callbacks emit Qt signals, which are delivered to
connected slots on the main (GUI) thread via Qt's event loop.
"""

import threading
from typing import Optional

import rclpy
from rclpy.node import Node
from PySide6.QtCore import QThread


def start_ros_spin_thread(node: Node) -> threading.Thread:
    """Start rclpy.spin() in a daemon thread.

    Args:
        node: The ROS2 node to spin.

    Returns:
        The started thread (daemon, will be killed when main thread exits).
    """
    thread = threading.Thread(
        target=_spin_worker,
        args=(node,),
        name='rclpy_spin',
        daemon=True,
    )
    thread.start()
    return thread


def _spin_worker(node: Node) -> None:
    """Worker function for the rclpy spin thread."""
    try:
        rclpy.spin(node)
    except Exception:
        pass  # Node was destroyed or shutdown requested
