import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
from ultralytics import YOLO
from sensor_msgs.msg import CompressedImage #agregado
import numpy as np #agregado


class YOLONode(Node):

    def __init__(self):
        super().__init__('yolo_node')

        # Parámetros ROS2
        self.declare_parameter('model_path', '')
        self.declare_parameter('source', '')
        self.declare_parameter('resolution', '')

        self.model_path = self.get_parameter('model_path').get_parameter_value().string_value
        self.source = self.get_parameter('source').get_parameter_value().string_value
        self.user_res = self.get_parameter('resolution').get_parameter_value().string_value

        # Cargar modelo YOLO
        self.model = YOLO(self.model_path)
        self.bridge = CvBridge()
        
        # Subscripción al topic proveniente de rpi
        self.image_sub = self.create_subscription(
            CompressedImage,
            '/image_raw/compressed',  # el topic de la imagen de la cámara
            self.callback,
            1
        )
        
        # Publicación de resultados
        self.image_pub = self.create_publisher(Image, '/image_out', 1)

        self.get_logger().info(f'YOLO Node iniciado con modelo: {self.model_path}')

    def callback(self, msg):
        try:
            np_arr = np.frombuffer(msg.data, np.uint8) #agregado
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR) #agregado
        except Exception as e:
            self.get_logger().error(f'Error CV bridge: {e}')
            return

        # Redimensionar si se indicó
        if self.user_res:
            w, h = map(int, self.user_res.split('x'))
            frame = cv2.resize(frame, (w, h))

        # Inferencia YOLO
        results = self.model(frame, verbose=False)
        detections = results[0].boxes                             # 1 frame -> [0]. Diccionario con todas las detecciones del frame.

        # Dibujar bounding boxes
        for det in detections:
            xyxy = det.xyxy.cpu().numpy().astype(int).squeeze()   # obtiene las coordenadas del BBox para despues dibujar el rectángulo. [x_min, y_min, x_max, y_max]
            class_idx = int(det.cls.item())                       # numero de la clase para ir a buscar el nombre de la clase.
            class_name = results[0].names[class_idx]              # nombre de la clase
            conf = det.conf.item()                                # confianza de la detección 
            if conf > 0.7:
                cv2.rectangle(frame, (xyxy[0], xyxy[1]), (xyxy[2], xyxy[3]), (0, 0, 255), 1)  
                cv2.putText(frame, f'{class_name} {conf:.2f}', (xyxy[0], xyxy[1]-5), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0,0,255), 2)
                self.get_logger().info(f'Detectado: {class_name} con confianza {conf:.2f}')
                #ACCIONAR LO QUE QUEREMOS ACÁ.

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

