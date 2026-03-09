import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, LaserScan 
from cv_bridge import CvBridge
import cv2
from ultralytics import YOLO
from sensor_msgs.msg import CompressedImage
import numpy as np
from collections import deque, Counter
import math

class YOLONode(Node):

    def __init__(self):
        super().__init__('yolo_node')

        # Parámetros ROS2
        self.declare_parameter('model_path', '')
        self.declare_parameter('source', '')
        self.declare_parameter('resolution', '')

        self.model_path = self.get_parameter('model_path').get_parameter_value().string_value
        self.user_res = self.get_parameter('resolution').get_parameter_value().string_value

        # Cargar modelo YOLO
        self.model = YOLO(self.model_path)
        self.bridge = CvBridge()
        
        # Lista de clases permitidas (Casa)
        '''self.target_classes = [
            0, 15, 16, 24, 25, 26, 28, 39, 40, 41, 42, 43, 44, 45,
            46, 47, 48, 49, 51, 53, 55, 56, 58, 62, 63, 64, 65, 66, 
            67, 73, 74, 75, 76, 77, 78, 79
        ]'''
        
        self.target_classes = [
            15, 16, 24, 25, 26, 28, 39, 40, 41, 42, 43, 44, 45,
            46, 47, 48, 49, 51, 53, 55, 58, 62, 63, 64, 65, 66, 
            67, 73, 74, 75, 76, 77, 78, 79
        ]
                
        # Variables para detección estable
        self.CONFIRMATION_LIMIT = 10
        
        # Historial de las últimas 10 detecciones
        self.detection_history = deque(maxlen=self.CONFIRMATION_LIMIT)
        
        # --- NUEVO: PARÁMETROS LIDAR Y CÁMARA ---
        self.latest_scan = None
        self.CAMERA_FOV_HORIZ = 62.2 
        self.LIDAR_OFFSET_ANGLE = math.radians(0.0)
        
        # Suscripción al Lidar
        self.scan_sub = self.create_subscription(
            LaserScan,
            '/scan',
            self.scan_callback,
            10
        )

        self.traductor = {
            'person': 'una persona', 'cat': 'un gato', 'dog': 'un perro',
            'backpack': 'una mochila', 'umbrella': 'un paraguas', 'handbag': 'un bolso', 'suitcase': 'una valija',
            'bottle': 'una botella', 'wine glass': 'una copa', 'cup': 'una taza', 'fork': 'un tenedor',
            'knife': 'un cuchillo', 'spoon': 'una cuchara', 'bowl': 'un bowl',
            'banana': 'una banana', 'apple': 'una manzana', 'sandwich': 'un sándwich', 'orange': 'una naranja',
            'carrot': 'una zanahoria', 'pizza': 'una pizza', 'cake': 'una torta',
            'chair': 'una silla', 'potted plant': 'una planta',
            'tv': 'una TV', 'laptop': 'una notebook', 'mouse': 'un mouse', 'remote': 'un control remoto',
            'keyboard': 'un teclado', 'cell phone': 'un celular',
            'book': 'un libro', 'clock': 'un reloj', 'vase': 'un florero', 'scissors': 'una tijera',
            'teddy bear': 'un peluche', 'hair drier': 'un secador', 'toothbrush': 'un cepillo de dientes'
        }
        
        # Subscripción a imagen
        self.image_sub = self.create_subscription(
            CompressedImage,
            '/image_raw/compressed',
            self.callback,
            1
        )
        
        # Publicación de resultados
        self.image_pub = self.create_publisher(Image, '/image_out', 1)

        self.get_logger().info(f'YOLO Node iniciado con modelo: {self.model_path}')

    def scan_callback(self, msg):
        self.latest_scan = msg

    # <--- MODIFICADO: Se agrega argumento img_timestamp para sincronizar
    def get_distance_to_bbox(self, bbox, img_width, img_timestamp):
        """
        Calcula distancia promedio manejando el cruce por cero (0 grados) del Lidar.
        """
        if self.latest_scan is None:
            return None

        # <--- MODIFICADO: TIME SYNC (Verificar que el scan no sea viejo) ---
        scan_time = self.latest_scan.header.stamp.sec + self.latest_scan.header.stamp.nanosec * 1e-9
        if abs(img_timestamp - scan_time) > 0.3: # Tolerancia de 0.3s
            return None 
        # ------------------------------------------------------------------

        # 1. Datos básicos
        x_min, _, x_max, _ = bbox
        msg = self.latest_scan
        
        # Factor de conversión
        pixels_per_degree = img_width / self.CAMERA_FOV_HORIZ
        center_pixel = img_width / 2.0
        
        # 2. Calcular ángulos
        angle_left_deg = (center_pixel - x_min) / pixels_per_degree 
        angle_right_deg = (center_pixel - x_max) / pixels_per_degree

        # 3. Función auxiliar para obtener índice en el array del Lidar
        def get_index(angle_deg):
            rad = math.radians(angle_deg) + self.LIDAR_OFFSET_ANGLE
            if rad < 0: rad += 2 * math.pi
            elif rad >= 2 * math.pi: rad -= 2 * math.pi
            idx = int((rad - msg.angle_min) / msg.angle_increment)
            return max(0, min(len(msg.ranges) - 1, idx))

        # 4. Obtenemos índices
        idx_start = get_index(angle_right_deg)
        idx_end = get_index(angle_left_deg)
        
        measurements = []

        # 5. Extracción inteligente
        if idx_start > idx_end:
            measurements = msg.ranges[idx_start:] + msg.ranges[:idx_end + 1]
        else:
            measurements = msg.ranges[idx_start : idx_end + 1]

        # 6. Filtrado INTELIGENTE
        valid_ranges = [r for r in measurements if msg.range_min < r < msg.range_max and not math.isnan(r)]
        
        if valid_ranges:
            valid_ranges.sort()
            n_samples = max(1, int(len(valid_ranges) * 0.4))
            closest_ranges = valid_ranges[:n_samples]
            return sum(closest_ranges) / len(closest_ranges)
            
        return None
        

    def callback(self, msg):
        try:
            np_arr = np.frombuffer(msg.data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        except Exception as e:
            self.get_logger().error(f'Error CV bridge: {e}')
            return

        if self.user_res:
            w, h = map(int, self.user_res.split('x'))
            frame = cv2.resize(frame, (w, h))

        # Inferencia YOLO
        results = self.model(frame, verbose=False, classes=self.target_classes, conf=0.7)
        detections = results[0].boxes
        
        # Solo analizamos si HAY detección
        if len(detections) > 0:
            # 1. Tomamos la clase del objeto principal
            top_det = detections[0]
            top_class_id = int(top_det.cls.item())
            class_name = results[0].names[top_class_id]
            
            # 2. Agregamos al historial
            self.detection_history.append(class_name)
            
            # 3. Analizamos
            most_common, count = Counter(self.detection_history).most_common(1)[0]
            nombre_es = self.traductor.get(most_common, most_common) 
            hist_len = len(self.detection_history)

            # --- CASO A: CONFIRMACIÓN (Lleno y estable) ---
            if hist_len == self.CONFIRMATION_LIMIT and count >= 8:
                
                # --- CALCULO DE DISTANCIA ---
                bbox = top_det.xyxy.cpu().numpy().astype(int).squeeze()
                img_w = frame.shape[1]
                
                # <--- MODIFICADO: Pasamos el tiempo actual de la imagen para validar sync
                current_img_time = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
                dist = self.get_distance_to_bbox(bbox, img_w, current_img_time)
                # ----------------------------------------------------------------------

                dist_str = f"a {dist:.2f}m" if dist else "(distancia desc.)"
                
                self.get_logger().info(f"✅ Veo {nombre_es} {dist_str}")
                self.detection_history.clear() 
                # Accionar aquí...

            # --- CASO B: VIENDO ALGO (En proceso) ---
            elif count == 6:
                self.get_logger().info(f"👀 Veo algo...")         
        
        # Dibujar bounding boxes
        for det in detections:
            xyxy = det.xyxy.cpu().numpy().astype(int).squeeze()
            
            # <--- MODIFICADO: Seguridad en índices (Clip) para evitar errores de cv2
            h_img, w_img, _ = frame.shape
            xyxy = np.clip(xyxy, 0, [w_img, h_img, w_img, h_img])
            # ----------------------------------------------------------------------

            class_idx = int(det.cls.item())
            class_name = results[0].names[class_idx]
            nombre_clase = self.traductor.get(class_name, class_name)
            conf = det.conf.item()
            
            cv2.rectangle(frame, (xyxy[0], xyxy[1]), (xyxy[2], xyxy[3]), (0, 0, 255), 2)  
            cv2.putText(frame, f'{nombre_clase} {conf:.2f}', (xyxy[0], xyxy[1]-5), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0,0,255), 2)

        # Publicar imagen
        img_msg = self.bridge.cv2_to_imgmsg(frame, 'bgr8')
        img_msg.header = msg.header
        self.image_pub.publish(img_msg)

def main(args=None):
    rclpy.init(args=args)
    node = YOLONode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


