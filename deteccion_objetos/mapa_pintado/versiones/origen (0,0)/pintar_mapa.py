import cv2
import yaml
import math
import os

# --- CONFIGURACIÓN ---
RUTA_YAML = "mapa_SLAM/mapa_entorno_SLAM.yaml"
RUTA_PGM = "mapa_SLAM/mapa_entorno_SLAM.pgm"
RUTA_TXT = "objetos_encontrados.txt"
OUTPUT_IMG = "mapa_con_objetos.png"
SCALE_FACTOR = 10 
DIST_TOLERANCE = 0.4 # Metros. Si está a menos de esto, se promedia.
MIN_DETECTIONS = 1   # <--- [MODIFICACIÓN 1] Umbral: si aparece menos de 5 veces, se ignora.

def pintar_objetos():
    # 1. Cargar Metadatos
    with open(RUTA_YAML, 'r') as f:
        map_data = yaml.safe_load(f)
    resolution = map_data['resolution']
    origin_x = map_data['origin'][0]
    origin_y = map_data['origin'][1]

    # 2. Cargar Imagen y Agrandar
    img_orig = cv2.imread(RUTA_PGM, cv2.IMREAD_COLOR)
    if img_orig is None: print(f"Error: {RUTA_PGM}"); return
    
    h_orig, w_orig, _ = img_orig.shape
    new_dim = (w_orig * SCALE_FACTOR, h_orig * SCALE_FACTOR)
    img = cv2.resize(img_orig, new_dim, interpolation=cv2.INTER_NEAREST)
    height, width, _ = img.shape 

    # --- [MODIFICACIÓN: DIBUJAR EJES Y ORIGEN (0,0)] ---
    # Convertir (0,0) metros a píxeles originales
    px_0_x = int((0.0 - origin_x) / resolution)
    px_0_y = int((0.0 - origin_y) / resolution)
    px_0_y = h_orig - px_0_y  # Invertir eje Y para imagen de OpenCV

    # Escalar a las dimensiones de la imagen final
    p0_x = px_0_x * SCALE_FACTOR
    p0_y = px_0_y * SCALE_FACTOR

    # Definir la longitud visual de los ejes (0.8 metros en píxeles)
    axis_len = int((0.8 / resolution) * SCALE_FACTOR)

    # Eje X (Rojo: BGR 0,0,255) apunta a la derecha
    cv2.arrowedLine(img, (p0_x, p0_y), (p0_x + axis_len, p0_y), (0, 0, 255), 3, tipLength=0.1)
    cv2.putText(img, "X", (p0_x + axis_len + 10, p0_y + 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # Eje Y (Verde: BGR 0,255,0) apunta hacia arriba (menor valor Y en la imagen)
    cv2.arrowedLine(img, (p0_x, p0_y), (p0_x, p0_y - axis_len), (0, 255, 0), 3, tipLength=0.1)
    cv2.putText(img, "Y", (p0_x - 20, p0_y - axis_len - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # Punto origen (Azul: BGR 255,0,0)
    cv2.circle(img, (p0_x, p0_y), 8, (255, 0, 0), -1)
    cv2.putText(img, "(0,0)", (p0_x - 60, p0_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
    # ---------------------------------------------------

    # 3. Leer y Agrupar Objetos
    print(f"Procesando {RUTA_TXT}...")
    objetos_unicos = [] # Lista de dicts: {'clase': str, 'x': float, 'y': float, 'n': int}

    with open(RUTA_TXT, 'r') as f:
        lines = f.readlines()

    for line in lines[2:]: # Saltar header
        parts = line.strip().split('|')
        if len(parts) < 4: continue
        
        clase = parts[1].strip()
        wx = float(parts[2].strip())
        wy = float(parts[3].strip())

        # Lógica de agrupación
        encontrado = False
        for obj in objetos_unicos:
            # Calcular distancia hipotenusa
            dist = math.hypot(wx - obj['x'], wy - obj['y'])
            
            # Si es la misma clase y está cerca, promediamos
            if clase == obj['clase'] and dist < DIST_TOLERANCE:
                # Actualizar promedio ponderado
                n = obj['n']
                obj['x'] = (obj['x'] * n + wx) / (n + 1)
                obj['y'] = (obj['y'] * n + wy) / (n + 1)
                obj['n'] += 1
                encontrado = True
                break
        
        if not encontrado:
            objetos_unicos.append({'clase': clase, 'x': wx, 'y': wy, 'n': 1})

    # 4. Pintar Objetos Únicos
    print(f"Se encontraron {len(objetos_unicos)} objetos únicos después de filtrar.")
    eliminados = 0
    
    for obj in objetos_unicos:
    
        # <--- [MODIFICACIÓN 2] Filtro: Si tiene pocas detecciones, saltar
        if obj['n'] < MIN_DETECTIONS:
            eliminados = eliminados + 1
            continue
        # ---------------------------------------------------------------
        
        # Conversión a píxeles
        px_x_orig = int((obj['x'] - origin_x) / resolution)
        px_y_orig = int((obj['y'] - origin_y) / resolution)
        px_y_orig = h_orig - px_y_orig 

        # Escalar
        pixel_x = px_x_orig * SCALE_FACTOR
        pixel_y = px_y_orig * SCALE_FACTOR

        if 0 <= pixel_x < width and 0 <= pixel_y < height:
            cv2.circle(img, (pixel_x, pixel_y), 8, (0, 0, 255), -1)
            # Texto con cantidad de detecciones entre paréntesis
            texto = f"{obj['clase']} ({obj['n']})"
            cv2.putText(img, texto, (pixel_x + 10, pixel_y), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # --- [NUEVA MODIFICACIÓN: DIBUJAR ESCALA DE 1 METRO] ---
    # Calcular longitud de 1 metro en píxeles finales
    scale_px = int((1.0 / resolution) * SCALE_FACTOR)
    
    # Posicionar en la esquina inferior derecha (con un margen de 40px)
    scale_x1 = width - scale_px - 40
    scale_x2 = width - 40
    scale_y = height - 40
    
    # Posicionar en la esquina inferior izquierda (con un margen de 40px)
    scale_x1 = 40
    scale_x2 = 40 + scale_px
    scale_y = height - 40
    
    # Dibujar la línea principal (Negro: BGR 0,0,0)
    cv2.line(img, (scale_x1, scale_y), (scale_x2, scale_y), (0, 0, 0), 3)
    # Dibujar los topes verticales
    cv2.line(img, (scale_x1, scale_y - 10), (scale_x1, scale_y + 10), (0, 0, 0), 3)
    cv2.line(img, (scale_x2, scale_y - 10), (scale_x2, scale_y + 10), (0, 0, 0), 3)
    
    # Añadir el texto "1 m" centrado arriba de la línea
    text_size = cv2.getTextSize("1 m", cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
    text_x = scale_x1 + (scale_px - text_size[0]) // 2
    cv2.putText(img, "1 m", (text_x, scale_y - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    # -------------------------------------------------------

    print(f"Se eliminaron {eliminados} objetos después de refiltrar.")
    cv2.imwrite(OUTPUT_IMG, img)
    print(f"✅ Mapa guardado como: {OUTPUT_IMG}")

if __name__ == "__main__":
    pintar_objetos()
