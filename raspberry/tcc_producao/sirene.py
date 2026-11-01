"""Sirene da borda: um relé ligado a um pino do GPIO da Raspberry Pi.

A sirene SEGUE A CENA (`atualizar`, chamado a cada ciclo do laço principal): liga assim que uma falta de EPI é confirmada,
fica ligada enquanto houver alguém sem EPI na frente da câmera e só cala `desliga_apos` segundos depois da última
infração (tolera um quadro em que o modelo "pisca" e quem está saindo de cena). Uma nova infração com a sirene já ligada
só a mantém ligada. Se a câmera parar de entregar quadros ela também cala: sem imagem não há infração para afirmar.
Tudo roda na thread do laço principal, então não há corrida entre ligar e encerrar.

Como o relé é comandado (configurável em config.py / .env):
  - O pino, pela numeração FÍSICA da placa (modo BOARD): o pino 11 é o mesmo do teste de bancada.
  - O nível que LIGA o relé (SIRENE_ATIVA_EM): a maioria dos módulos liga com o pino em BAIXO (LOW).
  - Como DESLIGAR (SIRENE_DESLIGA_SOLTANDO, padrão sim). Muitos módulos de relé são alimentados com 5 V mas comandados
    por um pino de 3,3 V: com o pino forçado em nível ALTO (3,3 V) o LED do optoacoplador ainda tem tensão e o relé NÃO
    desliga (foi o caso da bancada deste projeto). O que desliga é SOLTAR o pino (entrada, sem pull), que não manda tensão
    nenhuma. Então: ligar = conduzir o nível de "ligado"; desligar = soltar o pino.

Quando o programa termina (Ctrl+C, `systemctl stop`, reinício programado), a biblioteca de GPIO solta o pino e ele volta
ao estado de fábrica da Raspberry (entrada com pull-down), que pode ligar um módulo sensível. Por isso, ao encerrar, o
estado "solto, sem pull" é fixado no próprio hardware pelo `pinctrl` (que vem no Raspberry Pi OS) e continua valendo
depois que o processo acaba.

Sem a biblioteca RPi.GPIO (PC, testes) a sirene é simulada no terminal.
"""
import shutil
import subprocess
import time

# Numeração FÍSICA (BOARD) -> BCM (GPIO) do conector de 40 pinos (Raspberry Pi 2, 3, 4 e 5): o `pinctrl` fala em BCM.
BOARD_PARA_BCM = {
    3: 2, 5: 3, 7: 4, 8: 14, 10: 15, 11: 17, 12: 18, 13: 27, 15: 22, 16: 23, 18: 24, 19: 10, 21: 9, 22: 25,
    23: 11, 24: 8, 26: 7, 27: 0, 28: 1, 29: 5, 31: 6, 32: 12, 33: 13, 35: 19, 36: 16, 37: 26, 38: 20, 40: 21,
}


