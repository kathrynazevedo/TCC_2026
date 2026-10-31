"""Mede, no hardware onde roda (a Raspberry Pi), as métricas da tabela de latência e processamento do TCC.

    python medir_desempenho.py                        # 200 quadros da câmera (CAMERA_SOURCE do .env)
    python medir_desempenho.py 300 --fonte teste.mp4  # vídeo gravado: comparável entre execuções
    python medir_desempenho.py 100 --api 5            # também mede 5 envios REAIS à API (cria 5 registros de teste)

Percorre o MESMO caminho do main.py (redimensionar -> modelo -> regras de pessoa e alerta), sem sirene e sem rede.
Com uma câmera, o FPS é limitado pela taxa dela; com um vídeo, mostra a capacidade de processamento da placa.
"""
import argparse
import statistics
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import cv2

import cliente_api
import config
from deteccao import PESSOA, AlertasPorPessoa, papel

AQUECIMENTO = 5  # os primeiros quadros incluem a inicialização do delegate/XNNPACK e não representam o regime


def resumo(valores):
    v = sorted(valores)
    return {
        "média": statistics.fmean(v),
        "mediana": statistics.median(v),
        "p95": v[min(len(v) - 1, int(0.95 * len(v)))],
        "pior": v[-1],
    }


def linha(nome, valores):
    r = resumo(valores)
    print(f"  {nome:<44} média {r['média']:7.1f} | mediana {r['mediana']:7.1f} | p95 {r['p95']:7.1f} | pior {r['pior']:7.1f}  (ms)")


def temperatura():
    try:
        return int(Path("/sys/class/thermal/thermal_zone0/temp").read_text()) / 1000
    except (OSError, ValueError):
        return None


