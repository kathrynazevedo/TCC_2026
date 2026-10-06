from inference import get_model
import cv2
import paho.mqtt.client as mqtt
import time
import json
import sqlite3
from datetime import datetime

# --- CONFIGURAÇÕES DA IA ---
API_KEY = "oMSMjZateJdrCUnY7xN7"
MODEL_ID = "construction-safety-gsnvb/1"
CONFIDENCE_THRESHOLD = 0.40  
STABILITY_THRESHOLD = 2      

# --- INICIALIZAÇÃO MQTT ---
client = mqtt.Client()
try:
    client.connect("localhost", 1883, 60)
    client.loop_start()
    print("[MQTT] Conectado ao Broker com sucesso.")
except Exception as e:
    print(f"[ERRO] Não foi possível conectar ao Broker MQTT: {e}")

# --- CONEXÃO COM O BANCO DE DADOS (SQLITE) ---
try:
    conn = sqlite3.connect('database.sqlite')
    cursor = conn.cursor()
    print("[BANCO] Conectado ao SQLite com sucesso.")
except Exception as e:
    print(f"[ERRO] Falha ao conectar no SQLite: {e}")

# --- CONTROLE DE ESTABILIDADE E ANTI-FLOOD ---
stability_counters = {}
historico_recente = {}
TEMPO_ESPERA_SEG = 30 # Bloqueia flood da mesma infração por 30 segundos

print("Conectando ao modelo de segurança SafeWork...")
model = get_model(model_id=MODEL_ID, api_key=API_KEY)

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret: break

    start_inference = time.time()
    results = model.infer(frame)[0]
    latency_ms = (time.time() - start_inference) * 1000

    detections_summary = []
    labels_no_frame_atual = []

    for det in results.predictions:
        if det.confidence < CONFIDENCE_THRESHOLD:
            continue

        label = det.class_name.lower()
        conf = det.confidence
        labels_no_frame_atual.append(label)

        stability_counters[label] = stability_counters.get(label, 0) + 1

        if stability_counters[label] >= STABILITY_THRESHOLD:
            # Lógica para as Infrações (Falta de EPI)
            if "no-" in label:
                color = (0, 0, 255) # Vermelho
                status_texto = f"ALERTA: {label.upper()}"
                zona_atual = "Zona Norte"
                agora = time.time()
                chave_alerta = f"{label}-{zona_atual}"

                # 🚦 FILTRO ANTI-FLOOD E GRAVAÇÃO NO BANCO
                if chave_alerta not in historico_recente or (agora - historico_recente[chave_alerta] > TEMPO_ESPERA_SEG):
                    historico_recente[chave_alerta] = agora
                    data_hora = datetime.now().isoformat()

                    # 1. Salva no Banco de Dados para o Dashboard ler
                    try:
                        cursor.execute('''
                            INSERT INTO violations (type, zone, severity, status, detected_at, worker_name)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (label, zona_atual, 'high', 'active', data_hora, 'Desconhecido'))
                        conn.commit()
                        print(f"🚨 [BD] Infração '{label}' salva no banco de dados!")
                    except Exception as e:
                        print(f"❌ Erro ao salvar no BD: {e}")

                    # 2. Envia via MQTT
                    alert_data = {
                        "type": label,
                        "confidence": conf,
                        "zone": zona_atual,
                        "timestamp": agora
                    }
                    client.publish("safework/alerts", json.dumps(alert_data))
                    
            else:
                color = (0, 255, 255) # Amarelo
                status_texto = f"OK: {label.upper()}"

            # Desenho na tela
            x, y, w, h = det.x, det.y, det.width, det.height
            start = (int(x - w/2), int(y - h/2))
            end = (int(x + w/2), int(y + h/2))
            cv2.rectangle(frame, start, end, color, 2)
            cv2.putText(frame, f"{status_texto} {conf:.2f}", (start[0], start[1]-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            detections_summary.append(f"{label} ({conf:.2%})")

    for label in list(stability_counters.keys()):
        if label not in labels_no_frame_atual:
            stability_counters[label] = 0

    status_log = " | ".join(detections_summary) if detections_summary else "Processando..."
    print(f"[INFO] Latência: {latency_ms:6.2f}ms | Status: {status_log}")

    cv2.imshow("SafeWork Monitor - Analise de EPI", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
client.loop_stop()
client.disconnect()
conn.close()