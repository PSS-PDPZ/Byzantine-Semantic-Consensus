import os
import math
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, GroupAction, TimerAction, EmitEvent, LogInfo
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch.events import Shutdown

# --- 配置参数 ---
NUM_UAVS = 12
NUM_BYZANTINE = 3
EXPERIMENT_DURATION = 180.0
UAV_MODEL_PATH = os.path.expanduser("~/.gazebo/models/ebsc_quad/model.sdf")

def generate_launch_description():
    if not os.path.exists(UAV_MODEL_PATH):
        print(f"\n\nERROR: UAV model file not found at {UAV_MODEL_PATH}\n\n")
        return LaunchDescription([])

    pkg_ebsc_simulation = get_package_share_directory('ebsc_simulation')

    start_world = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ebsc_simulation, 'launch', 'start_world.launch.py')
        )
    )

    truth_oracle = Node(
        package='ebsc_brain',
        executable='truth_oracle_node',
        name='truth_oracle',
        output='screen'
    )

    logger_node = Node(
        package='ebsc_brain',
        executable='ebsc_logger',
        name='ebsc_logger',
        output='screen',
        parameters=[{'total_uavs': NUM_UAVS}, {'num_byzantine': NUM_BYZANTINE}]
    )

    spawn_and_brain_actions = []
    for i in range(NUM_UAVS):
        uav_name = f'uav_{i}'
        is_byzantine = (i < NUM_BYZANTINE)
        radius, angle = 8.0, (i / NUM_UAVS) * 2.0 * math.pi
        x, y, z = radius * math.cos(angle), radius * math.sin(angle), 0.5

        spawn_uav = Node(
            package='gazebo_ros',
            executable='spawn_entity.py',
            name=f'spawn_{uav_name}',
            output='screen',
            arguments=['-entity', uav_name, '-file', UAV_MODEL_PATH, '-x', str(x), '-y', str(y), '-z', str(z)]
        )
        
        start_brain = Node(
            package='ebsc_brain',
            executable='uav_node',
            name=f'ebsc_brain_{uav_name}',
            output='screen',
            parameters=[
                {'uav_id': i}, 
                {'uav_name': uav_name}, 
                {'is_byzantine': is_byzantine}, 
                {'total_uavs': NUM_UAVS}, 
                {'num_byzantine': NUM_BYZANTINE}
            ]
        )
        spawn_and_brain_actions.append(GroupAction([spawn_uav, start_brain]))

    shutdown_timer = TimerAction(
        period=EXPERIMENT_DURATION,
        actions=[
            LogInfo(msg=f"Experiment duration of {EXPERIMENT_DURATION} seconds reached. Shutting down."),
            EmitEvent(event=Shutdown(reason='Experiment finished'))
        ]
    )

    ld = LaunchDescription()
    ld.add_action(start_world)
    ld.add_action(TimerAction(period=5.0, actions=[truth_oracle]))
    ld.add_action(TimerAction(period=6.0, actions=[logger_node]))

    for i, stack in enumerate(spawn_and_brain_actions):
        delay = 7.0 + i * 0.5
        ld.add_action(TimerAction(period=delay, actions=[stack]))

    ld.add_action(shutdown_timer)
    
    return ld