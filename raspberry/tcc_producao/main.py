"""Monitoramento de EPIs na borda (Raspberry Pi): câmera -> YOLO -> sirene + alerta para a API."""
import queue
import signal
import sys
import threading
import time

import cv2

import cliente_api
import config
from deteccao import ROTULOS, AlertasPorPessoa, classificar, ocorrencia_da_cena

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


def descrever(numero, infracoes):
    """Ex.: 'Pessoa 2: sem capacete, sem colete' ou 'Pessoa 1: ok'."""
    return f"Pessoa {numero}: " + (", ".join(ROTULOS.get(t, t) for t in infracoes) or "ok")


def _cracha(frame, texto, x, y, cor):
    """Faixa colorida com texto branco, com o canto superior esquerdo em (x, y), mantida dentro do frame."""
    (largura, altura), _ = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
    alto, largo = frame.shape[:2]
    x = max(0, min(x, largo - largura - 8))
    y = max(0, min(y, alto - altura - 8))
    cv2.rectangle(frame, (x, y), (x + largura + 8, y + altura + 8), cor, -1)
    cv2.putText(frame, texto, (x + 4, y + altura + 3), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)


def desenhar_pessoa(frame, numero, pessoa, infracoes):
    """Crachá na cabeça, crachá curto no tronco e uma linha ligando os dois (vai na foto enviada à API).

    O crachá do tronco fica na vertical da cabeça, não no canto da caixa: o modelo às vezes desenha um colete largo
    cobrindo duas pessoas, e assim cada uma aparece marcada sobre o próprio corpo.
    """
    cor = (0, 0, 255) if infracoes else (0, 160, 0)
    cabeca, tronco = pessoa.cabeca, pessoa.tronco
    if cabeca is None:
        _cracha(frame, descrever(numero, infracoes), tronco.caixa[0], tronco.caixa[1], cor)
        return

    hx1, hy1, hx2, hy2 = cabeca.caixa
    _cracha(frame, descrever(numero, infracoes), hx1, hy1, cor)
    if tronco is not None:
        tx1, ty1, tx2, _ = tronco.caixa
        meio = (hx1 + hx2) // 2
        alvo = min(max(meio, tx1), tx2)  # a vertical da cabeça, mantida dentro da caixa do tronco
        cv2.line(frame, (meio, hy2), (alvo, ty1), (0, 255, 255), 1)  # amarelo: liga a cabeça ao tronco dela
        _cracha(frame, f"Pessoa {numero}", alvo - 38, ty1, cor)


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

    alertas = AlertasPorPessoa(
        config.TEMPO_REALERTA,
        config.RASTREADOR_TEMPO_AUSENTE,
        config.RASTREADOR_DIST_MAXIMA,
        config.RASTREADOR_TEMPO_PRESENTE,
        config.CONFIANCA_MINIMA,
    )
    situacao_anterior = ()  # só imprime a situação da cena quando ela muda
    repeticao = f"repete a cada {config.TEMPO_REALERTA:g}s" if config.TEMPO_REALERTA > 0 else "sem repetição"
    print(f"[ALERTAS] Um por pessoa em infração ({repeticao}); esquece quem some por {config.RASTREADOR_TEMPO_AUSENTE:g}s.")
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
                deteccoes.append((nome, confianca, tuple(map(int, box.xyxy[0]))))

            # Chamado a cada frame (mesmo sem detecções) para o rastreador perceber quem saiu de cena.
            cena = alertas.filtrar(deteccoes, time.monotonic())

            # Só desenha o que foi mantido: caixas duplicadas descartadas não poluem a foto de evidência.
            for numero, pessoa, infracoes in cena.pessoas:
                for parte in pessoa.partes():
                    desenhar(frame, parte.nome, parte.confianca, parte.caixa)
                desenhar_pessoa(frame, numero, pessoa, infracoes)

            if cena.situacao != situacao_anterior:
                situacao_anterior = cena.situacao
                if cena.situacao:
                    resumo = " | ".join(descrever(numero, tipos) for numero, tipos in cena.situacao)
                    print(f"[CENA] {len(cena.situacao)} pessoa(s) em cena: {resumo}")
                else:
                    print("[CENA] ninguém em cena")

            if cena.alertas:
                acionar_sirene()
                sucesso, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if sucesso:
                    for tipo, conf, numero in cena.alertas:
                        print(f"[ALERTA] {ROTULOS.get(tipo, tipo)}: pessoa {numero}, confiança {conf:.2f}")
                    # A cena inteira vai numa única requisição: uma foto, todas as pessoas e o que é novo.
                    ocorrencia = ocorrencia_da_cena(cena, config.ID_DISPOSITIVO, cliente_api.agora_utc())
                    threading.Thread(
                        target=cliente_api.processar_ocorrencia, args=(buffer.tobytes(), ocorrencia), daemon=True
                    ).start()

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
