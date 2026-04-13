"""Launch file for the bridge node only (without dashboard GUI)."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'robot_model',
            default_value='g1_29dof_rev_1_0',
            description='Robot URDF model variant',
        ),

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
    ])
