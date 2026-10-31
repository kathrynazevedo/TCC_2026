"""Métricas de desempenho e estabilidade da borda: o que a tabela de latência e processamento do TCC pede.

Sem dependências pesadas (testável fora da Raspberry). O main.py registra os tempos de cada quadro aqui e, a cada
`INTERVALO_METRICAS` segundos, imprime um resumo no terminal e grava uma linha no CSV.

Definições (as mesmas do texto do TCC):
  pré-processamento = redimensionar para 640x480 (OpenCV) + letterbox/normalização do modelo
  inferência        = tempo do modelo TFLite
  pós-processamento = NMS
  tempo total       = pré + inferência + pós + regras de pessoa/alerta (processamento de um quadro já em mãos)
  borda -> decisão  = da leitura do quadro na câmera até a decisão de alertar (inclui a espera na fila)
  borda -> sirene   = da leitura do quadro até a sirene ser acionada
  borda -> API      = da leitura do quadro até a API confirmar o registro (inclui JPEG e rede)
"""
import csv
import json
import os
import subprocess
import threading
import time
from collections import deque
from pathlib import Path

from reinicio import segundos_para_reinicio

SERIES = ("redim", "pre", "inf", "pos", "regras", "total", "espera", "borda_decisao", "borda_sirene", "borda_api")


def _estatistica(valores):
    """(média, p95, pior, n) em ms, ou None se não há amostras."""
    if not valores:
        return None
    ordenados = sorted(valores)
    return (sum(ordenados) / len(ordenados), ordenados[min(len(ordenados) - 1, int(0.95 * len(ordenados)))],
            ordenados[-1], len(ordenados))


class Metricas:
    """Acumula tempos (ms) por quadro e fecha resumos por intervalo, sem perder o acumulado desde a partida."""

    def __init__(self, relogio=time.perf_counter):
        self._relogio = relogio
        self._trava = threading.Lock()  # "borda -> API" é registrada por outra thread
        self._intervalo = {nome: [] for nome in SERIES}
        self._todas = {nome: deque(maxlen=20000) for nome in SERIES}
        self._quadros_intervalo = 0
        self._inicio_intervalo = relogio()
        self._intervalos_fechados = 0
        self.quadros_total = 0
        self.fps_minimo = None  # menor taxa vista em um intervalo completo (o primeiro, com aquecimento, não conta)
        self.temp_max = None

    def registrar(self, nome, ms):
        with self._trava:
            self._intervalo[nome].append(ms)
            self._todas[nome].append(ms)

    def quadro(self):
        with self._trava:
            self._quadros_intervalo += 1
            self.quadros_total += 1

    def fechar_intervalo(self, temperatura=None):
        """Resumo do intervalo que acabou ({série: (média, p95, pior, n)}, fps, ...) e recomeça a contagem."""
        with self._trava:
            agora = self._relogio()
            duracao = max(agora - self._inicio_intervalo, 1e-9)
            fps = self._quadros_intervalo / duracao
            resumo = {nome: _estatistica(valores) for nome, valores in self._intervalo.items()}
            resumo.update(fps=fps, quadros=self._quadros_intervalo, duracao=duracao)
            self._intervalos_fechados += 1
            if self._intervalos_fechados > 1 and self._quadros_intervalo > 0:
                self.fps_minimo = fps if self.fps_minimo is None else min(self.fps_minimo, fps)
            if temperatura is not None:
                self.temp_max = temperatura if self.temp_max is None else max(self.temp_max, temperatura)
            resumo.update(fps_minimo=self.fps_minimo, temp=temperatura, temp_max=self.temp_max)
            self._intervalo = {nome: [] for nome in SERIES}
            self._quadros_intervalo = 0
            self._inicio_intervalo = agora
            return resumo

    def resumo_geral(self):
        """Estatística de TODA a execução (até 20 mil amostras recentes por série)."""
        with self._trava:
            return {nome: _estatistica(list(valores)) for nome, valores in self._todas.items()}


