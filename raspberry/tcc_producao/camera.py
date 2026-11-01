"""Câmeras da placa: a principal e, se houver, uma reserva em espera que assume quando a principal perde o sinal.

Só UMA câmera é lida e analisada por vez (a Raspberry não dá conta de duas ao mesmo tempo). A reserva fica parada, sem
consumir CPU nem rede:
  - a principal ficou `troca_apos` segundos sem entregar imagem: a captura passa para a reserva;
  - com a reserva em uso, a principal é testada a cada `voltar_a_cada` s numa thread à parte (sem atrapalhar o vídeo) e,
    quando entrega alguns quadros seguidos, a captura volta para ela;
  - com a principal em uso, a reserva é testada de tempos em tempos só para avisar se ela não responde.
Sem reserva configurada, tudo se resume a reconectar a mesma câmera.
"""
import queue
import threading
import time

import cv2

import config

PRINCIPAL, RESERVA = "principal", "reserva"

CHECAR_RESERVA_A_CADA_S = 300.0  # com a principal em uso, de quanto em quanto tempo a reserva é testada
PRIMEIRA_CHECAGEM_S = 10.0  # a reserva é testada logo depois da partida, para avisar cedo se ela não responde
QUADROS_DA_SONDAGEM = 3  # quadros seguidos que a sondagem precisa ler para dar a câmera como boa
# Uma câmera para a qual acabamos de trocar e que ainda não entregou nenhum quadro ganha este prazo antes de ser largada:
# com as duas fora do ar, a captura não pode ficar pulando de uma para a outra a cada tentativa.
PRAZO_DA_CAMERA_NOVA_S = 30.0
ESPERA_ABRIR_FALHOU_S = 3.0
ESPERA_PERDEU_SINAL_S = 2.0


def abrir_camera(fonte):
    """Abre a câmera. Em câmera de rede (RTSP/HTTP) define o prazo (CAMERA_TIMEOUT_S) para abrir e para ler um quadro:
    sem ele, uma queda de rede deixa a leitura pendurada para sempre e o sistema para de monitorar sem avisar. Com o
    prazo a leitura falha, e o laço de captura reconecta (ou troca para a reserva)."""
    if isinstance(fonte, str) and "://" in fonte:
        prazo = int(config.CAMERA_TIMEOUT_S * 1000)
        try:
            return cv2.VideoCapture(fonte, cv2.CAP_FFMPEG, [
                cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, prazo, cv2.CAP_PROP_READ_TIMEOUT_MSEC, prazo,
            ])
        except (TypeError, AttributeError, cv2.error):
            pass  # OpenCV antigo, sem esses parâmetros: abre do jeito simples
    return cv2.VideoCapture(fonte)


