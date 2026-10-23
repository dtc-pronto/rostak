from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('cot_url', default_value='udp://127.0.0.1:16969'),
        DeclareLaunchArgument('fix_topic', default_value='/fix'),
        DeclareLaunchArgument('cot_params', default_value=PathJoinSubstitution([
            FindPackageShare('rostak'), 'config', 'cot.yaml'])),
        DeclareLaunchArgument('tak_params', default_value=PathJoinSubstitution([
            FindPackageShare('rostak'), 'config', 'tak.yaml'])),
        Node(package='rostak', executable='rostak_bridge', namespace='tak',
             parameters=[LaunchConfiguration('tak_params'),
                         {'COT_URL': LaunchConfiguration('cot_url')}], output='screen'),
        Node(package='rostak', executable='roscot_fix', namespace='tak',
             parameters=[{'cot_params': LaunchConfiguration('cot_params')}],
             remappings=[('fix', LaunchConfiguration('fix_topic'))], output='screen'),
    ])