# ==========================================
# SISTEMA (temperatura e limitação térmica)
# ==========================================
def ler_temperatura():
    """Temperatura da CPU em °C (Linux/Raspberry); None onde não existe (ex.: Windows)."""
    try:
        return int(Path("/sys/class/thermal/thermal_zone0/temp").read_text()) / 1000
    except (OSError, ValueError):
        return None


def ler_throttling():
    """'0x0' = sem limitação por temperatura/tensão; qualquer outro valor indica limitação (só na Raspberry)."""
    try:
        saida = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True, timeout=3).stdout
        return saida.strip().split("=")[-1] or None
    except (OSError, subprocess.SubprocessError):
        return None


def ler_memoria():
    """% da memória RAM em uso (Linux/Raspberry); None onde não existe."""
    try:
        valores = {}
        for linha in Path("/proc/meminfo").read_text().splitlines():
            chave, _, resto = linha.partition(":")
            valores[chave] = int(resto.split()[0])
        return round((valores["MemTotal"] - valores["MemAvailable"]) / valores["MemTotal"] * 100, 1)
    except (OSError, KeyError, ValueError, IndexError, ZeroDivisionError):
        return None


def ler_carga():
    """Carga média de 1 min dividida pelo nº de núcleos, em % (100 = todos os núcleos ocupados); None sem /proc."""
    try:
        return round(float(Path("/proc/loadavg").read_text().split()[0]) / (os.cpu_count() or 1) * 100, 1)
    except (OSError, ValueError, IndexError):
        return None


# ==========================================
# ESTABILIDADE (quantas vezes o programa foi reiniciado)
# ==========================================
class RegistroExecucao:
    """Guarda em disco cada partida do programa, para contar reinícios e quedas ao longo de um turno.

    A cada resumo o programa grava um "sinal de vida". Se na próxima partida a execução anterior não foi marcada
    como encerrada de forma limpa, ela caiu (energia, travamento, kill): conta como queda inesperada.
    """

    MAXIMO = 50

    def __init__(self, caminho, agora=time.time):
        self.caminho = Path(caminho)
        self._agora = agora
        self.execucoes = self._ler()
        self.anterior_caiu = bool(self.execucoes) and not self.execucoes[-1].get("limpo", False)
        inicio = self._agora()
        self.execucoes.append({"inicio": inicio, "ultimo_sinal": inicio, "limpo": False})
        self.execucoes = self.execucoes[-self.MAXIMO:]
        self._gravar()

    def _ler(self):
        try:
            dados = json.loads(self.caminho.read_text(encoding="utf-8"))
            return [e for e in dados if isinstance(e, dict) and "inicio" in e]
        except (OSError, ValueError, TypeError):
            return []

    def _gravar(self):
        try:
            temporario = self.caminho.with_suffix(".tmp")
            temporario.write_text(json.dumps(self.execucoes), encoding="utf-8")
            temporario.replace(self.caminho)
        except OSError:
            pass  # nunca derrubar o monitoramento por causa de um arquivo de estatística

    def sinal(self):
        self.execucoes[-1]["ultimo_sinal"] = self._agora()
        self._gravar()

    def encerrar(self, motivo=None):
        """Marca a execução como encerrada de forma limpa; `motivo` (ex.: "reinicio_programado") fica registrado."""
        self.execucoes[-1].update(ultimo_sinal=self._agora(), limpo=True)
        if motivo:
            self.execucoes[-1]["motivo"] = motivo
        self._gravar()

    @property
    def numero(self):
        return len(self.execucoes)

    def ligado_ha(self):
        return self._agora() - self.execucoes[-1]["inicio"]

    def reinicios(self, horas=8):
        """Partidas nas últimas `horas` que vieram depois de outra (cada uma é um reinício) e quantas foram quedas."""
        limite = self._agora() - horas * 3600
        total = quedas = 0
        for i, execucao in enumerate(self.execucoes):
            if i > 0 and execucao["inicio"] >= limite:
                total += 1
                quedas += 0 if self.execucoes[i - 1].get("limpo") else 1
        return total, quedas

    def reinicios_programados(self, horas=8):
        """Quantos dos reinícios das últimas `horas` foram o reinício programado do turno (não são quedas)."""
        limite = self._agora() - horas * 3600
        return sum(
            1 for i, execucao in enumerate(self.execucoes)
            if i > 0 and execucao["inicio"] >= limite and self.execucoes[i - 1].get("motivo") == "reinicio_programado"
        )


