import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from tf2_ros import Buffer, TransformListener
import json
import math
import os

class ObjectLocation(Node):

    def __init__(self):
        super().__init__('object_location')
        
        # 1. Suscripción a los datos de YOLO
        self.subscription = self.create_subscription(
            String,
            '/object_detection_data',
            self.listener_callback,
            10
        )

        # 2. Configurar TF (Para saber dónde está el robot)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # Lista para guardar objetos detectados
        self.detected_objects = []
        
        self.get_logger().info('Location Node iniciado. Esperando detecciones...')

    def listener_callback(self, msg):
        try:
            # Parsear datos de YOLO
            data = json.loads(msg.data)
            dist = data['distance']
            angle_obj_deg = data['angle'] # Angulo relativo al robot
            class_name = data['class']

            # 3. Obtener posición del robot (Transform map -> base_link)
            # Timeout de 1.0s para esperar la transformación
            t = self.tf_buffer.lookup_transform('map', 'base_link', rclpy.time.Time(), rclpy.duration.Duration(seconds=1.0))
            
            # Posición del robot
            rx = t.transform.translation.x
            ry = t.transform.translation.y
            
            # Orientación del robot (Cuaternión a Euler/Yaw)
            q = t.transform.rotation
            # Fórmula rápida para obtener Yaw (eje Z) desde cuaternión
            siny_cosp = 2 * (q.w * q.z + q.x * q.y)
            cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z)
            robot_yaw = math.atan2(siny_cosp, cosy_cosp)

            # 4. Calcular posición GLOBAL del objeto
            # Ángulo total = Orientación Robot + Ángulo Objeto (convertido a radianes)
            total_angle = robot_yaw + math.radians(angle_obj_deg)

            obj_x = rx + dist * math.cos(total_angle)
            obj_y = ry + dist * math.sin(total_angle)

            # Guardar en memoria
            obj_data = {
                "id": len(self.detected_objects) + 1,
                "clase": class_name,
                "x_map": round(obj_x, 3),
                "y_map": round(obj_y, 3),
                "distancia_original": dist
            }
            
            self.detected_objects.append(obj_data)
            self.get_logger().info(f"📍 Guardado: {class_name} en X:{obj_x:.2f}, Y:{obj_y:.2f}")

        except Exception as e:
            self.get_logger().warn(f"No se pudo transformar coordenadas: {e}")

    def save_to_file(self):
        filename = "objetos_encontrados.txt"
        with open(filename, "w") as f:
            f.write("ID | CLASE | X (MAPA) | Y (MAPA)\n")
            f.write("-" * 40 + "\n")
            for obj in self.detected_objects:
                line = f"{obj['id']} | {obj['clase']} | {obj['x_map']} | {obj['y_map']}\n"
                f.write(line)
        
        path = os.path.abspath(filename)
        print(f"\n💾 Archivo guardado exitosamente en: {path}")

def main(args=None):
    rclpy.init(args=args)
    location = ObjectLocation()

    try:
        rclpy.spin(location)
    except KeyboardInterrupt:
        # Aquí entra cuando presionas Ctrl+C
        location.save_to_file()
    finally:
        location.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
