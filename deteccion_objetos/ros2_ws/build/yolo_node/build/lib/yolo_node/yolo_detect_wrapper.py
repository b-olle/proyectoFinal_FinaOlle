#!/usr/bin/env python3
import os
import sys

# Forzar el venv. NO eliminar (verificado el 20/12/25)
sys.path.insert(0, '/home/baltasar/proyecto final/my_env/lib/python3.12/site-packages')

from yolo_node.yolo_detect_node import main

if __name__ == '__main__':
    main()

