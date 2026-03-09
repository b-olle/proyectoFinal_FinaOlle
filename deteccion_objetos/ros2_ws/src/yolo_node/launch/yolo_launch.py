from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
from launch.actions import DeclareLaunchArgument
import os

def generate_launch_description():
    model_path = LaunchConfiguration('model_path')
    source = LaunchConfiguration('source')
    resolution = LaunchConfiguration('resolution')

    model_arg = DeclareLaunchArgument('model_path', default_value='/home/baltasar/proyecto final/deteccion_objetos/ros2_ws/yolo11n.pt')
    source_arg = DeclareLaunchArgument('source', default_value='usb0')
    res_arg = DeclareLaunchArgument('resolution', default_value='1280x960')

    yolo_node = Node(
        package='yolo_node',
        executable='yolo_detect',
        parameters=[{
            'model_path': model_path,
            'source': source,
            'resolution': resolution
        }]
    )

    return LaunchDescription([model_arg, source_arg, res_arg, yolo_node])

