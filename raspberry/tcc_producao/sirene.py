"""Sirene da borda: um relé ligado a um pino do GPIO da Raspberry Pi.

Duas coisas dependem do hardware e por isso são configuráveis (config.py / .env):
  - O pino, pela numeração FÍSICA da placa (modo BOARD): o pino 11 é o mesmo do teste de bancada.
  - O nível que ACIONA o relé: a maioria dos módulos de relé liga com o pino em BAIXO (LOW) e desliga em ALTO (HIGH).
    O nível contrário é o de REPOUSO. Se a sirene tocar sozinha ao ligar o programa, o nível está invertido:
    troque SIRENE_ATIVA_EM no .env (rode `python3 testar_sirene.py` para conferir de ouvido).

Sem a biblioteca RPi.GPIO (PC, testes) a sirene é simulada no terminal.
"""
import threading
import time


class Sirene:
    def __init__(self, pino, duracao, ativa_em_baixo=True, gpio=None, esperar=time.sleep):
        self.pino = pino
        self.duracao = duracao
        self._gpio = gpio  # módulo RPi.GPIO (ou um falso nos testes); None = tentar importar em `preparar`
        self._esperar = esperar
        self._trava = threading.Lock()
        self.ativo = False  # True quando há GPIO de verdade; False = simulada
        self._nivel_ligado = None
        self._nivel_repouso = None
        self._definir_niveis(ativa_em_baixo)

    def _definir_niveis(self, ativa_em_baixo):
        if self._gpio is not None:
            baixo, alto = self._gpio.LOW, self._gpio.HIGH
        else:
            baixo, alto = 0, 1
        self._nivel_ligado, self._nivel_repouso = (baixo, alto) if ativa_em_baixo else (alto, baixo)
        self._ativa_em_baixo = ativa_em_baixo

    def preparar(self):
        """Configura o pino JÁ em repouso (sem pulso na partida). Devolve True se o GPIO real foi aberto."""
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
            self._gpio.setup(self.pino, self._gpio.OUT, initial=self._nivel_repouso)
        except (RuntimeError, ValueError):
            self._gpio = None
            return False
        self.ativo = True
        return True

    def _definir(self, nivel):
        if self.ativo:
            self._gpio.output(self.pino, nivel)

    def tocar(self):
        """Liga a sirene pelo tempo configurado e volta ao repouso (bloqueia; use `acionar` no laço principal)."""
        with self._trava:
            try:
                if self.ativo:
                    self._definir(self._nivel_ligado)
                else:
                    print("[SIRENE SIMULADA] ligada")
                self._esperar(self.duracao)
            finally:
                if self.ativo:
                    self._definir(self._nivel_repouso)  # mesmo se algo falhar, a sirene não fica ligada
                else:
                    print("[SIRENE SIMULADA] desligada")

    def acionar(self):
        """Dispara a sirene sem bloquear a inferência; se já estiver tocando, ignora."""
        if not self._trava.locked():
            threading.Thread(target=self.tocar, daemon=True).start()

    def encerrar(self, liberar=False):
        """Deixa o relé em repouso ao sair do programa.

        Por padrão NÃO chama GPIO.cleanup(): ele devolve o pino ao estado de entrada (flutuante), e num relé sem
        resistor de pull-up isso pode ligar a sirene logo depois do teste (o que foi visto na bancada). Sem o cleanup
        o pino segue em repouso. Se a biblioteca soltar o pino ao fim do processo, o remédio é um resistor de pull-up.
        """
        if not self.ativo:
            return
        try:
            self._definir(self._nivel_repouso)
        finally:
            if liberar:
                self._gpio.cleanup(self.pino)
            self.ativo = False
