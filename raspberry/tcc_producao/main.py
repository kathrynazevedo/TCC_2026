"""Monitoramento de EPIs na borda (Raspberry Pi): câmera -> YOLO -> sirene + alerta para a API."""
import queue
import signal
import sys
import threading
import time

import cv2

import cliente_api
import config
from deteccao import Debounce, resumir_infracoes, classificar

# ==========================================
# SIRENE (GPIO) — simulada quando não está numa Raspberry
# ==========================================
try:
    import RPi.GPIO as GPIO

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(config.PINO_SIRENE, GPIO.OUT)
    GPIO.output(config.PINO_SIRENE, GPIO.LOW)
    GPIO_ATIVO = True
    print("[HARDWARE] RPi.GPIO carregado. Relé da sirene conectado.")
except (ImportError, RuntimeError):
    GPIO_ATIVO = False
    print("[HARDWARE] RPi.GPIO indisponível: a sirene será simulada no terminal.")

_trava_sirene = threading.Lock()


def _tocar_sirene():
    with _trava_sirene:
        if GPIO_ATIVO:
            GPIO.output(config.PINO_SIRENE, GPIO.HIGH)
            time.sleep(config.DURACAO_SIRENE)
            GPIO.output(config.PINO_SIRENE, GPIO.LOW)
        else:
            print("[SIRENE SIMULADA] ligada")
            time.sleep(config.DURACAO_SIRENE)
            print("[SIRENE SIMULADA] desligada")


def acionar_sirene():
    """Dispara a sirene sem bloquear a inferência; se já estiver tocando, ignora."""
    if not _trava_sirene.locked():
        threading.Thread(target=_tocar_sirene, daemon=True).start()


# ==========================================
# THREADS DE APOIO
# ==========================================
parar = threading.Event()


def thread_heartbeat():
    """Avisa a API que a placa está viva; só imprime quando o estado muda."""
    online = None
    while not parar.is_set():
        ok = cliente_api.enviar_heartbeat()
        if ok != online:
            print("[REDE] Heartbeat OK: placa online na API." if ok else "[REDE] Heartbeat falhou: API inalcançável.")
            online = ok
        parar.wait(config.INTERVALO_HEARTBEAT)


def thread_sincronizacao():
    """Reenvia periodicamente os alertas guardados enquanto a API esteve fora."""
    while not parar.wait(config.INTERVALO_SINCRONIZACAO):
        cliente_api.sincronizar_pendentes()


def thread_captura(fila_frames):
    """Lê a câmera continuamente e mantém só o frame mais recente na fila; reconecta se cair."""
    cap = None
    while not parar.is_set():
        if cap is None or not cap.isOpened():
            if cap is not None:
                cap.release()
            cap = cv2.VideoCapture(config.CAMERA_SOURCE)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # menos atraso em streams RTSP
            if not cap.isOpened():
                print(f"[VÍDEO] Não foi possível abrir a câmera ({config.CAMERA_SOURCE}). Nova tentativa em 3s...")
                parar.wait(3)
                continue
            print("[VÍDEO] Câmera conectada.")

        ok, frame = cap.read()
        if not ok:
            print("[VÍDEO] Perda de sinal com a câmera. Reconectando...")
            cap.release()
            cap = None
            parar.wait(2)
            continue

        frame = cv2.resize(frame, (config.LARGURA_FRAME, config.ALTURA_FRAME))
        try:
            fila_frames.get_nowait()  # descarta o frame antigo
        except queue.Empty:
            pass
        fila_frames.put(frame)

    if cap is not None:
        cap.release()


# ==========================================
# PRINCIPAL
# ==========================================
def desenhar(frame, nome, confianca, caixa):
    x1, y1, x2, y2 = caixa
    cor = (0, 0, 255) if classificar(nome) else (0, 255, 0)  # vermelho = infração
    cv2.rectangle(frame, (x1, y1), (x2, y2), cor, 2)
    cv2.putText(frame, f"{nome} {confianca:.2f}", (x1, max(15, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, cor, 2)


def main():
    # Import tardio: carregar o ultralytics demora e não é necessário para os testes dos outros módulos.
    from ultralytics import YOLO

    print(f"Carregando modelo: {config.MODELO_PATH}")
    try:
        model = YOLO(config.MODELO_PATH, task="detect")
    except Exception as erro:
        print(f"[ERRO] Não foi possível carregar o modelo: {erro}")
        return 1

    if not config.EDGE_API_KEY:
        print("[AVISO] EDGE_API_KEY vazia: a API só aceitará a placa se estiver em modo de desenvolvimento.")

    # Faz o encerramento por systemd/kill passar pelo mesmo caminho do Ctrl+C.
    signal.signal(signal.SIGTERM, lambda *_: parar.set())

    fila = queue.Queue(maxsize=1)
    for alvo, args in ((thread_captura, (fila,)), (thread_heartbeat, ()), (thread_sincronizacao, ())):
        threading.Thread(target=alvo, args=args, daemon=True).start()

    debounce = Debounce(config.TEMPO_DEBOUNCE)
    print("Monitoramento iniciado. Pressione Ctrl+C para sair.")

    try:
        while not parar.is_set():
            try:
                frame = fila.get(timeout=1)
            except queue.Empty:
                continue  # câmera ainda conectando; espera sem gastar CPU

            resultado = model(frame, verbose=False, conf=config.CONFIANCA_MINIMA)[0]

            deteccoes = []
            for box in resultado.boxes:
                nome = model.names[int(box.cls[0])]
                confianca = float(box.conf[0])
                deteccoes.append((nome, confianca))
                desenhar(frame, nome, confianca, map(int, box.xyxy[0]))

            infracoes = resumir_infracoes(deteccoes, config.CONFIANCA_MINIMA)
            novos = [(tipo, conf) for tipo, conf in infracoes.items() if debounce.permitir(tipo, time.monotonic())]

            if novos:
                acionar_sirene()
                sucesso, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if sucesso:
                    jpeg = buffer.tobytes()
                    for tipo, conf in novos:
                        threading.Thread(target=cliente_api.processar_alerta, args=(jpeg, tipo, conf), daemon=True).start()

            if config.MOSTRAR_JANELA:
                cv2.imshow("TCC - Visão Computacional na Borda", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    except KeyboardInterrupt:
        pass
    finally:
        parar.set()
        if GPIO_ATIVO:
            GPIO.cleanup()
        cv2.destroyAllWindows()
        print("\nSistema encerrado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