# ==========================================
# SAÍDA
# ==========================================
COLUNAS_CSV = [
    "data_hora_utc", "quadros", "fps", "fps_minimo", "pre_ms", "redim_ms", "inferencia_ms", "pos_ms", "regras_ms",
    "total_ms", "total_p95_ms", "borda_decisao_ms", "borda_sirene_ms", "borda_api_ms",
    "temp_c", "temp_max_c", "throttled", "ligado_s", "execucao", "reinicios_8h", "quedas_8h",
]


def _m(estat, indice=0):
    return None if estat is None else estat[indice]


def _fmt(valor, casas=1, unidade=""):
    return "-" if valor is None else f"{valor:.{casas}f}{unidade}"


def _tempo(segundos):
    h, resto = divmod(int(segundos), 3600)
    return f"{h}h{resto // 60:02d}min"


def linhas_terminal(resumo, registro, throttled):
    """Duas linhas legíveis para o terminal."""
    pre = None if resumo["redim"] is None or resumo["pre"] is None else resumo["redim"][0] + resumo["pre"][0]
    total, decisao = resumo["total"], resumo["borda_decisao"]
    reinicios, quedas = registro.reinicios(8)
    desempenho = (
        f"[MÉTRICAS {resumo['duracao']:.0f}s] pré {_fmt(pre, 1, ' ms')} | inferência {_fmt(_m(resumo['inf']), 1, ' ms')} | "
        f"pós {_fmt(_m(resumo['pos']), 1, ' ms')} | total {_fmt(_m(total), 0, ' ms')} (p95 {_fmt(_m(total, 1), 0)}) | "
        f"{resumo['fps']:.1f} FPS (mín. {_fmt(resumo['fps_minimo'], 1)}) | borda→decisão {_fmt(_m(decisao), 0, ' ms')}"
    )
    sistema = (
        f"[SISTEMA] CPU {_fmt(resumo['temp'], 0, ' °C')} (máx. {_fmt(resumo['temp_max'], 0)}) "
        f"limitação {throttled or 'n/d'} | ligado há {_tempo(registro.ligado_ha())} | execução nº {registro.numero} | "
        f"reinícios em 8 h: {reinicios} ({quedas} queda(s)) | "
        f"sirene {_fmt(_m(resumo['borda_sirene']), 0, ' ms')} | API {_fmt(_m(resumo['borda_api']), 0, ' ms')}"
    )
    return desempenho, sistema


def linhas_janela(resumo):
    """Faixa curta para desenhar no vídeo quando há janela."""
    total = _m(resumo["total"])
    return [
        f"{resumo['fps']:.1f} FPS | total {_fmt(total, 0, ' ms')} | inf {_fmt(_m(resumo['inf']), 0, ' ms')}",
        f"CPU {_fmt(resumo['temp'], 0, ' C')} | borda->decisao {_fmt(_m(resumo['borda_decisao']), 0, ' ms')}",
    ]


