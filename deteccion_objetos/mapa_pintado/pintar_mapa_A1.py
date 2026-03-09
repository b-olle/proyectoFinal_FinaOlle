import cv2
import yaml
import math
import os

# --- CONFIGURACIÓN ---
RUTA_YAML = "/home/baltasar/proyecto final/deteccion_objetos/mapa_pintado/mapa depto facu/mi_depto.yaml"
RUTA_PGM = "/home/baltasar/proyecto final/deteccion_objetos/mapa_pintado/mapa depto facu/mi_depto.pgm"
RUTA_TXT = "objetos_encontrados.txt"
OUTPUT_IMG = "mapa_con_objetos.png"
SCALE_FACTOR = 10 
DIST_TOLERANCE = 0.2 # Metros. Si está a menos de esto, se promedia.

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
    
    for obj in objetos_unicos:
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

    cv2.imwrite(OUTPUT_IMG, img)
    print(f"✅ Mapa guardado como: {OUTPUT_IMG}")

if __name__ == "__main__":
    pintar_objetos()
