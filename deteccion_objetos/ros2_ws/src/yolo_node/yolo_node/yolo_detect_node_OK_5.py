import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
from ultralytics import YOLO
from sensor_msgs.msg import CompressedImage #agregado
import numpy as np #agregado
from collections import deque, Counter


class YOLONode(Node):

    def __init__(self):
        super().__init__('yolo_node')

        # Parámetros ROS2
        self.declare_parameter('model_path', '')
        self.declare_parameter('source', '')
        self.declare_parameter('resolution', '')

        self.model_path = self.get_parameter('model_path').get_parameter_value().string_value
        # self.source = self.get_parameter('source').get_parameter_value().string_value
        self.user_res = self.get_parameter('resolution').get_parameter_value().string_value

        # Cargar modelo YOLO
        self.model = YOLO(self.model_path)
        self.bridge = CvBridge()
        
        # Lista de clases permitidas (Casa)
        self.target_classes = [
            0, 15, 16, 24, 25, 26, 28, 39, 40, 41, 42, 43, 44, 45,
            46, 47, 48, 49, 51, 53, 55, 56, 58, 62, 63, 64, 65, 66, 
            67, 73, 74, 75, 76, 77, 78, 79
        ]
                
        # Variables para detección estable
        self.CONFIRMATION_LIMIT = 10
        
        # Historial de las últimas 10 detecciones (borra las viejas automáticamente)
        self.detection_history = deque(maxlen=self.CONFIRMATION_LIMIT)
        
        self.traductor = {
            # Seres vivos
            'person': 'una persona', 
            'cat': 'un gato', 
            'dog': 'un perro',
            
            # Accesorios
            'backpack': 'una mochila', 
            'umbrella': 'un paraguas', 
            'handbag': 'un bolso', 
            'suitcase': 'una valija',
            
            # Vajilla
            'bottle': 'una botella', 
            'wine glass': 'una copa', 
            'cup': 'una taza', 
            'fork': 'un tenedor',
            'knife': 'un cuchillo', 
            'spoon': 'una cuchara', 
            'bowl': 'un bowl',
            
            # Comida
            'banana': 'una banana', 
            'apple': 'una manzana', 
            'sandwich': 'un sándwich', 
            'orange': 'una naranja',
            'carrot': 'una zanahoria', 
            'pizza': 'una pizza', 
            'cake': 'una torta',
            
            # Muebles
            'chair': 'una silla', 
            'potted plant': 'una planta',
            
            # Electrónica
            'tv': 'una TV', 
            'laptop': 'una notebook', 
            'mouse': 'un mouse', 
            'remote': 'un control remoto',
            'keyboard': 'un teclado', 
            'cell phone': 'un celular',
            
            # Varios
            'book': 'un libro', 
            'clock': 'un reloj', 
            'vase': 'un florero', 
            'scissors': 'una tijera',
            'teddy bear': 'un peluche', 
            'hair drier': 'un secador', 
            'toothbrush': 'un cepillo de dientes'
        }
        
        
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
        # results = self.model(frame, verbose=False)
        results = self.model(frame, verbose=False, classes=self.target_classes, conf=0.75)
        detections = results[0].boxes                             # 1 frame -> [0]. Diccionario con todas las detecciones del frame.
        
        
        
        # Solo analizamos si HAY detección
        if len(detections) > 0:
            # 1. Tomamos la clase del objeto principal
            top_class_id = int(detections[0].cls.item())
            class_name = results[0].names[top_class_id]
            
            # 2. Agregamos al historial
            self.detection_history.append(class_name)
            
            # 3. Analizamos SIEMPRE (no esperamos a que llegue a 10)
            most_common, count = Counter(self.detection_history).most_common(1)[0]
            nombre_es = self.traductor.get(most_common, most_common)
            hist_len = len(self.detection_history)

            # --- CASO A: CONFIRMACIÓN (Lleno y estable) ---
            if hist_len == self.CONFIRMATION_LIMIT and count >= 8:
                self.get_logger().info(f"✅ Veo {nombre_es}")
                self.detection_history.clear() # Reiniciamos para buscar lo siguiente
                # Accionar aquí...

            # --- CASO B: VIENDO ALGO (En proceso) ---
            # Si llevamos más de 6 frames iguales, avisamos
            elif count == 6:
                # self.get_logger().info(f"👀 Parezco ver {nombre_es} ({count}/{hist_len})...")
                self.get_logger().info(f"👀 Veo algo...")       	
        

        # Dibujar bounding boxes
        for det in detections:
            xyxy = det.xyxy.cpu().numpy().astype(int).squeeze()   # obtiene las coordenadas del BBox para despues dibujar el rectángulo. [x_min, y_min, x_max, y_max]
            class_idx = int(det.cls.item())                       # numero de la clase para ir a buscar el nombre de la clase.
            class_name = results[0].names[class_idx]              # nombre de la clase
            conf = det.conf.item()                                # confianza de la detección 
            # if conf > 0.7:
            cv2.rectangle(frame, (xyxy[0], xyxy[1]), (xyxy[2], xyxy[3]), (0, 0, 255), 2)  
            cv2.putText(frame, f'{class_name} {conf:.2f}', (xyxy[0], xyxy[1]-5), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0,0,255), 2)
            # self.get_logger().info(f'Detectado: {class_name} con confianza como arg {conf:.2f}')
            # self.get_logger().info(f'Observando...')
            
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
