"""Launch file for the full G1 dashboard stack.

Starts: robot_state_publisher + g1_dashboard_bridge + g1_dashboard GUI.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    robot_model = LaunchConfiguration('robot_model')

    return LaunchDescription([
        DeclareLaunchArgument(
            'robot_model',
            default_value='g1_29dof_rev_1_0',
            description='Robot URDF model variant (e.g., g1_29dof_rev_1_0, g1_23dof_rev_1_0)',
        ),

        # Robot state publisher (URDF -> TF)
        # Note: Requires URDF file to be available in g1_dashboard/resource/urdf/
        # For now this is a placeholder — uncomment when URDF files are added:
        # Node(
        #     package='robot_state_publisher',
        #     executable='robot_state_publisher',
        #     parameters=[{
        #         'robot_description': Command([
        #             'cat ', FindPackageShare('g1_dashboard'),
        #             '/resource/urdf/', robot_model, '.urdf'
        #         ])
        #     }],
        # ),

        # Bridge node (Phase 2 — uncomment when implemented)
        # Node(
        #     package='g1_dashboard_bridge',
        #     executable='g1_dashboard_bridge_node',
        #     parameters=[
        #         os.path.join(
        #             get_package_share_directory('g1_dashboard_bridge'),
        #             'config', 'bridge_params.yaml'
        #         )
        #     ],
        # ),

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
