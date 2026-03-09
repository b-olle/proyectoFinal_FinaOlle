import cv2
import yaml
import numpy as np
import os

# --- CONFIGURACIÓN ---
RUTA_YAML = "/home/baltasar/proyecto final/deteccion_objetos/mapa_pintado/mapa depto facu/mi_depto.yaml"
RUTA_PGM = "/home/baltasar/proyecto final/deteccion_objetos/mapa_pintado/mapa depto facu/mi_depto.pgm"
RUTA_TXT = "objetos_encontrados.txt"
OUTPUT_IMG = "mapa_con_objetos_grande.png"
SCALE_FACTOR = 10  # Cuántas veces agrandar la imagen

def pintar_objetos():
    # 1. Cargar Metadatos
    with open(RUTA_YAML, 'r') as f:
        map_data = yaml.safe_load(f)
    resolution = map_data['resolution']
    origin_x = map_data['origin'][0]
    origin_y = map_data['origin'][1]

    # 2. Cargar Imagen y Agrandar
    img_orig = cv2.imread(RUTA_PGM, cv2.IMREAD_COLOR)
    if img_orig is None:
        print(f"Error: No se encuentra {RUTA_PGM}"); return

    h_orig, w_orig, _ = img_orig.shape
    
    # --- REDIMENSIONAR IMAGEN ---
    new_dim = (w_orig * SCALE_FACTOR, h_orig * SCALE_FACTOR)
    # Usamos INTER_NEAREST para que el mapa no se vea borroso
    img = cv2.resize(img_orig, new_dim, interpolation=cv2.INTER_NEAREST)
    height, width, _ = img.shape # Dimensiones escaladas
    # -----------------------------------

    # 3. Leer el TXT y Pintar
    print(f"Leyendo {RUTA_TXT}...")
    with open(RUTA_TXT, 'r') as f:
        lines = f.readlines()

    for line in lines[2:]:
        parts = line.strip().split('|')
        if len(parts) < 4: continue
        clase = parts[1].strip()
        world_x = float(parts[2].strip())
        world_y = float(parts[3].strip())

        # --- CONVERSIÓN Y ESCALADO ---
        # 1. Calcular pixel en imagen original chica
        px_x_orig = int((world_x - origin_x) / resolution)
        px_y_orig = int((world_y - origin_y) / resolution)
        px_y_orig = h_orig - px_y_orig # Invertir Y usando altura original

        # 2. Escalar coordenadas a la imagen escalada
        pixel_x = px_x_orig * SCALE_FACTOR
        pixel_y = px_y_orig * SCALE_FACTOR
        # -----------------------------

        if 0 <= pixel_x < width and 0 <= pixel_y < height:
            # Agrandé un poco el círculo (radio 8) y el texto (scale 0.7)
            cv2.circle(img, (pixel_x, pixel_y), 8, (0, 0, 255), -1)
            cv2.putText(img, clase, (pixel_x + 10, pixel_y), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            print(f"Pintado {clase} en ({pixel_x}, {pixel_y})")

    # 4. Guardar resultado
    cv2.imwrite(OUTPUT_IMG, img)
    print(f"✅ Mapa guardado como: {OUTPUT_IMG}")

if __name__ == "__main__":
    pintar_objetos()




'''import cv2
import yaml
import numpy as np

# --- CONFIGURACIÓN ---
RUTA_YAML = "/home/baltasar/proyecto final/deteccion_objetos/mapa_pintado/mapa depto facu/mi_depto.yaml"
RUTA_PGM = "/home/baltasar/proyecto final/deteccion_objetos/mapa_pintado/mapa depto facu/mi_depto.pgm"
RUTA_TXT = "objetos_encontrados.txt" 
OUTPUT_IMG = "mapa_con_objetos.png"

def pintar_objetos():
    # 1. Cargar Metadatos del Mapa (YAML)
    with open(RUTA_YAML, 'r') as f:
        map_data = yaml.safe_load(f)
        
    resolution = map_data['resolution']
    origin = map_data['origin']  # [x, y, z]
    origin_x = origin[0]
    origin_y = origin[1]

    # 2. Cargar Imagen del Mapa (PGM)
    # Usamos IMREAD_COLOR para poder pintar círculos de colores
    img = cv2.imread(RUTA_PGM, cv2.IMREAD_COLOR)
    height, width, _ = img.shape

    # 3. Leer el TXT y Pintar
    print(f"Leyendo {RUTA_TXT}...")
    
    with open(RUTA_TXT, 'r') as f:
        lines = f.readlines()
        
    # Saltamos el encabezado
    for line in lines[2:]:
        parts = line.strip().split('|')
        if len(parts) < 4: continue
        
        obj_id = parts[0].strip()
        clase = parts[1].strip()
        world_x = float(parts[2].strip())
        world_y = float(parts[3].strip())

        # --- CONVERSIÓN DE COORDENADAS ---
        # Formula: (Mundo - Origen) / Resolución
        # Nota: En imágenes, Y crece hacia abajo, en el mapa hacia arriba.
        # Por eso invertimos Y: (height - pixel_y)
        
        pixel_x = int((world_x - origin_x) / resolution)
        pixel_y = int((world_y - origin_y) / resolution)
        pixel_y = height - pixel_y  # Invertir eje Y

        # Verificar que esté dentro de la imagen
        if 0 <= pixel_x < width and 0 <= pixel_y < height:
            # Dibujar Círculo (Rojo)
            cv2.circle(img, (pixel_x, pixel_y), 5, (0, 0, 255), -1) 
            # Poner Texto (Verde)
            cv2.putText(img, clase, (pixel_x + 5, pixel_y), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 100, 0), 1)
            print(f"Pintado {clase} en píxeles ({pixel_x}, {pixel_y})")
        else:
            print(f"Objeto {clase} fuera de los límites del mapa.")

    # 4. Guardar resultado
    cv2.imwrite(OUTPUT_IMG, img)
    print(f"✅ Mapa guardado como: {OUTPUT_IMG}")

if __name__ == "__main__":
    pintar_objetos()'''
