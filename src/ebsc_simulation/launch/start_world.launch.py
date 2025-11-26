import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    pkg_ebsc_simulation = get_package_share_directory('ebsc_simulation')
    world_file_path = os.path.join(pkg_ebsc_simulation, 'worlds', 'ebsc_world.world')
    world_arg = DeclareLaunchArgument('world', default_value=world_file_path)
    start_gazebo = ExecuteProcess(
        cmd=['gzserver', '--verbose', '-s', 'libgazebo_ros_init.so', '-s', 'libgazebo_ros_factory.so', 
             LaunchConfiguration('world')],
        output='screen'
    )
    return LaunchDescription([world_arg, start_gazebo])