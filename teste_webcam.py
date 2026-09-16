import cv2
import numpy as np
from ultralytics import YOLO

# 1. Tente carregar seu modelo de EPI. Se não existir, ele usa o padrão para não dar erro.
try:
    model = YOLO("best_epi_model.pt")
    print("Sucesso: Modelo de EPI carregado.")
except:
    model = YOLO("yolov8n.pt")
    print("Aviso: 'best_epi_model.pt' não encontrado. Usando modelo genérico para teste.")

# 2. Definição das Zonas (Simulação para a maquete)
def draw_zones(img):
    h, w, _ = img.shape
    mid_x, mid_y = w // 2, h // 2
    # Linhas divisórias
    cv2.line(img, (mid_x, 0), (mid_x, h), (255, 255, 255), 1)
    cv2.line(img, (0, mid_y), (w, mid_y), (255, 255, 255), 1)
    # Rótulos
    cv2.putText(img, "ZONA A", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(img, "ZONA B", (mid_x + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(img, "ZONA C", (10, mid_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(img, "ZONA D", (mid_x + 10, mid_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

def get_zone(x, y, w, h):
    mid_x, mid_y = w // 2, h // 2
    if x < mid_x and y < mid_y: return "A"
    if x >= mid_x and y < mid_y: return "B"
    if x < mid_x and y >= mid_y: return "C"
    return "D"

cap = cv2.VideoCapture(0)

while True:
    success, img = cap.read()
    if not success: break
    h, w, _ = img.shape

    # Desenha as divisões da maquete
    draw_zones(img)

    results = model(img, conf=0.5, verbose=False)

    for r in results:
        for box in r.boxes:
            # Lógica de classes do seu TCC
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            
            zona = get_zone(cx, cy, w, h)
            
            # Cores para o alerta (Verde se OK, Vermelho se Violação)
            color = (0, 255, 0) if cls == 0 else (0, 0, 255)
            label = f"Classe {cls} - Zona {zona}"

            if cls != 0:
                print(f"[ALERTA] Violação tipo {cls} detectada na Zona {zona}!")

            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            cv2.putText(img, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    cv2.imshow("SafeWork Monitor - Validação de EPI", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()