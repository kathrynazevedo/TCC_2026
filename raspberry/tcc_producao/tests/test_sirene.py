"""Testes da sirene (GPIO, relógio e `pinctrl` falsos: rodam em qualquer PC, sem Raspberry).

    python -m unittest discover -s tests -v      (a partir de raspberry/tcc_producao)
"""
import contextlib
import io
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sirene import BOARD_PARA_BCM, Sirene  # noqa: E402

LIGA_BAIXO = ("setup", 11, "OUT", 0)  # conduz nível baixo = relé ligado
LIGA_ALTO = ("setup", 11, "OUT", 1)
SOLTO = ("setup", 11, "IN", "PUD_OFF")  # entrada sem pull = pino solto = relé desligado
PINCTRL = "/usr/bin/pinctrl"
ESPERA = 2.0  # SIRENE_DESLIGA_APOS usado nos testes


class GpioFalso:
    """Imita o RPi.GPIO e anota tudo o que foi feito com o pino."""
    LOW, HIGH, OUT, IN, BOARD, PUD_OFF = 0, 1, "OUT", "IN", "BOARD", "PUD_OFF"

    def __init__(self, falha_no_setup=None):
        self.chamadas = []
        self.falha = falha_no_setup  # levantada em qualquer `setup`
        self.falhas_ao_ligar = 0  # quantos `setup` como SAÍDA (ligar a sirene) ainda vão falhar

    def setwarnings(self, valor):
        self.chamadas.append(("avisos", valor))

    def setmode(self, modo):
        self.chamadas.append(("modo", modo))

    def setup(self, pino, direcao, initial=None, pull_up_down=None):
        if self.falha:
            raise self.falha
        if direcao == self.OUT and self.falhas_ao_ligar:
            self.falhas_ao_ligar -= 1
            raise RuntimeError("canal ocupado")
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


class Relogio:
    """Relógio que só anda quando o teste manda."""

    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t

    def avancar(self, segundos):
        self.t += segundos


