import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory('landxml_viz')
    default_file = os.path.expanduser(
        '~/Puskunrata_Oja_keskella_pohja_160cm_luiskat_1_2_100_45_100_75-0.200.xml')

    return LaunchDescription([
        DeclareLaunchArgument('file_path', default_value=default_file),
        DeclareLaunchArgument('frame_id', default_value='gk24'),
        DeclareLaunchArgument('rviz', default_value='true'),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        Node(
            package='landxml_viz',
            executable='landxml_publisher',
            name='landxml_publisher',
            output='screen',
            parameters=[{
                'file_path': LaunchConfiguration('file_path'),
                'frame_id': LaunchConfiguration('frame_id'),
                'use_sim_time': LaunchConfiguration('use_sim_time'),
            }],
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', os.path.join(share, 'rviz', 'landxml_viz.rviz')],
            parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}],
            condition=IfCondition(LaunchConfiguration('rviz')),
        ),
    ])
