# Proyecto Final: Sistema de mapeo y detección de objetos con robot móvil

Este proyecto consiste en el desarrollo de un robot móvil integrado con **ROS 2** que utiliza visión artificial para la detección y localización de objetos en tiempo real.

##  Tecnologías utilizadas
* **Sistema Operativo:** Ubuntu 22.04 / 24.04
* **Middleware:** ROS 2 (Humble/Jazzy)
* **Visión:** YOLO (You Only Look Once)
* **Lenguajes:** Python / C++
* **Hardware:** PC, Raspberry Pi 4, rpicam, sensor LiDAR LD19

##  Estructura del Repositorio
* `deteccion_objetos/`: Contiene los nodos de visión y el workspace de ROS 2.
* `location_pkg/`: Paquete encargado de la triangulación y posición del objeto.
* `create3_ws/`: Workspace para sensor LiDAR y mapeo SLAM.

##  Instalación y Uso sobre PC

### Dependencias Previas
Para la navegación y planificación, es necesario contar con el paquete `nav2_bringup`. Podés instalarlo mediante `apt` (reemplazá `<distro>` por tu versión de ROS 2, ej. `humble` o `jazzy`):
```bash
sudo apt install ros-<distro>-nav2-bringup

Para ejecutar este proyecto en local, cloná el repositorio y compilá el workspace:

```bash
# Clonar el repositorio
git clone [https://github.com/b-olle/proyectoFinal_FinaOlle.git](https://github.com/b-olle/proyectoFinal_FinaOlle.git)

# Compilar el workspace de ROS 2
cd proyecto\ final/deteccion_objetos/ros2_ws
colcon build
source install/setup.bash

# Lanzar el nodo principal
ros2 run yolo_node yolo_detect_node

```
##  Instalación y Uso sobre rpi4
### Dependencias Previas
Para ejecutar el nodo ROS de la cámara, es necesario contar con el paquete `v4l2_camera`. Podés instalarlo mediante `apt` (reemplazá `<distro>` por tu versión de ROS 2, ej. `humble` o `jazzy`):
```bash
sudo apt install ros-<distro>-v4l2-camera

Para nodos sensor LiDAR y ejecución de SLAM:
```bash
# Compilar el workspace del Create 3
cd proyecto\ final/create3_ws
colcon build
source install/setup.bash

# Lanzar drivers de sensores (LIDAR LD19 y cámara)
ros2 launch create3_lidar_slam sensors_launch.py

# Iniciar SLAM para generación de mapa
ros2 launch create3_lidar_slam slam_toolbox_launch.py

```
##  Integrantes
Este proyecto fue desarrollado para la carrera de Ingeniería Electrónica por:

* **Baltasar Ollé** - [b-olle](https://github.com/b-olle)
* **Facundo Fina** - [FacuFina](https://github.com/FacuFina)

---
