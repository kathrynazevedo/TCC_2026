"""Testa um modelo na SUA máquina, com a sua câmera ou um vídeo. Não envia nada à API nem aciona sirene.

    python testar_modelo.py                               # webcam 0 e o modelo do .env (modelo_pessoa_epi.tflite)
    python testar_modelo.py --modelo C:\\caminho\\best.pt   # o modelo que você acabou de treinar
    python testar_modelo.py --fonte cena.mp4 --sem-janela --quadros 100 --salvar saida.png

Mostra as pessoas (cada uma com o seu número), o capacete e o colete que o modelo achou nelas, a contagem e o FPS.
Com um modelo completo (pessoa + capacete + colete) roda também a regra de alerta e escreve [ALERTA] no terminal.
Com um modelo só de pessoas (ex.: o yolov8n.pt genérico) mostra só as pessoas: serve para ver a câmera e a contagem.
Tecla [q] na janela encerra.
"""
import argparse
import sys
import time
from collections import Counter, deque

import cv2

import config
import main as sistema  # reaproveita o desenho da foto de evidência, igual ao que vai para o painel
from deteccao import CAPACETE, COLETE, PESSOA, ROTULOS, AlertasPorPessoa, papel, papeis_faltando


def ler_argumentos():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--modelo", default=config.MODELO_PATH, help=".pt ou .tflite")
    p.add_argument("--fonte", default=str(config.CAMERA_SOURCE), help="índice da webcam, URL RTSP ou arquivo de vídeo")
    p.add_argument("--modelo-epi", default=None,
                   help="2º modelo SÓ para capacete/colete (ex.: o best.tflite antigo). Teste da regra com 2 modelos")
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
    modelo_epi = YOLO(args.modelo_epi, task="detect") if args.modelo_epi else None
    classes = list(modelo.names.values())
    faltando = papeis_faltando(classes + (list(modelo_epi.names.values()) if modelo_epi else []))
    print(f"Modelo : {args.modelo}\nClasses: {classes[:12]}{' ...' if len(classes) > 12 else ''} ({len(classes)})")
    if modelo_epi:
        print(f"Modelo de EPI: {args.modelo_epi}\nClasses: {list(modelo_epi.names.values())}")
    if args.so_classes:
        reconhecidas = {nome: papel(nome) for nome in classes if papel(nome)}
        print(f"Classes que o sistema reconhece ({len(reconhecidas)} de {len(classes)}): {reconhecidas or 'nenhuma'}")
        if faltando:
            print(f"\nRESULTADO: NÃO SERVE ao sistema. Falta classe de: {', '.join(faltando)}.")
            print("Um modelo treinado para este projeto tem 3 classes (pessoa, capacete, colete); este não é ele.")
            return 1
        print("\nRESULTADO: COMPATÍVEL. O modelo tem pessoa, capacete e colete.")
        return 0
    if PESSOA in faltando:
        print("[ERRO] Este modelo não tem classe de pessoa; não há o que contar. Use um modelo com pessoa/capacete/colete.")
        return 1
    completo = not faltando
    if completo and modelo_epi:
        print("Modo 2 MODELOS (só para teste: pessoas do 1º modelo, capacete/colete do 2º). Na placa, o tempo de "
              "inferência seria o dobro; o ideal é um único modelo com as 3 classes. Nada é enviado.")
    elif completo:
        print("Modo COMPLETO: pessoa + capacete + colete. A regra de alerta está ativa (nada é enviado, sirene só simulada).")
    else:
        print(f"Modo SÓ PESSOAS: o modelo não tem {', '.join(faltando)}. Mostro só a contagem e a numeração; sem alertas.")

    # Sem as 3 classes, "acusar" todo mundo de estar sem EPI seria falso: a confirmação nunca se completa.
    confirmacao = config.TEMPO_CONFIRMACAO if completo else float("inf")
    alertas = AlertasPorPessoa(
        config.TEMPO_REALERTA, config.RASTREADOR_TEMPO_AUSENTE, config.RASTREADOR_DIST_MAXIMA,
        config.RASTREADOR_TEMPO_PRESENTE, config.CONFIANCA_PESSOA, config.LIMIARES_EPI,
        config.ALTURA_MINIMA_PESSOA, confirmacao,
    )
    confianca_modelo = config.CONFIANCA_MODELO

    fonte = int(args.fonte) if args.fonte.isdigit() else args.fonte
    cap = cv2.VideoCapture(fonte)
    if not cap.isOpened():
        print(f"[ERRO] Não abriu a câmera/vídeo: {fonte}")
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
            resultado = modelo(frame, verbose=False, conf=confianca_modelo)[0]
            deteccoes = [
                (modelo.names[int(b.cls[0])], float(b.conf[0]), tuple(map(int, b.xyxy[0]))) for b in resultado.boxes
            ]
            if modelo_epi:  # pessoas vêm do 1º modelo; capacete e colete, do 2º
                deteccoes = [d for d in deteccoes if papel(d[0]) == PESSOA]
                extra = modelo_epi(frame, verbose=False, conf=confianca_modelo)[0]
                deteccoes += [
                    (nome, float(b.conf[0]), tuple(map(int, b.xyxy[0])))
                    for b in extra.boxes
                    if papel(nome := modelo_epi.names[int(b.cls[0])]) in (CAPACETE, COLETE)
                ]
            cena = alertas.filtrar(deteccoes, time.monotonic())

            for numero, pessoa, infracoes in cena.pessoas:
                sistema.desenhar_pessoa(frame, numero, pessoa, infracoes, avaliando=completo)
            tempos.append(time.perf_counter() - inicio)
            fps = len(tempos) / sum(tempos)
            cv2.putText(frame, f"Pessoas: {len(cena.situacao)}   {fps:.1f} FPS", (8, config.ALTURA_FRAME - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA)

            if cena.situacao != situacao_anterior:
                situacao_anterior = cena.situacao
                if cena.situacao:
                    print("[CENA]", f"{len(cena.situacao)} pessoa(s):",
                          " | ".join(sistema.descrever(n, t) if completo else f"Pessoa {n}" for n, t in cena.situacao))
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
        cv2.destroyAllWindows()

    if args.salvar and ultimo_quadro is not None:
        cv2.imwrite(args.salvar, ultimo_quadro)
        print(f"\nÚltimo quadro salvo em {args.salvar}")
    media = (len(tempos) / sum(tempos)) if tempos else 0
    print(f"\n{processados} quadro(s) | até {maximo_pessoas} pessoa(s) ao mesmo tempo | ~{media:.1f} FPS neste computador")
    if completo:
        print("Alertas que teriam saído:", dict(totais) or "nenhum")
    return 0


if __name__ == "__main__":
    sys.exit(main())