def throttled():
    """'throttled=0x0' = sem limitação por temperatura/tensão (só existe na Raspberry)."""
    try:
        return subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True, timeout=3).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def medir_api(frame, repeticoes):
    ok, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    jpeg = buffer.tobytes()
    marca = {  # caixa [1,2,3,4] identifica estes registros de teste para apagá-los depois
        "id_dispositivo": config.ID_DISPOSITIVO,
        "timestamp": cliente_api.agora_utc(),
        "severity": "high",
        "total_pessoas": 1,
        "pessoas": [{
            "numero": 1, "caixa": [1, 2, 3, 4],
            "capacete": {"estado": "ausente", "confianca": 0.99, "novo": True},
            "colete": {"estado": "desconhecido", "confianca": None, "novo": False},
        }],
    }
    tempos, resultados = [], []
    for _ in range(repeticoes):
        inicio = time.perf_counter()
        resultados.append(cliente_api.enviar_ocorrencia(jpeg, marca))
        tempos.append((time.perf_counter() - inicio) * 1000)
    return len(jpeg), tempos, resultados


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("quadros", nargs="?", type=int, default=200, help="quantos quadros medir (depois do aquecimento)")
    p.add_argument("--fonte", default=str(config.CAMERA_SOURCE), help="índice da webcam, URL RTSP ou arquivo de vídeo")
    p.add_argument("--api", type=int, default=0, help="também mede N envios REAIS de ocorrência (cria N registros)")
    args = p.parse_args()

    from ultralytics import YOLO

    fonte = int(args.fonte) if args.fonte.isdigit() else args.fonte
    modelo = YOLO(config.MODELO_PATH, task="detect")
    alertas = AlertasPorPessoa(
        config.TEMPO_REALERTA, config.RASTREADOR_TEMPO_AUSENTE, config.RASTREADOR_DIST_MAXIMA,
        config.RASTREADOR_TEMPO_PRESENTE, config.CONFIANCA_PESSOA, config.LIMIARES_EPI,
        config.ALTURA_MINIMA_PESSOA, config.TEMPO_CONFIRMACAO,
    )
    confianca_modelo = config.CONFIANCA_MODELO
    cap = cv2.VideoCapture(fonte)
    if not cap.isOpened():
        print(f"[ERRO] Não abriu a fonte de vídeo: {fonte}")
        return 1

    leitura, redim, pre, inf, pos, regras, resposta, borda_alerta = ([] for _ in range(8))
    instante_quadro = []  # fim de cada quadro medido, para a taxa sustentada por janela
    pessoas_por_quadro = []  # quantas pessoas o modelo viu em cada quadro medido (confere a linha da tabela)
    temp_inicio, frame = temperatura(), None
    inicio_medicao = None

    for i in range(args.quadros + AQUECIMENTO):
        t0 = time.perf_counter()
        ok, frame = cap.read()
        if not ok:
            if isinstance(fonte, str) and Path(fonte).is_file():  # acabou o vídeo: recomeça
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = cap.read()
            if not ok:
                print("[ERRO] Falha ao ler quadro.")
                break
        t1 = time.perf_counter()
        frame = cv2.resize(frame, (config.LARGURA_FRAME, config.ALTURA_FRAME))
        t2 = time.perf_counter()
        resultado = modelo(frame, verbose=False, conf=confianca_modelo)[0]
        t3 = time.perf_counter()
        deteccoes = [
            (modelo.names[int(b.cls[0])], float(b.conf[0]), tuple(map(int, b.xyxy[0]))) for b in resultado.boxes
        ]
        alertas.filtrar(deteccoes, time.monotonic())
        t4 = time.perf_counter()
        if i >= AQUECIMENTO:
            pessoas_por_quadro.append(sum(1 for nome, conf, _ in deteccoes
                                          if papel(nome) == PESSOA and conf >= config.CONFIANCA_PESSOA))

        if i % 50 == 0:
            print(f"  ... quadro {i}/{args.quadros + AQUECIMENTO}", flush=True)
        if i < AQUECIMENTO:
            continue
        if inicio_medicao is None:
            inicio_medicao = t0
        leitura.append((t1 - t0) * 1000)
        redim.append((t2 - t1) * 1000)
        pre.append(resultado.speed["preprocess"])
        inf.append(resultado.speed["inference"])
        pos.append(resultado.speed["postprocess"])
        regras.append((t4 - t3) * 1000)
        resposta.append((t4 - t2) * 1000 + (t2 - t1) * 1000)  # redimensionar + modelo + regras
        borda_alerta.append((t4 - t0) * 1000)  # a partir da leitura do quadro até a decisão de alertar
        instante_quadro.append(t4)
    cap.release()

    n = len(inf)
    if n == 0:
        return 1
    duracao = instante_quadro[-1] - inicio_medicao
    fps_medio = n / duracao

    # menor taxa em janelas de 10 s: a "sustentada" é a pior janela, não a média
    janelas, ini = [], 0
    for fim in range(n):
        if instante_quadro[fim] - instante_quadro[ini] >= 10.0:
            janelas.append((fim - ini) / (instante_quadro[fim] - instante_quadro[ini]))
            ini = fim
    fps_janela = min(janelas) if janelas else None

    print(f"\nModelo : {Path(config.MODELO_PATH).name} ({Path(config.MODELO_PATH).stat().st_size / 1e6:.1f} MB) | "
          f"entrada {config.LARGURA_FRAME}x{config.ALTURA_FRAME} -> 640x640 | conf do modelo {confianca_modelo}")
    print(f"Fonte  : {config.ocultar_credenciais(args.fonte)} | {n} quadros medidos (+{AQUECIMENTO} de aquecimento)\n")
    print("Tempos por quadro:")
    linha("Leitura do quadro (câmera/vídeo)", leitura)
    linha("Redimensionar 640x480 (OpenCV)", redim)
    linha("Pré-processamento do modelo (letterbox)", pre)
    linha("Inferência (TFLite)", inf)
    linha("Pós-processamento (NMS)", pos)
    linha("Regras de pessoa/alerta (rastreio)", regras)
    print()
    linha("PRÉ-PROCESSAMENTO TOTAL (redim. + modelo)", [a + b for a, b in zip(redim, pre)])
    linha("TEMPO TOTAL DE RESPOSTA (redim.+modelo+regras)", resposta)
    linha("BORDA -> DECISÃO DE ALERTA (inclui a leitura)", borda_alerta)
    pior = f"{fps_janela:.1f} FPS (pior janela de 10 s)" if fps_janela else "pior janela de 10 s: n/d (medir mais quadros)"
    print(f"\nTaxa de quadros: {fps_medio:.1f} FPS (média) | {pior}")

    if pessoas_por_quadro:
        frequencia = Counter(pessoas_por_quadro)
        print(f"Pessoas detectadas por quadro: média {statistics.mean(pessoas_por_quadro):.1f} | "
              f"mais frequente {frequencia.most_common(1)[0][0]} "
              f"({frequencia.most_common(1)[0][1] * 100 // len(pessoas_por_quadro)}% dos quadros) | "
              f"mín. {min(pessoas_por_quadro)} | máx. {max(pessoas_por_quadro)}")

    t_fim = temperatura()
    if temp_inicio is not None:
        print(f"Temperatura da CPU: {temp_inicio:.0f} °C -> {t_fim:.0f} °C | {throttled() or 'vcgencmd indisponível'}")

    if args.api > 0:
        tamanho, tempos, resultados = medir_api(frame, args.api)
        print(f"\nEnvio à API ({args.api}x, JPEG de {tamanho / 1024:.0f} KB, resultados: {resultados}):")
        linha("POST /api/occurrences (upload + banco)", tempos)
        print("Para apagar os registros de teste (SQL Editor do Neon):")
        print("  DELETE FROM infracao WHERE id_ocorrencia IN (SELECT id_ocorrencia FROM ocorrencia "
              "WHERE pessoas @> '[{\"caixa\":[1,2,3,4]}]');")
        print("  DELETE FROM ocorrencia WHERE pessoas @> '[{\"caixa\":[1,2,3,4]}]';")
    return 0


if __name__ == "__main__":
    sys.exit(main())