class Sirene:
    def __init__(self, pino, desliga_apos, ativa_em_baixo=True, desliga_soltando=True, gpio=None, relogio=time.monotonic,
                 procurar=shutil.which, rodar=subprocess.run):
        self.pino = pino
        self.desliga_apos = desliga_apos  # segundos sem nenhuma infração até a sirene calar
        self._desliga_soltando = desliga_soltando
        self._gpio = gpio  # módulo RPi.GPIO (ou um falso nos testes); None = tentar importar em `preparar`
        self._relogio = relogio
        self._procurar, self._rodar = procurar, rodar  # injetáveis: os testes não chamam o `pinctrl` de verdade
        self.ativo = False  # True quando há GPIO de verdade; False = simulada
        self.ligada = False  # a sirene está tocando agora
        self._ultima_infracao = float("-inf")  # instante da última infração vista (ligar à mão não conta como infração)
        self._com_falha = False  # o último comando ao GPIO falhou: avisa uma vez, não a cada quadro
        self._nivel_ligado = None
        self._nivel_repouso = None
        self._definir_niveis(ativa_em_baixo)

    @property
    def pino_bcm(self):
        """Número BCM (GPIO) do pino físico, ou None se o pino não é um GPIO (ex.: 3,3 V, GND)."""
        return BOARD_PARA_BCM.get(self.pino)

    def _definir_niveis(self, ativa_em_baixo):
        if self._gpio is not None:
            baixo, alto = self._gpio.LOW, self._gpio.HIGH
        else:
            baixo, alto = 0, 1
        self._nivel_ligado, self._nivel_repouso = (baixo, alto) if ativa_em_baixo else (alto, baixo)
        self._ativa_em_baixo = ativa_em_baixo

    def preparar(self):
        """Deixa o pino JÁ desligado (sem pulso na partida). Devolve True se o GPIO real foi aberto."""
        if self._gpio is None:
            try:
                import RPi.GPIO as gpio
            except (ImportError, RuntimeError):
                return False
            self._gpio = gpio
            self._definir_niveis(self._ativa_em_baixo)
        try:
            self._gpio.setwarnings(False)  # canal usado por uma execução anterior que não limpou o pino
            self._gpio.setmode(self._gpio.BOARD)
            if self._desliga_soltando:
                self._gpio.setup(self.pino, self._gpio.IN, pull_up_down=self._gpio.PUD_OFF)
            else:
                self._gpio.setup(self.pino, self._gpio.OUT, initial=self._nivel_repouso)
        except (RuntimeError, ValueError):
            self._gpio = None
            return False
        self.ativo = True
        return True

    def _comandar(self, ligar):
        """Liga ou desliga o relé. Desligar = soltar o pino (ou conduzir o repouso, se SIRENE_DESLIGA_SOLTANDO=false)."""
        if ligar:
            if self._desliga_soltando:
                self._gpio.setup(self.pino, self._gpio.OUT, initial=self._nivel_ligado)  # de entrada para saída
            else:
                self._gpio.output(self.pino, self._nivel_ligado)
        elif self._desliga_soltando:
            self._gpio.setup(self.pino, self._gpio.IN, pull_up_down=self._gpio.PUD_OFF)
        else:
            self._gpio.output(self.pino, self._nivel_repouso)

    def ligar(self):
        """Liga a sirene e a deixa ligada até `desligar` (o teste de bancada usa isto; o sistema usa `atualizar`)."""
        if self.ativo:
            self._comandar(True)
        else:
            print("[SIRENE SIMULADA] ligada")
        self.ligada = True

    def desligar(self):
        if self.ativo:
            self._comandar(False)
        else:
            print("[SIRENE SIMULADA] desligada")
        self.ligada = False

    def atualizar(self, infracao):
        """Faz a sirene seguir a cena: liga com a primeira infração e só desliga `desliga_apos` s depois da última.

        `infracao` diz se, agora, há alguém em infração confirmada. Chame a cada ciclo do laço principal, também quando
        não chegou quadro (senão a sirene ficaria ligada se a câmera caísse). Devolve True só na chamada que LIGOU a
        sirene: é o instante em que se mede a latência de acionamento.
        """
        agora = self._relogio()
        ligou = False
        try:
            if infracao:
                self._ultima_infracao = agora
                if not self.ligada:
                    self.ligar()
                    ligou = True
            elif self.ligada and agora - self._ultima_infracao >= self.desliga_apos:
                self.desligar()
        except (RuntimeError, OSError) as erro:  # GPIO com problema: o monitoramento segue e tenta de novo no próximo ciclo
            if not self._com_falha:
                print(f"[HARDWARE] Não consegui comandar a sirene ({erro}). Vou tentar de novo a cada ciclo.")
            self._com_falha = True
            return False
        self._com_falha = False
        return ligou

    def _segurar_desligada(self):
        """Fixa o estado "desligado" no hardware para valer DEPOIS que o processo terminar.

        Pino solto: libera o pino na biblioteca (ele já está solto, então não há pulso) e o `pinctrl` reafirma
        "entrada, sem pull" por fora do processo.
        Pino conduzindo o repouso: 1) pull no repouso (com o pino ainda conduzido), 2) solta o pino (o pull mantém o
        nível durante a troca), 3) o `pinctrl` volta a conduzir o repouso.
        """
        bcm = self.pino_bcm
        ferramenta = self._procurar("pinctrl") or self._procurar("raspi-gpio")
        if bcm is None or ferramenta is None:
            motivo = "o pino físico %s não é um GPIO" % self.pino if bcm is None else "falta o `pinctrl` (Raspberry Pi OS)"
            print(f"[HARDWARE] Não dá para segurar o relé desligado depois do fim do programa ({motivo}). "
                  "Se a sirene tocar quando o programa terminar, veja o README (config.txt ou resistor).")
            return
        try:
            if self._desliga_soltando:
                self._gpio.cleanup(self.pino)
                self._rodar([ferramenta, "set", str(bcm), "ip", "pn"], check=True, capture_output=True, timeout=5)
            else:
                repouso_alto = self._nivel_repouso == self._gpio.HIGH
                pull, nivel = ("pu", "dh") if repouso_alto else ("pd", "dl")
                self._rodar([ferramenta, "set", str(bcm), pull], check=True, capture_output=True, timeout=5)
                self._gpio.cleanup(self.pino)
                self._rodar([ferramenta, "set", str(bcm), "op", nivel], check=True, capture_output=True, timeout=5)
        except (OSError, RuntimeError, subprocess.SubprocessError) as erro:
            print(f"[HARDWARE] Não consegui segurar o relé desligado depois do fim do programa ({erro}). "
                  "Se a sirene tocar quando o programa terminar, veja o README (config.txt ou resistor).")

    def encerrar(self):
        """Desliga a sirene ao sair do programa e a mantém desligada depois que o processo terminar."""
        if not self.ativo:
            return
        try:
            self._comandar(False)
        except (RuntimeError, OSError):
            pass  # o pino é solto logo abaixo, de qualquer jeito
        self.ativo = self.ligada = False
        self._segurar_desligada()
