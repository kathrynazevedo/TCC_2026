"""Testes da sirene (GPIO falso: rodam em qualquer PC, sem Raspberry).

    python -m unittest discover -s tests -v      (a partir de raspberry/tcc_producao)
"""
import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sirene import Sirene  # noqa: E402


class GpioFalso:
    """Imita o RPi.GPIO e anota tudo o que foi feito com o pino."""
    LOW, HIGH, OUT, BOARD = 0, 1, "OUT", "BOARD"

    def __init__(self, falha_no_setup=None):
        self.chamadas = []
        self._falha = falha_no_setup

    def setwarnings(self, valor):
        self.chamadas.append(("avisos", valor))

    def setmode(self, modo):
        self.chamadas.append(("modo", modo))

    def setup(self, pino, direcao, initial=None):
        if self._falha:
            raise self._falha
        self.chamadas.append(("setup", pino, direcao, initial))

    def output(self, pino, nivel):
        self.chamadas.append(("saida", pino, nivel))

    def cleanup(self, pino=None):
        self.chamadas.append(("limpeza", pino))

    def niveis(self):
        return [c[2] for c in self.chamadas if c[0] == "saida"]


class TestSirene(unittest.TestCase):
    def nova(self, ativa_em_baixo=True, **kw):
        gpio = GpioFalso(**kw)
        sirene = Sirene(11, 2.0, ativa_em_baixo=ativa_em_baixo, gpio=gpio, esperar=lambda s: None)
        return sirene, gpio

    def test_prepara_em_modo_board_ja_em_repouso(self):
        sirene, gpio = self.nova(ativa_em_baixo=True)
        self.assertTrue(sirene.preparar())
        self.assertIn(("modo", "BOARD"), gpio.chamadas)  # numeração física: pino 11 é o pino 11 da placa
        # repouso = ALTO num relé que liga em BAIXO: nasce desligado, sem pulso na partida
        self.assertIn(("setup", 11, "OUT", GpioFalso.HIGH), gpio.chamadas)

    def test_rele_que_liga_em_baixo_toca_em_low_e_volta_para_high(self):
        sirene, gpio = self.nova(ativa_em_baixo=True)
        sirene.preparar()
        sirene.tocar()
        self.assertEqual(gpio.niveis(), [GpioFalso.LOW, GpioFalso.HIGH])

    def test_rele_que_liga_em_alto_toca_em_high_e_volta_para_low(self):
        sirene, gpio = self.nova(ativa_em_baixo=False)
        sirene.preparar()
        self.assertIn(("setup", 11, "OUT", GpioFalso.LOW), gpio.chamadas)
        sirene.tocar()
        self.assertEqual(gpio.niveis(), [GpioFalso.HIGH, GpioFalso.LOW])

    def test_se_a_espera_falhar_a_sirene_nao_fica_ligada(self):
        gpio = GpioFalso()

        def esperar_e_falhar(_):
            raise KeyboardInterrupt

        sirene = Sirene(11, 2.0, gpio=gpio, esperar=esperar_e_falhar)
        sirene.preparar()
        with self.assertRaises(KeyboardInterrupt):
            sirene.tocar()
        self.assertEqual(gpio.niveis()[-1], GpioFalso.HIGH)  # voltou ao repouso mesmo assim

    def test_acionar_durante_o_toque_e_ignorado(self):
        gpio = GpioFalso()
        solta, tocando = threading.Event(), threading.Event()

        def esperar(_):
            tocando.set()
            solta.wait(2)

        sirene = Sirene(11, 2.0, gpio=gpio, esperar=esperar)
        sirene.preparar()
        sirene.acionar()
        self.assertTrue(tocando.wait(2))
        sirene.acionar()  # já está tocando: não empilha outro toque
        solta.set()
        for _ in range(200):
            if len(gpio.niveis()) >= 2 and not sirene._trava.locked():
                break
            threading.Event().wait(0.01)
        self.assertEqual(gpio.niveis(), [GpioFalso.LOW, GpioFalso.HIGH])

    def test_encerrar_deixa_em_repouso_e_nao_solta_o_pino(self):
        sirene, gpio = self.nova()
        sirene.preparar()
        sirene.encerrar()
        self.assertEqual(gpio.niveis()[-1], GpioFalso.HIGH)  # repouso
        self.assertFalse([c for c in gpio.chamadas if c[0] == "limpeza"])  # cleanup deixaria o pino flutuando
        sirene.encerrar()  # segunda chamada não quebra
        self.assertEqual(len(gpio.niveis()), 1)

    def test_encerrar_pode_liberar_o_pino_quando_pedido(self):
        sirene, gpio = self.nova()
        sirene.preparar()
        sirene.encerrar(liberar=True)
        self.assertEqual(gpio.chamadas[-1], ("limpeza", 11))

    def test_sem_gpio_a_sirene_e_simulada_e_nao_quebra(self):
        sirene = Sirene(11, 0.0, esperar=lambda s: None)
        sirene.ativo = False  # PC: RPi.GPIO indisponível
        sirene.tocar()
        sirene.encerrar()

    def test_gpio_que_recusa_o_pino_cai_para_simulada(self):
        sirene, _ = self.nova(falha_no_setup=RuntimeError("sem permissão"))
        self.assertFalse(sirene.preparar())
        self.assertFalse(sirene.ativo)


if __name__ == "__main__":
    unittest.main()
