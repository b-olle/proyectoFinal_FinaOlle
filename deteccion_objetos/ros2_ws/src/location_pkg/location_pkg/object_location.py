import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from tf2_ros import Buffer, TransformListener
from visualization_msgs.msg import Marker, MarkerArray
import json
import math
import os


class ObjectLocation(Node):

    def __init__(self):
        super().__init__('object_location')

        # --- PARÁMETROS ---
        self.DISTANCE_THRESHOLD = 0.5

        # Offset del texto (SIEMPRE a la derecha del marker)
        self.TEXT_OFFSET_X = 0.4
        self.TEXT_OFFSET_Y = 0.0
        self.TEXT_Z = 0.25

        self.subscription = self.create_subscription(
            String,
            '/object_detection_data',
            self.listener_callback,
            10
        )

        self.marker_pub = self.create_publisher(MarkerArray, '/object_markers', 10)
        self.marker_array = MarkerArray()
        self.marker_id_counter = 0

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.detected_objects = []

        # --- COLORES FIJOS ---
        self.fixed_colors = {
            "una planta": (0.0, 0.8, 0.0),
            "un reloj": (0.0, 0.0, 0.0),
            "una botella": (0.0, 0.2, 1.0),
            "una banana": (1.0, 1.0, 0.0),
            "una florero": (1.0, 0.0, 0.0),
            "un libro": (1.0, 1.0, 1.0),
            "una copa": (1.0, 0.5, 0.0),
        }

        # --- PALETA AUTOMÁTICA ---
        self.palette = [
            (0.121, 0.466, 0.705),
            (1.000, 0.498, 0.054),
            (0.172, 0.627, 0.172),
            (0.839, 0.153, 0.157),
            (0.580, 0.404, 0.741),
            (0.549, 0.337, 0.294),
            (0.890, 0.467, 0.761),
            (0.498, 0.498, 0.498),
            (0.737, 0.741, 0.133),
            (0.090, 0.745, 0.811),
        ]

        self.class_colors = {}
        self.next_color_idx = 0

        self.get_logger().info("Location Node activo")

    # -----------------------------

    def strip_article(self, label: str) -> str:
        s = (label or "").strip()
        if s.lower().startswith("una "):
            return s[4:].strip()
        if s.lower().startswith("un "):
            return s[3:].strip()
        return s

    def get_color_for_class(self, class_label):
        if class_label in self.fixed_colors:
            return self.fixed_colors[class_label]

        if class_label in self.class_colors:
            return self.class_colors[class_label]

        color = self.palette[self.next_color_idx % len(self.palette)]
        self.class_colors[class_label] = color
        self.next_color_idx += 1
        return color

    def is_duplicate(self, new_x, new_y, class_label):
        for obj in self.detected_objects:
            dist = math.sqrt((new_x - obj['x_map'])**2 + (new_y - obj['y_map'])**2)
            if dist < self.DISTANCE_THRESHOLD and class_label == obj['clase']:
                return True
        return False

    # -----------------------------

    def listener_callback(self, msg):
        try:
            data = json.loads(msg.data)

            dist = data['distance']
            angle_obj_deg = data['angle']
            class_label_es = data['class']  # ya viene en español con artículo

            class_label_rviz = self.strip_article(class_label_es)

            t = self.tf_buffer.lookup_transform(
                'map',
                'base_link',
                rclpy.time.Time(),
                rclpy.duration.Duration(seconds=1.0)
            )

            rx = t.transform.translation.x
            ry = t.transform.translation.y

            q = t.transform.rotation
            siny_cosp = 2 * (q.w * q.z + q.x * q.y)
            cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z)
            robot_yaw = math.atan2(siny_cosp, cosy_cosp)

            total_angle = robot_yaw + math.radians(angle_obj_deg)
            obj_x = rx + dist * math.cos(total_angle)
            obj_y = ry + dist * math.sin(total_angle)

            if self.is_duplicate(obj_x, obj_y, class_label_es):
                return

            obj_data = {
                "id": self.marker_id_counter,
                "clase": class_label_es,
                "x_map": round(obj_x, 3),
                "y_map": round(obj_y, 3)
            }
            self.detected_objects.append(obj_data)

            r, g, b = self.get_color_for_class(class_label_es)

            # -------- ESFERA --------
            sphere_marker = Marker()
            sphere_marker.header.frame_id = "map"
            sphere_marker.header.stamp = self.get_clock().now().to_msg()
            sphere_marker.id = self.marker_id_counter * 2
            sphere_marker.type = Marker.SPHERE
            sphere_marker.action = Marker.ADD
            sphere_marker.pose.position.x = obj_x
            sphere_marker.pose.position.y = obj_y
            sphere_marker.pose.position.z = 0.1
            sphere_marker.scale.x = 0.2
            sphere_marker.scale.y = 0.2
            sphere_marker.scale.z = 0.2
            sphere_marker.color.a = 1.0
            sphere_marker.color.r = r
            sphere_marker.color.g = g
            sphere_marker.color.b = b

            # -------- TEXTO (A LA DERECHA) --------
            text_marker = Marker()
            text_marker.header.frame_id = "map"
            text_marker.header.stamp = self.get_clock().now().to_msg()
            text_marker.id = (self.marker_id_counter * 2) + 1
            text_marker.type = Marker.TEXT_VIEW_FACING
            text_marker.action = Marker.ADD
            text_marker.text = class_label_rviz
            text_marker.pose.position.x = obj_x + self.TEXT_OFFSET_X
            text_marker.pose.position.y = obj_y + self.TEXT_OFFSET_Y
            text_marker.pose.position.z = self.TEXT_Z
            text_marker.scale.z = 0.15
            text_marker.color.a = 1.0
            text_marker.color.r = r
            text_marker.color.g = g
            text_marker.color.b = b

            self.marker_array.markers.append(sphere_marker)
            self.marker_array.markers.append(text_marker)
            self.marker_pub.publish(self.marker_array)

            self.get_logger().info(
                f"📍 Registrado: {class_label_es} en (x={obj_x:.3f}, y={obj_y:.3f})"
            )

            self.marker_id_counter += 1

        except Exception as e:
            self.get_logger().warn(f"Error: {e}")

    # -----------------------------

    def save_to_file(self):
        filename = "objetos_encontrados.txt"
        with open(filename, "w") as f:
            f.write("ID | CLASE | X | Y\n")
            f.write("-" * 40 + "\n")
            for obj in self.detected_objects:
                f.write(f"{obj['id']} | {obj['clase']} | {obj['x_map']} | {obj['y_map']}\n")
        print(f"\n💾 Guardado en: {os.path.abspath(filename)}")


def main(args=None):
    rclpy.init(args=args)
    location = ObjectLocation()
    try:
        rclpy.spin(location)
    except KeyboardInterrupt:
        location.save_to_file()
    finally:
        location.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

