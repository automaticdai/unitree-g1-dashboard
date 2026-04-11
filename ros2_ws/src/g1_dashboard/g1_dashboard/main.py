"""Entry point for the G1 Dashboard application.

Initializes rclpy, starts the ROS2 spin thread, and launches the
PySide6 GUI on the main thread.
"""

import sys
import signal

import rclpy

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from g1_dashboard.dashboard_node import DashboardNode
from g1_dashboard.main_window import MainWindow
from g1_dashboard.utils.qt_ros_bridge import start_ros_spin_thread


def main():
    # Initialize ROS2
    rclpy.init(args=sys.argv)
    node = DashboardNode()

    # Start rclpy spin in background thread
    spin_thread = start_ros_spin_thread(node)

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName('G1 Dashboard')
    app.setOrganizationName('unitree-g1-dashboard')

    # Load dark theme stylesheet
    stylesheet = _load_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)

    # Allow Ctrl+C to kill the app
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Create and show main window
    window = MainWindow(node)
    window.show()

    # Run Qt event loop
    exit_code = app.exec()

    # Cleanup
    node.destroy_node()
    rclpy.try_shutdown()
    sys.exit(exit_code)


def _load_stylesheet() -> str | None:
    """Load the dark theme QSS stylesheet from the package resources."""
    try:
        from ament_index_python.packages import get_package_share_directory
        import os
        share_dir = get_package_share_directory('g1_dashboard')
        qss_path = os.path.join(share_dir, 'resource', 'styles', 'dark_theme.qss')
        if os.path.exists(qss_path):
            with open(qss_path, 'r') as f:
                return f.read()
    except Exception:
        pass

    # Fallback: try loading from source tree (development mode)
    try:
        import os
        source_qss = os.path.join(
            os.path.dirname(__file__), '..', 'resource', 'styles', 'dark_theme.qss'
        )
        if os.path.exists(source_qss):
            with open(source_qss, 'r') as f:
                return f.read()
    except Exception:
        pass

    return None


if __name__ == '__main__':
    main()
