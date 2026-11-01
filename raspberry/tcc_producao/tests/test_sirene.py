"""Testes da sirene (GPIO e `pinctrl` falsos: rodam em qualquer PC, sem Raspberry).

    python -m unittest discover -s tests -v      (a partir de raspberry/tcc_producao)
"""
import contextlib
import io
import subprocess
import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sirene import BOARD_PARA_BCM, Sirene  # noqa: E402

LIGA_BAIXO = ("setup", 11, "OUT", 0)  # conduz nível baixo = relé ligado
LIGA_ALTO = ("setup", 11, "OUT", 1)
SOLTO = ("setup", 11, "IN", "PUD_OFF")  # entrada sem pull = pino solto = relé desligado
PINCTRL = "/usr/bin/pinctrl"


class GpioFalso:
    """Imita o RPi.GPIO e anota tudo o que foi feito com o pino."""
    LOW, HIGH, OUT, IN, BOARD, PUD_OFF = 0, 1, "OUT", "IN", "BOARD", "PUD_OFF"

    def __init__(self, falha_no_setup=None):
        self.chamadas = []
        self._falha = falha_no_setup

    def setwarnings(self, valor):
        self.chamadas.append(("avisos", valor))

    def setmode(self, modo):
        self.chamadas.append(("modo", modo))

    def setup(self, pino, direcao, initial=None, pull_up_down=None):
        if self._falha:
            raise self._falha
        self.chamadas.append(("setup", pino, direcao, initial if direcao == self.OUT else pull_up_down))

    def output(self, pino, nivel):
        self.chamadas.append(("saida", pino, nivel))

    def cleanup(self, pino=None):
        self.chamadas.append(("limpeza", pino))


class TerminalFalso:
    """Falsos `procurar`/`rodar`: anotam os comandos do pinctrl na MESMA linha do tempo das chamadas ao GPIO."""

    def __init__(self, eventos, tem_pinctrl=True, falha=None):
        self.eventos, self.tem_pinctrl, self.falha = eventos, tem_pinctrl, falha

    def procurar(self, nome):
        return f"/usr/bin/{nome}" if self.tem_pinctrl and nome == "pinctrl" else None

    def rodar(self, comando, **_):
        if self.falha:
            raise self.falha
        self.eventos.append(("cmd", *comando))


