from setuptools import find_packages, setup

package_name = 'yolo_node'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/yolo_launch.py']),
    ],
    install_requires=['setuptools', 'opencv-python', 'ultralytics', 'numpy', 'cv_bridge'],
    zip_safe=True,
    maintainer='baltasar',
    maintainer_email='baltasar@todo.todo',
    description='YOLO Node ROS2',
    license='Apache-2.0',
    tests_require=['pytest'],
    python_requires='>=3.12',
    entry_points={
        'console_scripts': [
        'yolo_detect = yolo_node.yolo_detect_wrapper:main',
        ],
    },
)
