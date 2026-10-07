import cv2
import time
import requests
import os
import queue
import threading
from datetime import datetime
from ultralytics import YOLO

# ==========================================
# CONFIGURAÇÕES DO SISTEMA (TCC)
# ==========================================
API_URL = "http://192.168.1.180:3000/api/alertas"
ZONA_ID = "Zona Norte"
MODELO_PATH = "best.tflite"

# ==========================================
# CONFIGURAÇÃO DOS PINOS GPIO (Sirene)
# ==========================================
PINO_SIRENE = 18

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PINO_SIRENE, GPIO.OUT)
    GPIO.output(PINO_SIRENE, GPIO.LOW)
    GPIO_ATIVO = True
    print("[HARDWARE] RPi.GPIO carregado com sucesso. Relé conectado.")
except (ImportError, RuntimeError):
    GPIO_ATIVO = False
    print("[HARDWARE] RPi.GPIO não encontrado (Rodando no Windows). O acionamento da Sirene será simulado no terminal.")

def acionar_sirene():
    """Liga a sirene (ou simula) por 2 segundos e desliga"""
    if GPIO_ATIVO:
        print("\n[GPIO REAL] Ligando Sirene Física (Pino 18)!")
        GPIO.output(PINO_SIRENE, GPIO.HIGH)
        time.sleep(2)
        GPIO.output(PINO_SIRENE, GPIO.LOW)
        print("[GPIO REAL] Sirene Desligada.")
    else:
        print("\n[GPIO SIMULADO] 🚨 Sirene LIGADA!")
        time.sleep(2)
        print("[GPIO SIMULADO] 🚨 Sirene DESLIGADA.")

# ==========================================
# CLASSES E FUNÇÕES CORE
# ==========================================

def enviar_alerta(frame, tipo_infracao, confianca):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamp_formatado = datetime.now().isoformat()
    nome_arquivo = f"infracao_{timestamp}.jpg"
    
    cv2.imwrite(nome_arquivo, frame)

    dados = {
        'zone': ZONA_ID,
        'type': tipo_infracao,
        'severity': 'high',
        'confidence': f"{confianca:.2f}",
        'detected_at': timestamp_formatado
    }

    try:
        with open(nome_arquivo, 'rb') as f:
            files = {'imagem': (nome_arquivo, f, 'image/jpeg')}
            resposta = requests.post(API_URL, data=dados, files=files, timeout=5)
        
        if resposta.status_code == 201:
            print(f"[REDE] Alerta '{tipo_infracao}' enviado à nuvem!")
            os.remove(nome_arquivo)
    except Exception as e:
        print(f"[REDE] Erro ao enviar: {e}. Salvando localmente.")

# ==========================================
# THREAD 1: CAPTURA DE VÍDEO (Leve)
# ==========================================
def thread_captura(fila_frames):
    import time # Garantir que o time seja usado na reconexão
    RTSP_URL = "rtsp://admin:admin123@192.168.1.209:554/cam/realmonitor?channel=1&subtype=1"
    cap = cv2.VideoCapture(RTSP_URL)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[VÍDEO] Perda de sinal com a câmera IP. Tentando reconectar...")
            time.sleep(2)
            cap = cv2.VideoCapture(RTSP_URL)
            continue

        frame = cv2.resize(frame, (640, 480))
        
        # Mantém a fila com apenas o frame mais recente (joga o velho fora)
        if not fila_frames.full():
            fila_frames.put(frame)
        else:
            try:
                fila_frames.get_nowait()
                fila_frames.put(frame)
            except queue.Empty:
                pass
                
# ==========================================
# MAIN: INFERÊNCIA DA IA
# ==========================================
if __name__ == "__main__":
    print(f"Carregando Modelo Otimizado (LiteRT): {MODELO_PATH}")
    model = YOLO(MODELO_PATH, task='detect')
    
    fila = queue.Queue(maxsize=1)
    t_captura = threading.Thread(target=thread_captura, args=(fila,), daemon=True)
    t_captura.start()

    # Controles de Debounce para evitar "piscar" e floodar o servidor
    ultimo_alerta_capacete = 0
    ultimo_alerta_colete = 0
    TEMPO_DEBOUNCE = 5.0

    print("Iniciando Monitoramento (Multi-threading). Pressione 'q' para sair.")
    
    try:
        while True:
            tempo_atual = time.time()
            if fila.empty():
                continue
                
            frame = fila.get()
            resultados = model(frame, verbose=False)[0]

            for box in resultados.boxes:
                confianca = float(box.conf[0])
                classe_id = int(box.cls[0])
                nome_classe = model.names[classe_id]

                if confianca > 0.75:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cor = (0, 255, 0) if "Sem_" not in nome_classe else (0, 0, 255)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), cor, 2)
                    cv2.putText(frame, f"{nome_classe} {confianca:.2f}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, cor, 2)

                if nome_classe.lower() in ["sem_capacete", "sem-capacete", "no-helmet"] and (tempo_atual - ultimo_alerta_capacete) > TEMPO_DEBOUNCE:
                    ultimo_alerta_capacete = tempo_atual
                    threading.Thread(target=acionar_sirene).start()
                    threading.Thread(target=enviar_alerta, args=(frame.copy(), 'no-helmet', confianca)).start()

                if nome_classe.lower() in ["sem_colete", "sem-colete", "no-vest"] and (tempo_atual - ultimo_alerta_colete) > TEMPO_DEBOUNCE:
                    ultimo_alerta_colete = tempo_atual
                    threading.Thread(target=acionar_sirene).start()
                    threading.Thread(target=enviar_alerta, args=(frame.copy(), 'no-vest', confianca)).start()

            #cv2.imshow("TCC - Visão Computacional na Borda", frame)

            #if cv2.waitKey(1) & 0xFF == ord('q'):
            #    break
                
    except KeyboardInterrupt:
        pass
    finally:
        if GPIO_ATIVO:
            GPIO.cleanup()
        cv2.destroyAllWindows()
        print("\nSistema encerrado.")
