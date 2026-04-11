"""Launch file for the dashboard GUI only.

Use this when the bridge node is already running separately,
or for testing with fake/recorded data.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_jsp_gui = LaunchConfiguration('use_joint_state_publisher_gui')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_joint_state_publisher_gui',
            default_value='false',
            description='Launch joint_state_publisher_gui for testing without a robot',
        ),

        # Optional: joint_state_publisher_gui for testing
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            condition=IfCondition(use_jsp_gui),
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
