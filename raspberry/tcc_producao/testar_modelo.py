"""Testa um modelo com a MESMA regra do sistema, na câmera ou num vídeo. Não envia nada à API nem aciona a sirene.

    python testar_modelo.py --so-classes                  # só confere se o modelo serve ao sistema e sai
    python testar_modelo.py                               # câmera e modelo do .env (modelo_pessoa_epi.tflite), com janela
    python testar_modelo.py --modelo C:\\caminho\\best.pt   # um modelo recém-treinado
    python testar_modelo.py --fonte cena.mp4 --sem-janela --quadros 100 --salvar saida.png

Mostra cada pessoa (com o seu número), o capacete e o colete que o modelo achou nela, a contagem e o FPS, e escreve
[ALERTA] no terminal quando uma falta de EPI seria confirmada. Tecla [q] na janela encerra.
"""
import argparse
import sys
import time
from collections import Counter, deque

import cv2

import config
import main as sistema  # reaproveita o desenho da foto de evidência, igual ao que vai para o painel
from deteccao import ROTULOS, AlertasPorPessoa, papel, papeis_faltando


def ler_argumentos():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--modelo", default=config.MODELO_PATH, help=".pt ou .tflite")
    p.add_argument("--fonte", default=str(config.CAMERA_SOURCE), help="índice da webcam, URL RTSP ou arquivo de vídeo")
    p.add_argument("--so-classes", action="store_true",
                   help="só confere se o modelo serve ao sistema (classes de pessoa, capacete e colete) e sai")
    p.add_argument("--sem-janela", action="store_true", help="não abre janela (para rodar sem monitor)")
    p.add_argument("--quadros", type=int, default=0, help="para depois de N quadros (0 = até apertar q / fim do vídeo)")
    p.add_argument("--salvar", default=None, help="grava o último quadro, já desenhado, neste arquivo .png/.jpg")
    return p.parse_args()


def main():
    args = ler_argumentos()
    from ultralytics import YOLO

    modelo = YOLO(args.modelo, task="detect")
    classes = list(modelo.names.values())
    faltando = papeis_faltando(classes)
    print(f"Modelo : {args.modelo}\nClasses: {classes[:12]}{' ...' if len(classes) > 12 else ''} ({len(classes)})")
    reconhecidas = {nome: papel(nome) for nome in classes if papel(nome)}
    print(f"Classes que o sistema reconhece ({len(reconhecidas)} de {len(classes)}): {reconhecidas or 'nenhuma'}")
    if faltando:
        print(f"\nRESULTADO: NÃO SERVE ao sistema. Falta classe de: {', '.join(faltando)}.")
        print("O modelo deste projeto tem 3 classes (pessoa, capacete, colete); este não é ele.")
        return 1
    if args.so_classes:
        print("\nRESULTADO: COMPATÍVEL. O modelo tem pessoa, capacete e colete.")
        return 0

    alertas = AlertasPorPessoa(
        config.TEMPO_REALERTA, config.RASTREADOR_TEMPO_AUSENTE, config.RASTREADOR_DIST_MAXIMA,
        config.RASTREADOR_TEMPO_PRESENTE, config.CONFIANCA_PESSOA, config.LIMIARES_EPI,
        config.ALTURA_MINIMA_PESSOA, config.TEMPO_CONFIRMACAO,
    )
    print("A regra de alerta está ativa (nada é enviado, a sirene não toca).")

    fonte = int(args.fonte) if args.fonte.isdigit() else args.fonte
    cap = sistema.abrir_camera(fonte)
    if not cap.isOpened():
        print(f"[ERRO] Não abriu a câmera/vídeo: {config.ocultar_credenciais(fonte)}")
        return 1

    situacao_anterior, ultimo_quadro = None, None  # o último quadro DESENHADO (ao fim do vídeo a leitura devolve None)
    tempos, processados, maximo_pessoas, totais = deque(maxlen=20), 0, 0, Counter()
    print("Rodando... (q para sair)\n")
    try:
        while args.quadros == 0 or processados < args.quadros:
            ok, frame = cap.read()
            if not ok:
                break
            inicio = time.perf_counter()
            frame = cv2.resize(frame, (config.LARGURA_FRAME, config.ALTURA_FRAME))
            resultado = modelo(frame, verbose=False, conf=config.CONFIANCA_MODELO)[0]
            deteccoes = [
                (modelo.names[int(b.cls[0])], float(b.conf[0]), tuple(map(int, b.xyxy[0]))) for b in resultado.boxes
            ]
            cena = alertas.filtrar(deteccoes, time.monotonic())

            for numero, pessoa, infracoes in cena.pessoas:
                sistema.desenhar_pessoa(frame, numero, pessoa, infracoes)
            tempos.append(time.perf_counter() - inicio)
            fps = len(tempos) / sum(tempos)
            cv2.putText(frame, f"Pessoas: {len(cena.situacao)}   {fps:.1f} FPS", (8, config.ALTURA_FRAME - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA)

            if cena.situacao != situacao_anterior:
                situacao_anterior = cena.situacao
                if cena.situacao:
                    print("[CENA]", f"{len(cena.situacao)} pessoa(s):",
                          " | ".join(sistema.descrever(n, t) for n, t in cena.situacao))
                else:
                    print("[CENA] ninguém em cena")
            for tipo, confianca, numero in cena.alertas:
                totais[tipo] += 1
                print(f"[ALERTA] {ROTULOS.get(tipo, tipo)}: pessoa {numero} (confiança da pessoa {confianca:.2f})"
                      "  [simulado: nada enviado]")

            processados += 1
            ultimo_quadro = frame
            maximo_pessoas = max(maximo_pessoas, len(cena.situacao))
            if not args.sem_janela:
                cv2.imshow("Teste do modelo (q = sair)", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        if not args.sem_janela:
            cv2.destroyAllWindows()

    if args.salvar and ultimo_quadro is not None:
        cv2.imwrite(args.salvar, ultimo_quadro)
        print(f"\nÚltimo quadro salvo em {args.salvar}")
    media = (len(tempos) / sum(tempos)) if tempos else 0
    print(f"\n{processados} quadro(s) | até {maximo_pessoas} pessoa(s) ao mesmo tempo | ~{media:.1f} FPS neste computador")
    print("Alertas que teriam saído:", dict(totais) or "nenhum")
    return 0


if __name__ == "__main__":
    sys.exit(main())
