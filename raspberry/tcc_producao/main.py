import cv2
import time
import requests
import queue
import threading
from datetime import datetime
from ultralytics import YOLO

# ==========================================
# CONFIGURAÇÕES DO SISTEMA (TCC)
# ==========================================
#IP_BACKEND = "192.168.1.180" # Substitua pelo IP da máquina rodando Node.js
IP_BACKEND = "127.0.0.1" # voltar a rota do ip da placa a cima
VIOLATION_URL = f"http://{IP_BACKEND}:3000/api/violations"
HEARTBEAT_URL = f"http://{IP_BACKEND}:3000/api/status/heartbeat"

ID_DISPOSITIVO = 1 # ID numérico mapeado no banco PostgreSQL
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
# THREAD DE COMUNICAÇÃO: HEARTBEAT
# ==========================================
def enviar_heartbeat():
    """Avisa a API a cada 30s que a placa está online"""
    while True:
        try:
            requests.post(HEARTBEAT_URL, json={"id_dispositivo": ID_DISPOSITIVO}, timeout=5)
            # print("[REDE] Heartbeat enviado") # Opcional descomentar para debug
        except Exception:
            pass # Ignora falhas silenciosamente para não poluir o terminal
        time.sleep(30)

# ==========================================
# FUNÇÃO CORE: ENVIO DE ALERTA
# ==========================================
def enviar_alerta(frame, tipo_infracao, confianca):
    timestamp_formatado = datetime.now().isoformat()
    
    # 1. Converte o frame atual para JPEG diretamente na memória RAM (poupa o SD Card)
    sucesso, buffer = cv2.imencode('.jpg', frame)
    if not sucesso:
        return

    # 2. Payload ajustado para os nomes que o violationController.js exige
    dados = {
        'id_dispositivo': ID_DISPOSITIVO,
        'tipo_epi_ausente': tipo_infracao,
        'severity': 'high',
        'confidence': confianca,
        'timestamp': timestamp_formatado
    }

    try:
        # 3. Envia os bytes da memória. NOTA: A chave 'image' deve bater com upload.single('image') no Node
        files = {'image': ('infracao.jpg', buffer.tobytes(), 'image/jpeg')}
        resposta = requests.post(VIOLATION_URL, data=dados, files=files, timeout=10)
        
        if resposta.status_code == 201:
            print(f"[REDE] Alerta '{tipo_infracao}' enviado à nuvem (Cloudinary) com sucesso!")
    except Exception as e:
        print(f"[REDE] Falha ao enviar para API: {e}")

# ==========================================
# THREAD 1: CAPTURA DE VÍDEO (Leve)
# ==========================================
def thread_captura(fila_frames):
    import time
    #RTSP_URL = "rtsp://admin:admin123@192.168.1.209:554/cam/realmonitor?channel=1&subtype=1"
    #cap = cv2.VideoCapture(RTSP_URL)
    cap = cv2.VideoCapture(0) #Remover depois - teste web cam

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
    
    # Inicia a captura de vídeo
    t_captura = threading.Thread(target=thread_captura, args=(fila,), daemon=True)
    t_captura.start()

    # Inicia o Heartbeat
    t_heartbeat = threading.Thread(target=enviar_heartbeat, daemon=True)
    t_heartbeat.start()

    # Controles de Debounce para evitar "piscar" e floodar o servidor
    ultimo_alerta_capacete = 0
    ultimo_alerta_colete = 0
    TEMPO_DEBOUNCE = 10.0 # Aumentado para 10s para não sobrecarregar o upload do Cloudinary

    print("Iniciando Monitoramento (Multi-threading). Pressione Ctrl+C para sair.")
    
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

                if confianca > 0.70: # Ajuste de limite de confiança se necessário
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cor = (0, 255, 0) if "Sem_" not in nome_classe else (0, 0, 255)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), cor, 2)
                    cv2.putText(frame, f"{nome_classe} {confianca:.2f}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, cor, 2)

                    # Lógica de disparo e envio (Assíncrono)
                    if nome_classe.lower() in ["sem_capacete", "sem-capacete", "no-helmet"] and (tempo_atual - ultimo_alerta_capacete) > TEMPO_DEBOUNCE:
                        ultimo_alerta_capacete = tempo_atual
                        threading.Thread(target=acionar_sirene).start()
                        threading.Thread(target=enviar_alerta, args=(frame.copy(), 'Capacete', confianca)).start()

                    if nome_classe.lower() in ["sem_colete", "sem-colete", "no-vest"] and (tempo_atual - ultimo_alerta_colete) > TEMPO_DEBOUNCE:
                        ultimo_alerta_colete = tempo_atual
                        threading.Thread(target=acionar_sirene).start()
                        threading.Thread(target=enviar_alerta, args=(frame.copy(), 'Colete', confianca)).start()

            # cv2.imshow("TCC - Visão Computacional na Borda", frame)
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     break
                
    except KeyboardInterrupt:
        pass
    finally:
        if GPIO_ATIVO:
            GPIO.cleanup()
        cv2.destroyAllWindows()
        print("\nSistema encerrado.")