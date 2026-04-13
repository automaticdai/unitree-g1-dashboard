"""Launch file for the full G1 dashboard stack.

Starts g1_dashboard_bridge + g1_dashboard GUI. Optionally starts the
simulator for hardware-free testing when `use_simulator:=true`.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_simulator = LaunchConfiguration('use_simulator')

    return LaunchDescription([
        DeclareLaunchArgument(
            'robot_model',
            default_value='g1_29dof_rev_1_0',
            description='Robot URDF model variant',
        ),
        DeclareLaunchArgument(
            'use_simulator',
            default_value='false',
            description='Launch the Python simulator for hardware-free testing',
        ),

        # Bridge node (always runs — validates joint commands + publishes safety status)
        Node(
            package='g1_dashboard_bridge',
            executable='g1_dashboard_bridge_node',
            name='g1_dashboard_bridge',
            parameters=[
                os.path.join(
                    get_package_share_directory('g1_dashboard_bridge'),
                    'config', 'bridge_params.yaml'
                )
            ],
            output='screen',
        ),

        # Simulator — fake robot telemetry
        Node(
            package='g1_dashboard',
            executable='simulator',
            name='g1_simulator',
            condition=IfCondition(use_simulator),
            output='screen',
        ),

        # Dashboard GUI
        Node(
            package='g1_dashboard',
            executable='dashboard',
            name='g1_dashboard',
            parameters=[
                os.path.join(
                    get_package_share_directory('g1_dashboard'),
                    'config', 'dashboard_params.yaml'
                )
            ],
            output='screen',
        ),
    ])
