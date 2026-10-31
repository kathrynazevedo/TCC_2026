"""Monitoramento de EPIs na borda (Raspberry Pi): câmera -> YOLO -> sirene + alerta para a API."""
import queue
import signal
import sys
import threading
import time
from pathlib import Path

import cv2

import cliente_api
import config
from deteccao import ROTULOS, AlertasPorPessoa, ocorrencia_da_cena, papeis_faltando
from metricas import (Metricas, RegistroCsv, RegistroExecucao, Resultados, Telemetria, ler_temperatura,
                      ler_throttling, linhas_janela, linhas_terminal)
from reinicio import executar_reinicio, reinicio_devido
from sirene import Sirene

# ==========================================
# SIRENE (GPIO) — simulada quando não está numa Raspberry (ver sirene.py)
# ==========================================
sirene = Sirene(config.PINO_SIRENE, config.DURACAO_SIRENE, ativa_em_baixo=config.SIRENE_ATIVA_EM_BAIXO)


# ==========================================
# THREADS DE APOIO
# ==========================================
parar = threading.Event()
telemetria = Telemetria()  # o heartbeat leva este retrato da placa ao painel "Sistema"


def thread_heartbeat():
    """Avisa a API que a placa está viva; só imprime quando o estado muda."""
    online = None
    while not parar.is_set():
        ok = cliente_api.enviar_heartbeat(telemetria.instantaneo())
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
                print(f"[VÍDEO] Não foi possível abrir a câmera ({config.ocultar_credenciais(config.CAMERA_SOURCE)}). Nova tentativa em 3s...")
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

        t_captura = time.perf_counter()  # marco zero da latência "borda -> alerta"
        frame = cv2.resize(frame, (config.LARGURA_FRAME, config.ALTURA_FRAME))
        ms_redim = (time.perf_counter() - t_captura) * 1000
        try:
            fila_frames.get_nowait()  # descarta o frame antigo
        except queue.Empty:
            pass
        fila_frames.put((frame, t_captura, ms_redim))

    if cap is not None:
        cap.release()


