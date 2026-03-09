import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
from ultralytics import YOLO
from sensor_msgs.msg import CompressedImage  # agregado
import numpy as np  # agregado


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

        # -------- Control de inferencia --------
        self.do_inference = True
        self.inference_period = 1.15  # segundos 

        # Timer que habilita inferencia cada 500 ms
        self.timer = self.create_timer(self.inference_period, self.enable_inference)

        # Guardamos la última detección válida
        self.last_detections = []  # lista de dicts

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

    def enable_inference(self):
        # Este timer solo habilita la inferencia
        self.do_inference = True

    def callback(self, msg):
        try:
            np_arr = np.frombuffer(msg.data, np.uint8)  # agregado
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)  # agregado
        except Exception as e:
            self.get_logger().error(f'Error CV bridge: {e}')
            return

        # Redimensionar si se indicó
        if self.user_res:
            w, h = map(int, self.user_res.split('x'))
            frame = cv2.resize(frame, (w, h))

        # ---------- Inferencia YOLO cada X s ----------
        if self.do_inference:
            self.do_inference = False  # consumimos el permiso

            self.last_detections = []  # limpiamos detecciones previas

            results = self.model(frame, verbose=False)
            detections = results[0].boxes  # 1 frame -> [0]

            # Dibujar bounding boxes
            for det in detections:
                xyxy = det.xyxy.cpu().numpy().astype(int).squeeze()   # [x_min, y_min, x_max, y_max]
                class_idx = int(det.cls.item())                       # número de la clase
                class_name = results[0].names[class_idx]              # nombre de la clase
                conf = det.conf.item()                                # confianza

                if conf > 0.7:
                    self.last_detections.append({
                        "xyxy": xyxy,
                        "class_name": class_name,
                        "conf": conf
                    })

                    self.get_logger().info(
                        f'Detectado: {class_name} con confianza {conf:.2f}'
                    )
                    # ACCIONAR LO QUE QUEREMOS ACÁ.

        # ---------- Dibujar SIEMPRE la última detección ----------
        for det in self.last_detections:
            xyxy = det["xyxy"]
            class_name = det["class_name"]
            conf = det["conf"]
            
            h, w, _ = frame.shape
            x1 = max(0, min(xyxy[0], w - 1))
            y1 = max(0, min(xyxy[1], h - 1))
            x2 = max(0, min(xyxy[2], w - 1))
            y2 = max(0, min(xyxy[3], h - 1))
            
            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 0, 255),
                1
            )


            '''cv2.rectangle(
                frame,
                (xyxy[0], xyxy[1]),
                (xyxy[2], xyxy[3]),
                (0, 0, 255),
                1
            )'''

            cv2.putText(
                frame,
                f'{class_name} {conf:.2f}',
                (xyxy[0], xyxy[1] - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.85,
                (0, 0, 255),
                2
            )

        # Publicar imagen (siempre, inferida o no)
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