class RegistroCsv:
    """Uma linha por intervalo: o registro local das medições, com data e hora (abre direto no Excel).

    É a evidência auditável dos números mostrados no painel. Para não encher o cartão SD numa operação contínua, o
    arquivo é rodado ao passar de `limite_bytes`: o cheio vira "<nome>.csv.1" (substituindo o anterior) e um novo começa.
    """

    def __init__(self, caminho, limite_bytes=5_000_000):
        self.caminho = Path(caminho)
        self.limite_bytes = limite_bytes

    def _rodar_se_cheio(self):
        try:
            if self.caminho.exists() and self.caminho.stat().st_size >= self.limite_bytes:
                self.caminho.replace(self.caminho.with_name(self.caminho.name + ".1"))
        except OSError:
            pass

    def gravar(self, resumo, registro, throttled, agora_utc):
        self._rodar_se_cheio()
        novo = not self.caminho.exists() or self.caminho.stat().st_size == 0
        reinicios, quedas = registro.reinicios(8)
        linha = [
            agora_utc, resumo["quadros"], round(resumo["fps"], 2), _fmt(resumo["fps_minimo"], 2),
            _fmt(_m(resumo["pre"]), 2), _fmt(_m(resumo["redim"]), 2), _fmt(_m(resumo["inf"]), 2),
            _fmt(_m(resumo["pos"]), 2), _fmt(_m(resumo["regras"]), 2), _fmt(_m(resumo["total"]), 2),
            _fmt(_m(resumo["total"], 1), 2), _fmt(_m(resumo["borda_decisao"]), 2),
            _fmt(_m(resumo["borda_sirene"]), 2), _fmt(_m(resumo["borda_api"]), 2),
            _fmt(resumo["temp"], 1), _fmt(resumo["temp_max"], 1), throttled or "", int(registro.ligado_ha()),
            registro.numero, reinicios, quedas,
        ]
        try:
            with self.caminho.open("a", newline="", encoding="utf-8") as arquivo:
                escritor = csv.writer(arquivo, delimiter=";")
                if novo:
                    escritor.writerow(COLUNAS_CSV)
                escritor.writerow(linha)
        except OSError:
            pass  # disco cheio ou sem permissão: o terminal continua mostrando as métricas


# ==========================================
# TELEMETRIA (o que o heartbeat leva à API para o painel "Sistema")
# ==========================================
class Telemetria:
    """Retrato da placa para o painel: o laço principal chama `atualizar` a cada resumo de métricas e a thread do
    heartbeat chama `instantaneo` a cada envio. Sensores (temperatura, memória...) são lidos na hora; tempos e FPS
    vêm do último resumo. Os tempos de sirene e API só existem quando houve alerta, então guardam o último conhecido.
    """

    def __init__(self):
        self._trava = threading.Lock()
        self._ultimo = {}
        self._alerta = {}
        self._temp_max = None
        self.registro = None
        self.modelo = None
        self.resultados = None  # `Resultados` do laço principal (confiança por classe, desempenho por carga de cena)
        self.reiniciar_apos_h = 0
        self.arquivo_validacao = None

    def configurar(self, registro, modelo, resultados=None, reiniciar_apos_h=0, arquivo_validacao=None):
        self.registro, self.modelo = registro, modelo
        self.resultados, self.reiniciar_apos_h, self.arquivo_validacao = resultados, reiniciar_apos_h, arquivo_validacao

    def atualizar(self, resumo):
        pre = None if resumo["redim"] is None or resumo["pre"] is None else resumo["redim"][0] + resumo["pre"][0]
        with self._trava:
            self._ultimo = {
                "fps": resumo["fps"], "fps_minimo": resumo["fps_minimo"], "pre_ms": pre,
                "inferencia_ms": _m(resumo["inf"]), "pos_ms": _m(resumo["pos"]),
                "total_ms": _m(resumo["total"]), "total_p95_ms": _m(resumo["total"], 1),
                "borda_decisao_ms": _m(resumo["borda_decisao"]),
            }
            for chave, serie in (("borda_sirene_ms", "borda_sirene"), ("borda_api_ms", "borda_api")):
                valor = _m(resumo[serie])
                if valor is not None:
                    self._alerta[chave] = valor

    def instantaneo(self):
        """Dicionário só com o que existe (None sai), pronto para ir como JSON no heartbeat."""
        temperatura = ler_temperatura()
        with self._trava:
            if temperatura is not None:
                self._temp_max = temperatura if self._temp_max is None else max(self._temp_max, temperatura)
            dados = {
                "temperatura_c": temperatura, "temperatura_max_c": self._temp_max, "limitacao": ler_throttling(),
                "memoria_pct": ler_memoria(), "carga_cpu_pct": ler_carga(), "modelo": self.modelo,
            }
            if self.registro is not None:
                reinicios, quedas = self.registro.reinicios(8)
                dados.update(ligado_s=int(self.registro.ligado_ha()), execucao=self.registro.numero,
                             reinicios_8h=reinicios, quedas_8h=quedas,
                             reinicios_programados_8h=self.registro.reinicios_programados(8))
                falta = segundos_para_reinicio(self.registro.ligado_ha(), self.reiniciar_apos_h)
                if falta is not None:
                    dados.update(reinicio_programado_em_s=int(falta), reinicio_apos_h=self.reiniciar_apos_h)
            dados.update(self._ultimo)
            dados.update(self._alerta)
        if self.resultados is not None:
            dados.update(self.resultados.resumo())
        if self.arquivo_validacao:
            dados["validacao"] = ler_validacao(self.arquivo_validacao)
        return {k: (round(v, 2) if isinstance(v, float) else v) for k, v in dados.items() if v is not None}