class Captura:
    """Lê a câmera em uso e mantém só o quadro mais recente na fila; reconecta se cair e, havendo reserva, troca.

    Cada item da fila é (quadro, instante da captura, ms de redimensionamento, câmera de origem), onde a câmera de origem
    é `PRINCIPAL` ou `RESERVA`: quem consome sabe quando a câmera mudou e o enquadramento já não é o mesmo.
    """

    def __init__(self, principal, reserva=None, parar=None, abrir=abrir_camera, relogio=time.monotonic, esperar=None,
                 troca_apos=5.0, voltar_a_cada=30.0, checar_reserva_a_cada=None):
        self.fontes = {PRINCIPAL: principal, RESERVA: reserva}
        self.tem_reserva = reserva is not None
        self.ativa = PRINCIPAL
        self.trocas = 0
        self.reserva_ok = None  # None = ainda não testada
        self.troca_apos = troca_apos
        self.voltar_a_cada = voltar_a_cada  # 0 = não volta sozinho para a principal
        self.checar_reserva_a_cada = CHECAR_RESERVA_A_CADA_S if checar_reserva_a_cada is None else checar_reserva_a_cada
        self._parar = parar if parar is not None else threading.Event()
        self._abrir, self._relogio = abrir, relogio
        self._esperar = esperar if esperar is not None else self._parar.wait  # injetável: os testes não esperam de verdade
        self._cap = None  # só a thread de captura mexe nele
        self._ultimo_ok = relogio()  # último quadro bom da câmera em uso (ou o instante em que ela passou a ser a em uso)
        self._estreando = False  # trocou de câmera e a nova ainda não entregou o primeiro quadro
        self._principal_voltou = threading.Event()
        self._proxima_sondagem = float("inf")
        self._threads = []

    # ---------- vida das threads ----------

    def iniciar(self, fila):
        """Sobe a thread de captura e, havendo reserva, a de sondagem."""
        self._proxima_sondagem = self._relogio() + PRIMEIRA_CHECAGEM_S if self.tem_reserva else float("inf")
        self._threads = [threading.Thread(target=self.executar, args=(fila,), daemon=True, name="captura")]
        if self.tem_reserva:
            self._threads.append(threading.Thread(target=self.sondagem, daemon=True, name="sondagem"))
        for thread in self._threads:
            thread.start()

    def encerrar(self, prazo=5.0):
        """Chame depois de `parar.set()`. As threads não podem estar dentro do OpenCV (C++) quando o Python começa a
        encerrar: derrubadas ali, abortam o processo ("terminate called without an active exception")."""
        for thread in self._threads:
            thread.join(timeout=prazo)

    def executar(self, fila):
        """Laço da thread de captura."""
        self._ultimo_ok = self._relogio()
        try:
            while not self._parar.is_set():
                self.passo(fila)
        finally:
            self._soltar()

    def sondagem(self):
        """Laço da thread que testa a OUTRA câmera (a reserva, ou a principal enquanto a reserva está em uso)."""
        while not self._parar.wait(1.0):
            self.passo_sondagem()

    # ---------- captura ----------

    def passo(self, fila):
        """Uma volta do laço: lê um quadro da câmera em uso ou, sem sinal, reconecta ou troca de câmera."""
        if self._cap is None:
            self._cap = self._conectar()
            if self._cap is None:
                fonte = config.ocultar_credenciais(self.fontes[self.ativa])
                return self._sem_sinal(ESPERA_ABRIR_FALHOU_S, f"Não foi possível abrir a câmera{self._qual()} ({fonte}). "
                                                              f"Nova tentativa em {ESPERA_ABRIR_FALHOU_S:g}s...")
        ok, quadro = self._cap.read()
        if not ok:
            self._soltar()
            return self._sem_sinal(ESPERA_PERDEU_SINAL_S, f"Perda de sinal com a câmera{self._qual()}. Reconectando...")
        self._ultimo_ok = self._relogio()
        self._entregar(fila, quadro)
        if self.ativa == RESERVA and self._principal_voltou.is_set():
            print("[CÂMERA] A principal voltou a responder: retomando por ela.")
            self._trocar(PRINCIPAL)

    def _qual(self):
        return f" {self.ativa}" if self.tem_reserva else ""

    def _conectar(self):
        fonte = self.fontes[self.ativa]
        cap = self._abrir(fonte)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # menos atraso em streams RTSP
        if not cap.isOpened():
            cap.release()
            return None
        print(f"[VÍDEO] Câmera{self._qual()} conectada.")
        return cap

    def _entregar(self, fila, quadro):
        t_captura = time.perf_counter()  # marco zero da latência "borda -> alerta"
        quadro = cv2.resize(quadro, (config.LARGURA_FRAME, config.ALTURA_FRAME))
        ms_redim = (time.perf_counter() - t_captura) * 1000
        try:
            fila.get_nowait()  # descarta o quadro antigo
        except queue.Empty:
            pass
        fila.put((quadro, t_captura, ms_redim, self.ativa))
        self._estreando = False
        if self.ativa == RESERVA:
            self.reserva_ok = True

    def _sem_sinal(self, espera, aviso):
        """A câmera em uso não entregou imagem: espera e tenta de novo, ou, passado `troca_apos`, usa a outra."""
        if self.ativa == RESERVA:
            self.reserva_ok = False
        agora = self._relogio()
        sem_imagem = agora - self._ultimo_ok
        prazo = max(self.troca_apos, PRAZO_DA_CAMERA_NOVA_S) if self._estreando else self.troca_apos
        if self.tem_reserva and sem_imagem >= prazo:
            destino = RESERVA if self.ativa == PRINCIPAL else PRINCIPAL
            print(f"[CÂMERA] Sem imagem da {self.ativa} há {sem_imagem:.0f}s: passando para a {destino} "
                  f"({config.ocultar_credenciais(self.fontes[destino])}).")
            self._trocar(destino)
            return
        print(f"[VÍDEO] {aviso}")
        self._esperar(espera)

    def _trocar(self, destino):
        self._soltar()
        self.ativa = destino
        self.trocas += 1
        self._ultimo_ok = self._relogio()  # a conta de "sem imagem" recomeça para a câmera nova
        self._estreando = True
        self._principal_voltou.clear()
        espera = self.voltar_a_cada if destino == RESERVA else self.checar_reserva_a_cada
        self._proxima_sondagem = self._relogio() + espera if espera > 0 else float("inf")

    def _soltar(self):
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    # ---------- sondagem da outra câmera ----------

    def passo_sondagem(self):
        """Testa a outra câmera quando chega a hora: a reserva só informa; a principal, se boa, chama a captura de volta."""
        if self._relogio() < self._proxima_sondagem:
            return
        em_uso = self.ativa
        alvo = RESERVA if em_uso == PRINCIPAL else PRINCIPAL
        boa = self._sondar(self.fontes[alvo])
        if self.ativa != em_uso:
            return  # a captura trocou de câmera durante o teste: o resultado já não vale
        if alvo == RESERVA:
            self._registrar_reserva(boa)
            espera = self.checar_reserva_a_cada
        else:
            if boa:
                self._principal_voltou.set()
            espera = self.voltar_a_cada
        self._proxima_sondagem = self._relogio() + espera if espera > 0 else float("inf")

    def _sondar(self, fonte):
        """Abre a câmera e lê alguns quadros seguidos; a primeira falha já dá a câmera como ruim (não trava a thread)."""
        cap = None
        try:
            cap = self._abrir(fonte)
            if not cap.isOpened():
                return False
            return all(cap.read()[0] for _ in range(QUADROS_DA_SONDAGEM))
        except cv2.error:
            return False
        finally:
            if cap is not None:
                cap.release()

    def _registrar_reserva(self, boa):
        if boa != self.reserva_ok:  # só fala quando muda: a checagem periódica não enche o terminal
            print("[CÂMERA] A reserva respondeu: pronta para assumir se a principal cair." if boa else
                  "[CÂMERA] ATENÇÃO: a reserva não responde. Se a principal cair, ficará sem câmera.")
        self.reserva_ok = boa

    # ---------- painel ----------

    def estado(self):
        """O que o painel "Sistema" mostra: câmera em uso, nº de trocas e se a reserva respondeu. Vazio sem reserva."""
        if not self.tem_reserva:
            return {}
        dados = {"camera_ativa": self.ativa, "trocas_camera": self.trocas}
        if self.reserva_ok is not None:
            dados["reserva_ok"] = int(self.reserva_ok)
        return dados