class TestSirene(unittest.TestCase):
    def nova(self, ativa_em_baixo=True, desliga_soltando=True, pino=11, tem_pinctrl=False, falha_pinctrl=None, **kw):
        gpio = GpioFalso(**kw)
        terminal = TerminalFalso(gpio.chamadas, tem_pinctrl, falha_pinctrl)
        sirene = Sirene(pino, 2.0, ativa_em_baixo=ativa_em_baixo, desliga_soltando=desliga_soltando, gpio=gpio,
                        esperar=lambda s: None, procurar=terminal.procurar, rodar=terminal.rodar)
        return sirene, gpio

    def apos_preparar(self, sirene, gpio):
        sirene.preparar()
        gpio.chamadas.clear()

    # ---------- desligar = SOLTAR o pino (o que o relé deste projeto exige) ----------

    def test_prepara_em_modo_board_com_o_pino_solto(self):
        sirene, gpio = self.nova()
        self.assertTrue(sirene.preparar())
        self.assertIn(("modo", "BOARD"), gpio.chamadas)  # numeração física: pino 11 é o pino 11 da placa
        self.assertIn(SOLTO, gpio.chamadas)  # nasce desligada, sem conduzir nível nenhum
        self.assertFalse([c for c in gpio.chamadas if c[0] == "saida" or c[:3] == ("setup", 11, "OUT")])

    def test_liga_conduzindo_baixo_e_desliga_soltando(self):
        sirene, gpio = self.nova(ativa_em_baixo=True)
        self.apos_preparar(sirene, gpio)
        sirene.tocar()
        self.assertEqual(gpio.chamadas, [LIGA_BAIXO, SOLTO])  # nunca conduz nível alto (que não desligaria o relé)

    def test_rele_que_liga_em_alto_conduz_alto_e_tambem_desliga_soltando(self):
        sirene, gpio = self.nova(ativa_em_baixo=False)
        self.apos_preparar(sirene, gpio)
        sirene.tocar()
        self.assertEqual(gpio.chamadas, [LIGA_ALTO, SOLTO])

    def test_se_a_espera_falhar_a_sirene_nao_fica_ligada(self):
        gpio = GpioFalso()

        def esperar_e_falhar(_):
            raise KeyboardInterrupt

        sirene = Sirene(11, 2.0, gpio=gpio, esperar=esperar_e_falhar)
        self.apos_preparar(sirene, gpio)
        with self.assertRaises(KeyboardInterrupt):
            sirene.tocar()
        self.assertEqual(gpio.chamadas, [LIGA_BAIXO, SOLTO])  # Ctrl+C no meio do toque: volta a soltar o pino

    def test_acionar_durante_o_toque_e_ignorado(self):
        gpio = GpioFalso()
        solta, tocando = threading.Event(), threading.Event()

        def esperar(_):
            tocando.set()
            solta.wait(2)

        sirene = Sirene(11, 2.0, gpio=gpio, esperar=esperar)
        self.apos_preparar(sirene, gpio)
        sirene.acionar()
        self.assertTrue(tocando.wait(2))
        sirene.acionar()  # já está tocando: não empilha outro toque
        solta.set()
        for _ in range(200):
            if len(gpio.chamadas) >= 2 and not sirene._trava.locked():
                break
            threading.Event().wait(0.01)
        self.assertEqual(gpio.chamadas, [LIGA_BAIXO, SOLTO])

    # ---------- o relé tem de continuar DESLIGADO depois que o programa termina ----------

    def test_encerrar_segura_o_pino_solto_no_hardware(self):
        sirene, gpio = self.nova(tem_pinctrl=True)
        self.apos_preparar(sirene, gpio)
        sirene.encerrar()
        # 1) solto; 2) libera o pino na biblioteca; 3) pinctrl reafirma "entrada sem pull" por fora do processo
        self.assertEqual(gpio.chamadas, [SOLTO, ("limpeza", 11), ("cmd", PINCTRL, "set", "17", "ip", "pn")])
        self.assertFalse([c for c in gpio.chamadas if c[0] == "saida" or c[:3] == ("setup", 11, "OUT")])  # nem um instante ligado

    def test_encerrar_no_meio_do_toque_deixa_desligado(self):
        sirene, gpio = self.nova(tem_pinctrl=True)
        solta, tocando = threading.Event(), threading.Event()

        def esperar(_):
            tocando.set()
            solta.wait(2)

        sirene._esperar = esperar
        self.apos_preparar(sirene, gpio)
        sirene.acionar()
        self.assertTrue(tocando.wait(2))
        sirene.encerrar()  # Ctrl+C no meio do toque
        solta.set()
        for _ in range(200):
            if not sirene._trava.locked():
                break
            threading.Event().wait(0.01)
        self.assertEqual(gpio.chamadas, [LIGA_BAIXO, SOLTO, ("limpeza", 11), ("cmd", PINCTRL, "set", "17", "ip", "pn")])
        self.assertEqual(gpio.chamadas[-1], ("cmd", PINCTRL, "set", "17", "ip", "pn"))  # a thread do toque não religou nada

    def test_raspi_gpio_antigo_tambem_serve_quando_nao_ha_pinctrl(self):
        sirene, gpio = self.nova(tem_pinctrl=False)
        sirene._procurar = lambda nome: "/usr/bin/raspi-gpio" if nome == "raspi-gpio" else None
        self.apos_preparar(sirene, gpio)
        sirene.encerrar()
        self.assertEqual(gpio.chamadas[-1], ("cmd", "/usr/bin/raspi-gpio", "set", "17", "ip", "pn"))

    def test_sem_pinctrl_avisa_e_deixa_o_pino_solto(self):
        sirene, gpio = self.nova(tem_pinctrl=False)
        self.apos_preparar(sirene, gpio)
        with contextlib.redirect_stdout(io.StringIO()) as saida:
            sirene.encerrar()
        self.assertEqual(gpio.chamadas, [SOLTO])  # sem como segurar: só garante que está solto
        self.assertIn("README", saida.getvalue())  # e diz onde ver o que fazer
        sirene.encerrar()  # segunda chamada não quebra nem repete nada
        self.assertEqual(gpio.chamadas, [SOLTO])

    def test_falha_do_pinctrl_nao_derruba_o_encerramento(self):
        sirene, gpio = self.nova(tem_pinctrl=True, falha_pinctrl=subprocess.CalledProcessError(1, "pinctrl"))
        self.apos_preparar(sirene, gpio)
        with contextlib.redirect_stdout(io.StringIO()) as saida:
            sirene.encerrar()
        self.assertIn(SOLTO, gpio.chamadas)
        self.assertIn("Não consegui segurar", saida.getvalue())
        self.assertFalse(sirene.ativo)

    def test_pino_que_nao_e_gpio_nao_chama_o_pinctrl(self):
        sirene, gpio = self.nova(pino=1, tem_pinctrl=True)  # pino físico 1 = 3,3 V
        sirene.preparar()
        gpio.chamadas.clear()
        with contextlib.redirect_stdout(io.StringIO()):
            sirene.encerrar()
        self.assertFalse([c for c in gpio.chamadas if c[0] == "cmd"])

    # ---------- modo alternativo: desligar conduzindo o nível de repouso (módulos que aceitam) ----------

    def test_modo_nivel_conduz_o_repouso_como_antes(self):
        sirene, gpio = self.nova(ativa_em_baixo=True, desliga_soltando=False)
        sirene.preparar()
        self.assertIn(("setup", 11, "OUT", 1), gpio.chamadas)  # nasce conduzindo o repouso (alto)
        gpio.chamadas.clear()
        sirene.tocar()
        self.assertEqual(gpio.chamadas, [("saida", 11, 0), ("saida", 11, 1)])

    def test_modo_nivel_segura_o_repouso_sem_pulso(self):
        sirene, gpio = self.nova(ativa_em_baixo=True, desliga_soltando=False, tem_pinctrl=True)
        self.apos_preparar(sirene, gpio)
        sirene.encerrar()
        self.assertEqual(gpio.chamadas, [
            ("saida", 11, 1),
            ("cmd", PINCTRL, "set", "17", "pu"),
            ("limpeza", 11),
            ("cmd", PINCTRL, "set", "17", "op", "dh"),
        ])

    def test_modo_nivel_com_rele_que_liga_em_alto_segura_em_baixo(self):
        sirene, gpio = self.nova(ativa_em_baixo=False, desliga_soltando=False, tem_pinctrl=True)
        self.apos_preparar(sirene, gpio)
        sirene.encerrar()
        self.assertEqual(gpio.chamadas, [
            ("saida", 11, 0),
            ("cmd", PINCTRL, "set", "17", "pd"),
            ("limpeza", 11),
            ("cmd", PINCTRL, "set", "17", "op", "dl"),
        ])

    # ---------- sem hardware ----------

    def test_sem_gpio_a_sirene_e_simulada_e_nao_quebra(self):
        sirene = Sirene(11, 0.0, esperar=lambda s: None)
        sirene.ativo = False  # PC: RPi.GPIO indisponível
        sirene.tocar()
        sirene.encerrar()

    def test_gpio_que_recusa_o_pino_cai_para_simulada(self):
        sirene, _ = self.nova(falha_no_setup=RuntimeError("sem permissão"))
        self.assertFalse(sirene.preparar())
        self.assertFalse(sirene.ativo)


class TestMapaDosPinos(unittest.TestCase):
    def test_pinos_conhecidos(self):
        self.assertEqual([BOARD_PARA_BCM[p] for p in (3, 5, 7, 11, 12, 13, 15, 40)], [2, 3, 4, 17, 18, 27, 22, 21])

    def test_o_conector_de_40_pinos_tem_28_gpios_sem_repeticao(self):
        self.assertEqual(sorted(BOARD_PARA_BCM.values()), list(range(28)))  # GPIO0 a GPIO27, cada um uma vez
        self.assertTrue(all(1 <= pino <= 40 for pino in BOARD_PARA_BCM))

    def test_pino_bcm_do_objeto(self):
        self.assertEqual(Sirene(11, 1.0).pino_bcm, 17)
        self.assertIsNone(Sirene(1, 1.0).pino_bcm)  # 3,3 V


if __name__ == "__main__":
    unittest.main()