# ==========================================
# RESULTADOS DA EXECUÇÃO (o que enche as tabelas do TCC e aparece na tela Sistema)
# ==========================================
class Resultados:
    """Acumula, durante a execução, dois resultados medidos com o sistema em operação:

    - Confiança média por classe (capacete, colete, ausência de EPI). Uma amostra por classe a cada `espaco`
      segundos (quadros seguidos do mesmo capacete são quase iguais e inflariam a contagem); a amostra é a maior
      confiança da classe naquele instante. Em "ausência de EPI" o modelo não detecta a falta: a amostra é a confiança
      da PESSOA em infração confirmada, o mesmo valor que vai para a API.
    - Desempenho por carga de cena: FPS, inferência, latência borda -> decisão e temperatura, separados pela
      quantidade de pessoas no quadro (1, 2, 3 e "4 ou mais"). Cada quadro cai no grupo da sua própria contagem.
    """

    CLASSES = ("capacete", "colete", "ausencia")
    CARGAS = (1, 2, 3, 4)  # 4 = "4 ou mais"
    SALTO_MAXIMO = 5.0  # s: um intervalo maior entre quadros é queda de câmera, não ritmo de processamento

    def __init__(self, relogio=time.perf_counter, espaco=1.0):
        self._trava = threading.Lock()
        self._relogio = relogio
        self._espaco = espaco
        self._conf = {c: [0.0, 0] for c in self.CLASSES}  # [soma, amostras]
        self._ultima_amostra = {c: None for c in self.CLASSES}
        self._cena = {n: {"quadros": 0, "segundos": 0.0, "inf": 0.0, "borda": 0.0, "temp": 0.0, "temp_n": 0}
                      for n in self.CARGAS}
        self._quadros_do_intervalo = {n: 0 for n in self.CARGAS}
        self._ultimo_quadro = None
        self._temp_soma, self._temp_n = 0.0, 0

    def amostrar_confianca(self, classe, valor):
        """Guarda a confiança (0 a 1) se já passou `espaco` desde a última amostra desta classe."""
        agora = self._relogio()
        with self._trava:
            ultima = self._ultima_amostra[classe]
            if ultima is not None and agora - ultima < self._espaco:
                return
            self._ultima_amostra[classe] = agora
            self._conf[classe][0] += valor
            self._conf[classe][1] += 1

    def registrar_quadro(self, pessoas, inferencia_ms, borda_decisao_ms):
        """Registra um quadro processado, com quantas pessoas apareceram nele (0 = não entra na tabela de carga)."""
        agora = self._relogio()
        with self._trava:
            anterior, self._ultimo_quadro = self._ultimo_quadro, agora
            if pessoas < 1 or anterior is None or agora - anterior > self.SALTO_MAXIMO:
                return
            grupo_id = min(pessoas, self.CARGAS[-1])
            grupo = self._cena[grupo_id]
            grupo["quadros"] += 1
            grupo["segundos"] += agora - anterior
            grupo["inf"] += inferencia_ms
            grupo["borda"] += borda_decisao_ms
            self._quadros_do_intervalo[grupo_id] += 1

    def registrar_temperatura(self, celsius):
        """Uma leitura de temperatura; é atribuída ao grupo de carga que dominou o intervalo que acabou."""
        if celsius is None:
            return
        with self._trava:
            self._temp_soma += celsius
            self._temp_n += 1
            if any(self._quadros_do_intervalo.values()):
                dominante = max(self._quadros_do_intervalo, key=self._quadros_do_intervalo.get)
                self._cena[dominante]["temp"] += celsius
                self._cena[dominante]["temp_n"] += 1
            self._quadros_do_intervalo = {n: 0 for n in self.CARGAS}

    def resumo(self):
        """Dicionário só com o que já tem dados, pronto para o heartbeat."""
        with self._trava:
            saida = {}
            for classe, (soma, n) in self._conf.items():
                if n:
                    saida[f"conf_{classe}_pct"] = round(soma / n * 100, 1)
                    saida[f"conf_{classe}_n"] = n
            carga = {}
            for pessoas, g in self._cena.items():
                if g["quadros"] and g["segundos"] > 0:
                    item = {"quadros": g["quadros"], "fps": round(g["quadros"] / g["segundos"], 2),
                            "inferencia_ms": round(g["inf"] / g["quadros"], 1),
                            "borda_decisao_ms": round(g["borda"] / g["quadros"], 1)}
                    if g["temp_n"]:
                        item["temperatura_c"] = round(g["temp"] / g["temp_n"], 1)
                    carga[str(pessoas)] = item
            if carga:
                saida["carga_cena"] = carga
            if self._temp_n:
                saida["temperatura_media_c"] = round(self._temp_soma / self._temp_n, 1)
            return saida


