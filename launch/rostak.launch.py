import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node, PushRosNamespace
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    tak_params_arg = DeclareLaunchArgument(
        'tak_params',
        default_value=PathJoinSubstitution([
            FindPackageShare('rostak'),
            'config',
            'tak.yaml'
        ]),
        description='Path to TAK parameters file'
    )

    cot_params_arg = DeclareLaunchArgument(
        'cot_params',
        default_value=PathJoinSubstitution([
            FindPackageShare('rostak'),
            'config',
            'cot.yaml'
        ]),
        description='Path to CoT parameters file'
    )
     
    fix_rate_arg = DeclareLaunchArgument(
        'fix_rate',
        default_value='0.2',
        description='Fix rate in Hz'
    )
    
    # Get launch configurations
    tak_params = LaunchConfiguration('tak_params')
    cot_params = LaunchConfiguration('cot_params')
    fix_rate = LaunchConfiguration('fix_rate')
    
    # Define nodes
    rostak_bridge_node = Node(
        package='rostak',
        executable='rostak_bridge',
        name='rostak_bridge',
        output='screen',
        parameters=[tak_params],
        env={'DEBUG': 'false'}
    )
    
    roscot_fix_node = Node(
        package='rostak',
        executable='roscot_fix',
        name='roscot_fix',
        output='screen',
        parameters=[{
            'cot_params': cot_params,
            'rate': fix_rate
        }],
        remappings=[('fix', 'fix')]
    )
    
    
    # Group nodes under 'tak' namespace
    tak_group = GroupAction([
        PushRosNamespace('tak'),
        rostak_bridge_node,
        roscot_fix_node,
    ])
    
    return LaunchDescription([
        tak_params_arg,
        cot_params_arg,
        fix_rate_arg,
        tak_group
    ])