# ==========================================
# PRINCIPAL
# ==========================================
def desenhar_epi(frame, parte):
    """Capacete ou colete que o modelo achou, em amarelo fino: mostra o que foi aceito como 'presente'."""
    x1, y1, x2, y2 = parte.caixa
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 1)
    cv2.putText(frame, f"{parte.nome} {parte.confianca:.2f}", (x1, min(frame.shape[0] - 4, y2 + 14)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)


def descrever(numero, infracoes):
    """Ex.: 'Pessoa 2: sem capacete, sem colete' ou 'Pessoa 1: ok'."""
    return f"Pessoa {numero}: " + (", ".join(ROTULOS.get(t, t) for t in infracoes) or "ok")


def _cracha(frame, linhas, x, y, cor):
    """Faixas coloridas com texto branco (uma por linha), com o canto superior esquerdo em (x, y), dentro do frame.

    Empilhado em linhas curtas para caber na largura de uma pessoa: duas pessoas lado a lado não escondem o crachá uma
    da outra, como acontecia com uma frase só.
    """
    fonte, escala = cv2.FONT_HERSHEY_SIMPLEX, 0.5
    medidas = [cv2.getTextSize(linha, fonte, escala, 1)[0] for linha in linhas]
    largura = max(w for w, _ in medidas) + 8
    altura_linha = max(h for _, h in medidas) + 8
    alto, largo = frame.shape[:2]
    total = altura_linha * len(linhas)
    if y - total >= 0:  # cabe acima da caixa: não cobre a cabeça, onde fica o capacete
        y -= total
    x = max(0, min(x, largo - largura))
    y = max(0, min(y, alto - total))
    for i, (linha, (_, h)) in enumerate(zip(linhas, medidas)):
        topo = y + i * altura_linha
        cv2.rectangle(frame, (x, topo), (x + largura, topo + altura_linha), cor, -1)
        cv2.putText(frame, linha, (x + 4, topo + h + 3), fonte, escala, (255, 255, 255), 1, cv2.LINE_AA)


def desenhar_pessoa(frame, numero, pessoa, infracoes, avaliando=True):
    """Caixa da pessoa (vermelha se há infração confirmada, verde se não) com o crachá dela e o EPI que ela tem.

    Vai na foto enviada à API: quem olha vê a pessoa inteira, o número dela e o que o modelo achou nela.
    `avaliando=False` (modelo sem capacete/colete, só em testes) desenha em cinza e NÃO diz "ok": o EPI nem foi visto.
    """
    x1, y1, x2, y2 = pessoa.caixa
    if not avaliando:
        cor, linhas = (128, 128, 128), [f"Pessoa {numero}", "EPI nao avaliado"]
    elif infracoes:
        cor, linhas = (0, 0, 255), [f"Pessoa {numero}", *(ROTULOS.get(t, t) for t in infracoes)]
    else:
        cor, linhas = (0, 160, 0), [f"Pessoa {numero}", "ok"]
    cv2.rectangle(frame, (x1, y1), (x2, y2), cor, 2)
    for epi in pessoa.epis():
        desenhar_epi(frame, epi)
    _cracha(frame, linhas, x1, y1, cor)


def registrar_resultados(resultados, cena, inferencia_ms, borda_decisao_ms):
    """Alimenta os resultados da tela Sistema com o que o quadro mostrou (ver metricas.Resultados)."""
    por_classe = {"capacete": [], "colete": [], "ausencia": []}
    for _, pessoa, infracoes in cena.pessoas:
        if pessoa.capacete is not None:
            por_classe["capacete"].append(pessoa.capacete.confianca)
        if pessoa.colete is not None:
            por_classe["colete"].append(pessoa.colete.confianca)
        if infracoes:  # o modelo não detecta a falta: vale a confiança da pessoa em infração confirmada
            por_classe["ausencia"].append(pessoa.confianca)
    for classe, valores in por_classe.items():
        if valores:
            resultados.amostrar_confianca(classe, max(valores))
    resultados.registrar_quadro(len(cena.pessoas), inferencia_ms, borda_decisao_ms)


def enviar_ocorrencia(jpeg, ocorrencia, t_captura, metricas):
    """Envia a ocorrência (em thread) e mede o tempo desde que a câmera entregou o quadro até a API confirmar."""
    if cliente_api.processar_ocorrencia(jpeg, ocorrencia) == cliente_api.OK:
        metricas.registrar("borda_api", (time.perf_counter() - t_captura) * 1000)


def main():
    # Import tardio: carregar o ultralytics demora e não é necessário para os testes dos outros módulos.
    from ultralytics import YOLO

    print(f"Carregando modelo: {config.MODELO_PATH}")
    try:
        model = YOLO(config.MODELO_PATH, task="detect")
    except Exception as erro:
        print(f"[ERRO] Não foi possível carregar o modelo: {erro}")
        return 1

    # A infração agora é a ausência de EPI dentro da caixa de uma pessoa: um modelo sem as três classes (ex.: o antigo,
    # com 'Sem_Capacete') nunca alertaria. Melhor recusar na partida do que ficar mudo.
    faltando = papeis_faltando(model.names)
    if faltando:
        print(f"[ERRO] O modelo não tem classe de: {', '.join(faltando)}. Classes encontradas: {list(model.names.values())}")
        print("       Este sistema precisa de um modelo com pessoa, capacete e colete (ver README).")
        return 1
    print(f"[MODELO] Classes: {list(model.names.values())}")

    if sirene.preparar():
        nivel = "BAIXO" if config.SIRENE_ATIVA_EM_BAIXO else "ALTO"
        print(f"[HARDWARE] Sirene no pino físico {config.PINO_SIRENE} (liga em nível {nivel}), {config.DURACAO_SIRENE:g}s por alerta.")
    else:
        print("[HARDWARE] RPi.GPIO indisponível: a sirene será simulada no terminal.")

    if not config.EDGE_API_KEY:
        print("[AVISO] EDGE_API_KEY vazia: a API só aceitará a placa se estiver em modo de desenvolvimento.")

    if config.CONFIANCA_PESSOA < 0.5:
        print("[AVISO] CONFIANCA_PESSOA abaixo de 0,50: o banco da API recusa infração com confiança menor que 0,50 "
              "(erro 500) e esses alertas ficariam presos na fila offline.")

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
        config.CONFIANCA_PESSOA,
        config.LIMIARES_EPI,
        config.ALTURA_MINIMA_PESSOA,
        config.TEMPO_CONFIRMACAO,
    )
    confianca_modelo = config.CONFIANCA_MODELO
    situacao_anterior = ()  # só imprime a situação da cena quando ela muda
    repeticao = f"repete a cada {config.TEMPO_REALERTA:g}s" if config.TEMPO_REALERTA > 0 else "sem repetição"
    print(f"[ALERTAS] Falta de EPI confirmada após {config.TEMPO_CONFIRMACAO:g}s contínuos; um alerta por pessoa ({repeticao}); "
          f"esquece quem some por {config.RASTREADOR_TEMPO_AUSENTE:g}s.")

    metricas = Metricas()
    registro = RegistroExecucao(config.ARQUIVO_ESTADO)
    resultados = Resultados()  # confiança por classe e desempenho por carga de cena (tela Sistema)
    telemetria.configurar(registro, Path(config.MODELO_PATH).name, resultados, config.REINICIAR_APOS_HORAS,
                          config.ARQUIVO_VALIDACAO)
    envios, reiniciar = [], False  # envios em andamento (esperados antes de reiniciar) e pedido de reinício
    csv_metricas = RegistroCsv(config.ARQUIVO_METRICAS)
    if registro.anterior_caiu:
        print("[SISTEMA] A execução anterior não terminou normalmente (queda de energia, travamento ou kill): "
              "contada como queda inesperada.")
    ultimo_resumo, faixa = time.perf_counter(), None
    print("Monitoramento iniciado. Pressione Ctrl+C para sair.")

    try:
        while not parar.is_set():
            try:
                frame, t_captura, ms_redim = fila.get(timeout=1)
            except queue.Empty:
                continue  # câmera ainda conectando; espera sem gastar CPU

            t_inicio = time.perf_counter()
            resultado = model(frame, verbose=False, conf=confianca_modelo)[0]
            velocidade = resultado.speed  # ms de pré-processamento, inferência e NMS medidos pelo próprio Ultralytics

            deteccoes = []
            for box in resultado.boxes:
                nome = model.names[int(box.cls[0])]
                confianca = float(box.conf[0])
                deteccoes.append((nome, confianca, tuple(map(int, box.xyxy[0]))))

            # Chamado a cada frame (mesmo sem detecções) para o rastreador perceber quem saiu de cena.
            t_regras = time.perf_counter()
            cena = alertas.filtrar(deteccoes, time.monotonic())
            t_decisao = time.perf_counter()

            ms_regras = (t_decisao - t_regras) * 1000
            metricas.quadro()
            metricas.registrar("redim", ms_redim)
            metricas.registrar("pre", velocidade["preprocess"])
            metricas.registrar("inf", velocidade["inference"])
            metricas.registrar("pos", velocidade["postprocess"])
            metricas.registrar("regras", ms_regras)
            metricas.registrar("total", ms_redim + velocidade["preprocess"] + velocidade["inference"]
                               + velocidade["postprocess"] + ms_regras)
            metricas.registrar("espera", (t_inicio - t_captura) * 1000)
            metricas.registrar("borda_decisao", (t_decisao - t_captura) * 1000)
            registrar_resultados(resultados, cena, velocidade["inference"], (t_decisao - t_captura) * 1000)

            # Só desenha o que foi mantido: caixas duplicadas ou sem dono não poluem a foto de evidência.
            for numero, pessoa, infracoes in cena.pessoas:
                desenhar_pessoa(frame, numero, pessoa, infracoes)

            if cena.situacao != situacao_anterior:
                situacao_anterior = cena.situacao
                if cena.situacao:
                    resumo = " | ".join(descrever(numero, tipos) for numero, tipos in cena.situacao)
                    print(f"[CENA] {len(cena.situacao)} pessoa(s) em cena: {resumo}")
                else:
                    print("[CENA] ninguém em cena")

            if cena.alertas:
                sirene.acionar()
                metricas.registrar("borda_sirene", (time.perf_counter() - t_captura) * 1000)
                sucesso, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if sucesso:
                    for tipo, conf, numero in cena.alertas:
                        print(f"[ALERTA] {ROTULOS.get(tipo, tipo)}: pessoa {numero}, confiança {conf:.2f}")
                    # A cena inteira vai numa única requisição: uma foto, todas as pessoas e o que é novo.
                    ocorrencia = ocorrencia_da_cena(cena, config.ID_DISPOSITIVO, cliente_api.agora_utc())
                    envio = threading.Thread(
                        target=enviar_ocorrencia, args=(buffer.tobytes(), ocorrencia, t_captura, metricas), daemon=True
                    )
                    envio.start()
                    envios[:] = [e for e in envios if e.is_alive()] + [envio]

            # Resumo periódico no terminal e no CSV (a tabela de latência e processamento do TCC).
            if config.INTERVALO_METRICAS > 0 and time.perf_counter() - ultimo_resumo >= config.INTERVALO_METRICAS:
                ultimo_resumo = time.perf_counter()
                temperatura = ler_temperatura()
                resumo = metricas.fechar_intervalo(temperatura)
                resultados.registrar_temperatura(temperatura)
                limitacao = ler_throttling()
                for linha in linhas_terminal(resumo, registro, limitacao):
                    print(linha)
                csv_metricas.gravar(resumo, registro, limitacao, cliente_api.agora_utc())
                telemetria.atualizar(resumo)
                registro.sinal()  # "sinal de vida": se o programa cair, a próxima partida sabe até quando viveu
                faixa = linhas_janela(resumo)

            if reinicio_devido(registro.ligado_ha(), config.REINICIAR_APOS_HORAS, not cena.pessoas,
                               config.REINICIO_TOLERANCIA_S):
                print(f"[REINÍCIO] {config.REINICIAR_APOS_HORAS:g} h de operação: reinício programado do turno.")
                reiniciar = True
                break

            if config.MOSTRAR_JANELA:
                vista = frame  # a faixa de métricas só vai na tela, nunca na foto de evidência (já codificada acima)
                for i, texto in enumerate(faixa or []):
                    cv2.putText(vista, texto, (8, 20 + 18 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
                cv2.imshow("TCC - Visão Computacional na Borda", vista)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    except KeyboardInterrupt:
        pass
    finally:
        registro.encerrar("reinicio_programado" if reiniciar else None)
        geral = metricas.resumo_geral()
        if geral["total"]:
            print(f"\n[RESUMO] {metricas.quadros_total} quadros | total médio {geral['total'][0]:.0f} ms "
                  f"(p95 {geral['total'][1]:.0f}) | inferência média {geral['inf'][0]:.0f} ms | "
                  f"FPS mínimo {metricas.fps_minimo or 0:.1f} | temperatura máx. {metricas.temp_max or 0:.0f} °C")
        parar.set()
        sirene.encerrar()
        cv2.destroyAllWindows()
        print("\nSistema encerrado.")
    if reiniciar:
        for envio in envios:  # não perde um alerta que ainda está subindo para a API
            envio.join(timeout=15)
        executar_reinicio(config.REINICIO_MODO)
    return 0


if __name__ == "__main__":
    sys.exit(main())