def _numero_valido(valor, minimo, maximo):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool) and minimo <= valor <= maximo


def ler_validacao(caminho):
    """Resultado da validação do modelo (mAP por classe) gravado no Colab; None se o arquivo não existe ou é inválido.

    Formato: {"modelo": "...", "conjunto": "test", "imagens": 1272, "classes": {"capacete": {"precisao": 0.9,
    "recall": 0.8, "map50": 0.9, "map50_95": 0.6}, ..., "todas": {...}}}. O Colab gera esse arquivo (ver README).
    """
    try:
        bruto = json.loads(Path(caminho).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(bruto, dict) or not isinstance(bruto.get("classes"), dict):
        return None
    classes = {}
    for nome, valores in bruto["classes"].items():
        if not isinstance(valores, dict):
            continue
        limpo = {k: float(valores[k]) for k in ("precisao", "recall", "map50", "map50_95")
                 if _numero_valido(valores.get(k), 0, 1)}
        if limpo:
            classes[str(nome)[:30]] = limpo
    if not classes:
        return None
    saida = {"classes": classes}
    for chave in ("modelo", "conjunto"):
        if isinstance(bruto.get(chave), str) and bruto[chave].strip():
            saida[chave] = bruto[chave].strip()[:80]
    if _numero_valido(bruto.get("imagens"), 0, 10**9):
        saida["imagens"] = int(bruto["imagens"])
    return saida
