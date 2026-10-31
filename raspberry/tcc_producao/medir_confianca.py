"""Confiança média da detecção por classe (tabela de confiança do TCC), medida com o modelo real.

    python medir_confianca.py                          # câmera do .env, 50 capacetes, 50 coletes, 20 ausências
    python medir_confianca.py --fonte teste.mp4        # vídeo gravado (repetível)
    python medir_confianca.py --capacete 30 --colete 30 --ausencia 10 --minutos 5

Cada amostra é UMA detecção, e no máximo uma por classe a cada `--espaco` segundos (quadros seguidos da mesma pessoa
quase não diferem, então contar todos inflaria o número de amostras).
  - Capacete / colete: a confiança do capacete (ou colete) que o modelo achou dentro da caixa de uma pessoa.
  - Ausência de EPI: o modelo não detecta a falta; a amostra é a confiança da PESSOA que está em infração confirmada
    (sem o EPI de forma contínua por TEMPO_CONFIRMACAO), que é o valor que o sistema grava na ocorrência.
Só entram detecções acima dos limiares do .env (CONFIANCA_PESSOA, CONFIANCA_CAPACETE, CONFIANCA_COLETE), como no sistema em operação.
"""
import argparse
import statistics
import sys
import time
from pathlib import Path

import cv2

import config
from deteccao import AlertasPorPessoa


def linha(nome, amostras):
    if not amostras:
        print(f"  {nome:<22} 0 amostras")
        return
    desvio = statistics.stdev(amostras) if len(amostras) > 1 else 0.0
    print(f"  {nome:<22} {len(amostras):>3} amostras | média {statistics.mean(amostras) * 100:5.1f}% | "
          f"mín. {min(amostras) * 100:5.1f}% | máx. {max(amostras) * 100:5.1f}% | desvio {desvio * 100:4.1f} p.p.")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--fonte", default=str(config.CAMERA_SOURCE), help="índice da webcam, URL RTSP ou arquivo de vídeo")
    p.add_argument("--capacete", type=int, default=50, help="amostras de capacete")
    p.add_argument("--colete", type=int, default=50, help="amostras de colete")
    p.add_argument("--ausencia", type=int, default=20, help="amostras de ausência de EPI (pessoa em infração)")
    p.add_argument("--espaco", type=float, default=1.0, help="segundos mínimos entre duas amostras da mesma classe")
    p.add_argument("--minutos", type=float, default=10.0, help="tempo máximo da coleta")
    args = p.parse_args()
    metas = {"capacete": args.capacete, "colete": args.colete, "ausencia": args.ausencia}

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
        print(f"[ERRO] Não abriu a fonte de vídeo: {config.ocultar_credenciais(fonte)}")
        return 1

    amostras = {nome: [] for nome in metas}
    ultima = {nome: -1e9 for nome in metas}
    inicio = time.monotonic()
    print("Coletando... mantenha as pessoas à vista (uns de capacete e colete, outros sem). Ctrl+C encerra.", flush=True)
    try:
        while any(len(amostras[n]) < metas[n] for n in metas) and time.monotonic() - inicio < args.minutos * 60:
            ok, frame = cap.read()
            if not ok:
                if isinstance(fonte, str) and Path(fonte).is_file():
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                print("[ERRO] Falha ao ler quadro.")
                break
            frame = cv2.resize(frame, (config.LARGURA_FRAME, config.ALTURA_FRAME))
            resultado = modelo(frame, verbose=False, conf=confianca_modelo)[0]
            deteccoes = [
                (modelo.names[int(b.cls[0])], float(b.conf[0]), tuple(map(int, b.xyxy[0]))) for b in resultado.boxes
            ]
            agora = time.monotonic()
            cena = alertas.filtrar(deteccoes, agora)

            achados = {"capacete": [], "colete": [], "ausencia": []}
            for em_cena in cena.pessoas:
                pessoa = em_cena.pessoa
                if pessoa.capacete is not None:
                    achados["capacete"].append(pessoa.capacete.confianca)
                if pessoa.colete is not None:
                    achados["colete"].append(pessoa.colete.confianca)
                if em_cena.infracoes:
                    achados["ausencia"].append(pessoa.confianca)
            for nome, valores in achados.items():
                if valores and len(amostras[nome]) < metas[nome] and agora - ultima[nome] >= args.espaco:
                    amostras[nome].append(max(valores))
                    ultima[nome] = agora
    except KeyboardInterrupt:
        print("\n(interrompido)")
    finally:
        cap.release()

    print(f"\nConfiança média da detecção por classe | modelo {Path(config.MODELO_PATH).name} | "
          f"limiares: pessoa {config.CONFIANCA_PESSOA}, capacete {config.CONFIANCA_CAPACETE}, colete {config.CONFIANCA_COLETE}")
    linha("Capacete de segurança", amostras["capacete"])
    linha("Colete refletivo", amostras["colete"])
    linha("Ausência de EPI", amostras["ausencia"])
    faltou = [n for n in metas if len(amostras[n]) < metas[n]]
    if faltou:
        print(f"\nAtenção: meta não atingida em {', '.join(faltou)}. Mostre mais pessoas (com/sem EPI) ou aumente --minutos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