class TestSirene(unittest.TestCase):
    def nova(self, ativa_em_baixo=True, desliga_soltando=True, pino=11, tem_pinctrl=False, falha_pinctrl=None, **kw):
        gpio = GpioFalso(**kw)
        terminal = TerminalFalso(gpio.chamadas, tem_pinctrl, falha_pinctrl)
        self.relogio = Relogio()
        sirene = Sirene(pino, ESPERA, ativa_em_baixo=ativa_em_baixo, desliga_soltando=desliga_soltando, gpio=gpio,
                        relogio=self.relogio, procurar=terminal.procurar, rodar=terminal.rodar)
        return sirene, gpio

    def apos_preparar(self, sirene, gpio):
        sirene.preparar()
        gpio.chamadas.clear()

    # ---------- partida ----------

    def test_prepara_em_modo_board_com_o_pino_solto(self):
        sirene, gpio = self.nova()
        self.assertTrue(sirene.preparar())
        self.assertIn(("modo", "BOARD"), gpio.chamadas)  # numeração física: pino 11 é o pino 11 da placa
        self.assertIn(SOLTO, gpio.chamadas)  # nasce desligada, sem conduzir nível nenhum
        self.assertFalse([c for c in gpio.chamadas if c[0] == "saida" or c[:3] == ("setup", 11, "OUT")])
        self.assertFalse(sirene.ligada)

    # ---------- a sirene segue a cena: liga com a infração, fica ligada enquanto ela durar, cala depois ----------

    def test_liga_na_primeira_infracao_conduzindo_baixo(self):
        sirene, gpio = self.nova(ativa_em_baixo=True)
        self.apos_preparar(sirene, gpio)
        self.assertTrue(sirene.atualizar(True))  # devolve True na chamada que LIGOU (é aí que se mede a latência)
        self.assertEqual(gpio.chamadas, [LIGA_BAIXO])
        self.assertTrue(sirene.ligada)

    def test_enquanto_ha_infracao_fica_ligada_sem_repetir_comando(self):
        sirene, gpio = self.nova()
        self.apos_preparar(sirene, gpio)
        resultados = []
        for _ in range(60):  # 30 s de infração, um quadro a cada 0,5 s
            resultados.append(sirene.atualizar(True))
            self.relogio.avancar(0.5)
        self.assertEqual(resultados, [True] + [False] * 59)  # só a primeira chamada liga
        self.assertEqual(gpio.chamadas, [LIGA_BAIXO])  # e o pino não é mexido de novo a cada quadro
        self.assertTrue(sirene.ligada)

    def test_so_desliga_depois_do_tempo_de_espera_sem_infracao(self):
        sirene, gpio = self.nova()
        self.apos_preparar(sirene, gpio)
        sirene.atualizar(True)
        self.relogio.avancar(ESPERA - 0.1)
        self.assertFalse(sirene.atualizar(False))
        self.assertEqual(gpio.chamadas, [LIGA_BAIXO])  # ainda dentro do tempo de espera: continua ligada
        self.relogio.avancar(0.1)
        sirene.atualizar(False)
        self.assertEqual(gpio.chamadas, [LIGA_BAIXO, SOLTO])  # desliga SOLTANDO o pino, nunca conduzindo alto
        self.assertFalse(sirene.ligada)

    def test_um_quadro_sem_infracao_nao_corta_a_sirene(self):
        # O modelo "pisca": num quadro enxerga um capacete que não existe. A infração some e volta; a sirene não pode picotar.
        sirene, gpio = self.nova()
        self.apos_preparar(sirene, gpio)
        sirene.atualizar(True)  # t = 0
        self.relogio.avancar(0.5)
        sirene.atualizar(False)  # t = 0,5: quadro sem infração
        self.relogio.avancar(0.5)
        sirene.atualizar(True)  # t = 1,0: a infração voltou
        self.relogio.avancar(1.5)
        sirene.atualizar(False)  # t = 2,5: 1,5 s desde a última infração
        self.assertEqual(gpio.chamadas, [LIGA_BAIXO])
        self.relogio.avancar(0.5)
        sirene.atualizar(False)  # t = 3,0: 2 s desde a última infração
        self.assertEqual(gpio.chamadas, [LIGA_BAIXO, SOLTO])

    def test_quem_se_equipa_ou_sai_de_cena_faz_a_sirene_calar(self):
        sirene, gpio = self.nova()
        self.apos_preparar(sirene, gpio)
        sirene.atualizar(True)
        for _ in range(8):  # a pessoa colocou o capacete: cada quadro seguinte chega sem infração
            self.relogio.avancar(0.5)
            sirene.atualizar(False)
        self.assertEqual(gpio.chamadas, [LIGA_BAIXO, SOLTO])

    def test_se_a_camera_cair_a_sirene_cala(self):
        # Sem quadros o laço principal chama atualizar(False) a cada segundo de espera: não dá para afirmar infração.
        sirene, gpio = self.nova()
        self.apos_preparar(sirene, gpio)
        sirene.atualizar(True)
        self.relogio.avancar(1.0)
        sirene.atualizar(False)
        self.assertTrue(sirene.ligada)
        self.relogio.avancar(1.0)
        sirene.atualizar(False)
        self.assertFalse(sirene.ligada)
        self.assertEqual(gpio.chamadas, [LIGA_BAIXO, SOLTO])

    def test_nova_infracao_depois_de_calar_liga_de_novo(self):
        sirene, gpio = self.nova()
        self.apos_preparar(sirene, gpio)
        self.assertTrue(sirene.atualizar(True))
        self.relogio.avancar(ESPERA)
        sirene.atualizar(False)
        self.assertTrue(sirene.atualizar(True))  # tirou o capacete de novo: toca outra vez
        self.assertEqual(gpio.chamadas, [LIGA_BAIXO, SOLTO, LIGA_BAIXO])

    def test_rele_que_liga_em_alto_conduz_alto_e_tambem_desliga_soltando(self):
        sirene, gpio = self.nova(ativa_em_baixo=False)
        self.apos_preparar(sirene, gpio)
        sirene.atualizar(True)
        self.relogio.avancar(ESPERA)
        sirene.atualizar(False)
        self.assertEqual(gpio.chamadas, [LIGA_ALTO, SOLTO])

    def test_ligar_e_desligar_a_mao_para_o_teste_de_bancada(self):
        sirene, gpio = self.nova()
        self.apos_preparar(sirene, gpio)
        sirene.ligar()
        self.assertTrue(sirene.ligada)
        sirene.desligar()
        self.assertFalse(sirene.ligada)
        self.assertEqual(gpio.chamadas, [LIGA_BAIXO, SOLTO])  # nunca conduz nível alto (que não desligaria o relé)

    def test_ligada_a_mao_nao_conta_como_infracao(self):
        sirene, gpio = self.nova()
        self.apos_preparar(sirene, gpio)
        sirene.ligar()
        sirene.atualizar(False)  # nenhuma infração foi vista: o primeiro ciclo já desliga
        self.assertEqual(gpio.chamadas, [LIGA_BAIXO, SOLTO])

    # ---------- um problema no GPIO não derruba o monitoramento ----------

    def test_falha_ao_ligar_nao_derruba_e_tenta_de_novo(self):
        sirene, gpio = self.nova()
        self.apos_preparar(sirene, gpio)
        gpio.falhas_ao_ligar = 2
        with contextlib.redirect_stdout(io.StringIO()) as saida:
            self.assertFalse(sirene.atualizar(True))
            self.assertFalse(sirene.atualizar(True))
        self.assertFalse(sirene.ligada)
        self.assertEqual(saida.getvalue().count("Não consegui comandar a sirene"), 1)  # avisa uma vez, não a cada quadro
        self.assertTrue(sirene.atualizar(True))  # o GPIO voltou: liga e devolve True
        self.assertEqual(gpio.chamadas, [LIGA_BAIXO])
        self.assertTrue(sirene.ligada)

    # ---------- o relé tem de continuar DESLIGADO depois que o programa termina ----------

    def test_encerrar_segura_o_pino_solto_no_hardware(self):
        sirene, gpio = self.nova(tem_pinctrl=True)
        self.apos_preparar(sirene, gpio)
        sirene.encerrar()
        # 1) solto; 2) libera o pino na biblioteca; 3) pinctrl reafirma "entrada sem pull" por fora do processo
        self.assertEqual(gpio.chamadas, [SOLTO, ("limpeza", 11), ("cmd", PINCTRL, "set", "17", "ip", "pn")])
        self.assertFalse([c for c in gpio.chamadas if c[0] == "saida" or c[:3] == ("setup", 11, "OUT")])  # nem um instante ligado

    def test_encerrar_com_a_sirene_ligada_deixa_desligado(self):
        sirene, gpio = self.nova(tem_pinctrl=True)
        self.apos_preparar(sirene, gpio)
        sirene.atualizar(True)
        sirene.encerrar()  # Ctrl+C / systemctl stop com a sirene tocando
        self.assertEqual(gpio.chamadas, [LIGA_BAIXO, SOLTO, ("limpeza", 11), ("cmd", PINCTRL, "set", "17", "ip", "pn")])
        self.assertFalse(sirene.ligada)
        self.assertFalse(sirene.ativo)

    def test_erro_do_gpio_ao_encerrar_nao_impede_de_segurar_o_pino(self):
        sirene, gpio = self.nova(tem_pinctrl=True)
        self.apos_preparar(sirene, gpio)
        sirene.atualizar(True)
        gpio.chamadas.clear()
        gpio.falha = RuntimeError("canal inválido")
        sirene.encerrar()
        self.assertEqual(gpio.chamadas, [("limpeza", 11), ("cmd", PINCTRL, "set", "17", "ip", "pn")])
        self.assertFalse(sirene.ligada)

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

    def test_modo_nivel_conduz_o_repouso(self):
        sirene, gpio = self.nova(ativa_em_baixo=True, desliga_soltando=False)
        sirene.preparar()
        self.assertIn(("setup", 11, "OUT", 1), gpio.chamadas)  # nasce conduzindo o repouso (alto)
        gpio.chamadas.clear()
        sirene.atualizar(True)
        self.relogio.avancar(ESPERA)
        sirene.atualizar(False)
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

    def test_sem_gpio_a_sirene_e_simulada_no_terminal_e_nao_quebra(self):
        relogio = Relogio()
        sirene = Sirene(11, ESPERA, relogio=relogio)  # PC: RPi.GPIO indisponível, `preparar` nunca foi chamado
        with contextlib.redirect_stdout(io.StringIO()) as saida:
            self.assertTrue(sirene.atualizar(True))
            relogio.avancar(ESPERA)
            sirene.atualizar(False)
            sirene.encerrar()
        self.assertEqual(saida.getvalue().splitlines(), ["[SIRENE SIMULADA] ligada", "[SIRENE SIMULADA] desligada"])

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
