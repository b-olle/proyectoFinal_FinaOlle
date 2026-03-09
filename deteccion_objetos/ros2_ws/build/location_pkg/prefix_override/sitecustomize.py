import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/baltasar/proyecto final/deteccion_objetos/ros2_ws/install/location_pkg'
