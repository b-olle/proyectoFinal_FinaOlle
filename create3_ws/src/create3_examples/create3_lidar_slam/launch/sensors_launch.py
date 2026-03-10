from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # Evaluate at launch the value of the launch configuration 'namespace'
    namespace = LaunchConfiguration('namespace')

    # Declares an action to allow users to pass the robot namespace from the
    # CLI into the launch description as an argument.
    namespace_argument = DeclareLaunchArgument(
        'namespace',
        default_value='',
        description='Robot namespace')

    # Declares an action that will launch a node when executed by the launch description.
    # This node is responsible for providing a static transform from the robot's base_link
    # frame to a new laser_frame, which will be the coordinate frame for the lidar.
    static_transform_node = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        arguments=[
                '--x', '0.0',  
                '--y', '0.0',
                '--z', '0.13', # unidad [m]
                '--qx', '0.0',
                '--qy', '0.0',
                '--qz', '0.0',
                '--qw', '1.0',
                '--frame-id', 'base_link',
                '--child-frame-id', 'laser_frame'
        ],

        # Remaps topics used by the 'tf2_ros' package from absolute (with slash) to relative (no slash).
        # This is necessary to use namespaces with 'tf2_ros'.
        remappings=[
            ('/tf_static', 'tf_static'),
            ('/tf', 'tf')],
        namespace=namespace
    )

    # Declares an action that will launch a node when executed by the launch description.
    # This node is responsible for configuring the LDLidar sensor.
    ldlidar_node = Node(
      package='ldlidar_stl_ros2',
      executable='ldlidar_stl_ros2_node',
      name='LD19',
      output='screen',
      arguments=['--ros-args', '--log-level', 'WARN'],
      parameters=[
        {'product_name': 'LDLiDAR_LD19'},
        {'topic_name': 'scan'},
        {'port_name': '/dev/ttyUSB0'},
        {'frame_id': 'laser_frame'},
        {'laser_scan_dir': True},
        {'enable_angle_crop_func': False},
        {'angle_crop_min': 135.0},
        {'angle_crop_max': 225.0},
        {'use_sim_time': False}
      ],
      namespace=namespace
    )

    # Launches all named actions
    return LaunchDescription([
        namespace_argument,
        static_transform_node,
        TimerAction(
            period=2.0,
            actions=[ldlidar_node]
        )
    ])
