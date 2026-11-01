"""Testes da captura com câmera principal e reserva (câmeras e relógio falsos: rodam em qualquer PC).

    python -m unittest discover -s tests -v      (a partir de raspberry/tcc_producao)
"""
import contextlib
import io
import queue
import sys
import threading
import time
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import camera  # noqa: E402
from camera import PRINCIPAL, RESERVA, Captura  # noqa: E402

CAM_P, CAM_R = "rtsp://usuario:senha@192.168.1.208:554/cam", "rtsp://usuario:senha@192.168.1.209:554/cam"


class Relogio:
    """Relógio que só anda quando o teste (ou uma espera/falha falsa) manda."""

    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def avancar(self, segundos):
        self.t += segundos


class Rede:
    """Estado das câmeras: `vivas[fonte]` diz se ela responde. Câmera morta custa o prazo de abertura/leitura (como no RTSP)."""

    def __init__(self, relogio, prazo=5.0):
        self.relogio, self.prazo = relogio, prazo
        self.vivas = {CAM_P: True, CAM_R: True}
        self.aberturas = []  # a ordem em que as câmeras foram abertas
        self.liberadas = 0

    def abrir(self, fonte):
        self.aberturas.append(fonte)
        return CameraFalsa(self, fonte)


class CameraFalsa:
    def __init__(self, rede, fonte):
        self.rede, self.fonte = rede, fonte
        self.viva_ao_abrir = rede.vivas.get(fonte, False)
        if not self.viva_ao_abrir:
            rede.relogio.avancar(rede.prazo)  # abrir uma câmera morta espera o prazo acabar

    def isOpened(self):
        return self.viva_ao_abrir

    def set(self, *args):
        return True

    def read(self):
        if self.rede.vivas.get(self.fonte, False) and self.viva_ao_abrir:
            return True, np.zeros((48, 64, 3), np.uint8)
        self.rede.relogio.avancar(self.rede.prazo)  # leitura pendurada até o prazo
        return False, None

    def release(self):
        self.rede.liberadas += 1


class TestCaptura(unittest.TestCase):
    def montar(self, com_reserva=True, **kw):
        self.relogio = Relogio()
        self.rede = Rede(self.relogio)
        self.fila = queue.Queue(maxsize=1)
        opcoes = dict(troca_apos=5.0, voltar_a_cada=30.0, checar_reserva_a_cada=300.0)
        opcoes.update(kw)
        self.captura = Captura(CAM_P, CAM_R if com_reserva else None, abrir=self.rede.abrir, relogio=self.relogio,
                               esperar=self.relogio.avancar, **opcoes)
        self.captura._proxima_sondagem = self.relogio() + camera.PRIMEIRA_CHECAGEM_S if com_reserva else float("inf")
        return self.captura

    def passos(self, n):
        """Roda `n` voltas do laço e devolve a câmera de origem de cada quadro entregue (None = volta sem quadro)."""
        origens = []
        for _ in range(n):
            self.captura.passo(self.fila)
            try:
                origens.append(self.fila.get_nowait()[3])
            except queue.Empty:
                origens.append(None)
        return origens

    def silencio(self):
        return contextlib.redirect_stdout(io.StringIO())

    # ---------- sem reserva: o comportamento de sempre ----------

    def test_sem_reserva_reconecta_a_mesma_camera_e_nunca_troca(self):
        self.montar(com_reserva=False)
        self.rede.vivas[CAM_P] = False
        with self.silencio():
            self.passos(10)  # um minuto sem sinal
            self.rede.vivas[CAM_P] = True
            origens = self.passos(3)
        self.assertEqual(origens[-1], PRINCIPAL)
        self.assertEqual((self.captura.ativa, self.captura.trocas), (PRINCIPAL, 0))
        self.assertEqual(set(self.rede.aberturas), {CAM_P})

    def test_sem_reserva_nao_ha_o_que_mostrar_no_painel(self):
        self.assertEqual(self.montar(com_reserva=False).estado(), {})

    # ---------- troca para a reserva ----------

    def test_quadros_trazem_a_camera_de_origem(self):
        self.montar()
        with self.silencio():
            self.assertEqual(self.passos(3), [PRINCIPAL] * 3)  # a 1ª volta conecta e já entrega o quadro

    def test_queda_curta_da_principal_nao_troca(self):
        self.montar(troca_apos=15.0)
        with self.silencio():
            self.passos(2)
            self.rede.vivas[CAM_P] = False
            self.passos(1)  # a leitura pendurou por 5 s: ainda dentro do prazo de 15 s
            self.rede.vivas[CAM_P] = True
            origens = self.passos(3)
        self.assertEqual(self.captura.ativa, PRINCIPAL)
        self.assertEqual(origens[-1], PRINCIPAL)
        self.assertEqual(self.captura.trocas, 0)

    def test_principal_sem_imagem_passa_para_a_reserva(self):
        self.montar()
        with self.silencio():
            self.passos(2)
            self.rede.vivas[CAM_P] = False
            inicio = self.relogio()
            origens = self.passos(4)
        self.assertEqual((self.captura.ativa, self.captura.trocas), (RESERVA, 1))
        self.assertEqual(origens[-1], RESERVA)
        self.assertGreaterEqual(self.relogio() - inicio, self.captura.troca_apos)
        self.assertEqual(self.rede.aberturas[-1], CAM_R)

    def test_a_troca_avisa_no_terminal_sem_vazar_a_senha(self):
        self.montar()
        with self.silencio():
            self.passos(1)
        self.rede.vivas[CAM_P] = False
        with contextlib.redirect_stdout(io.StringIO()) as saida:
            self.passos(3)
        texto = saida.getvalue()
        self.assertIn("passando para a reserva", texto)
        self.assertIn("192.168.1.209", texto)
        self.assertNotIn("senha", texto)

    def test_reserva_tambem_cai_volta_para_a_principal(self):
        self.montar()
        with self.silencio():
            self.passos(1)
            self.rede.vivas[CAM_P] = False
            self.passos(4)  # agora na reserva
            self.assertEqual(self.captura.ativa, RESERVA)
            self.rede.vivas[CAM_P], self.rede.vivas[CAM_R] = True, False
            origens = self.passos(6)
        self.assertEqual(self.captura.ativa, PRINCIPAL)
        self.assertEqual(origens[-1], PRINCIPAL)
        self.assertFalse(self.captura.reserva_ok)

    def test_as_duas_fora_do_ar_nao_ficam_pulando_de_uma_para_a_outra(self):
        self.montar()
        self.rede.vivas[CAM_P] = self.rede.vivas[CAM_R] = False
        with contextlib.redirect_stdout(io.StringIO()) as saida:
            self.passos(60)
        simulado = self.relogio() - 1000.0
        # a primeira troca é rápida (a principal estava em uso); depois cada câmera nova ganha 30 s para estrear
        self.assertGreater(simulado, 300.0)
        self.assertLessEqual(self.captura.trocas, simulado / camera.PRAZO_DA_CAMERA_NOVA_S + 1)
        self.assertLess(saida.getvalue().count("[CÂMERA] Sem imagem"), 20)  # e o terminal não vira uma enxurrada

    def test_camera_nova_que_estreia_normalmente_volta_ao_prazo_curto(self):
        self.montar()
        with self.silencio():
            self.passos(1)
            self.rede.vivas[CAM_P] = False
            self.passos(4)  # trocou para a reserva e ela já entregou quadros
            self.assertEqual(self.captura.ativa, RESERVA)
            self.assertFalse(self.captura._estreando)
            self.rede.vivas[CAM_R] = False
            inicio = self.relogio()
            self.passos(3)
        self.assertEqual(self.captura.ativa, PRINCIPAL)  # largou a reserva no prazo curto, não em 30 s
        self.assertLess(self.relogio() - inicio, camera.PRAZO_DA_CAMERA_NOVA_S)

    # ---------- volta para a principal ----------

    def preparar_na_reserva(self, **kw):
        self.montar(**kw)
        with self.silencio():
            self.passos(1)
            self.rede.vivas[CAM_P] = False
            self.passos(4)
        self.assertEqual(self.captura.ativa, RESERVA)

    def test_principal_que_volta_e_boa_chama_a_captura_de_volta(self):
        self.preparar_na_reserva()
        self.rede.vivas[CAM_P] = True
        self.relogio.avancar(30)  # chega a hora de sondar a principal
        self.captura.passo_sondagem()
        self.assertTrue(self.captura._principal_voltou.is_set())
        with self.silencio():
            origens = self.passos(3)
        self.assertEqual(self.captura.ativa, PRINCIPAL)
        self.assertEqual(origens[-1], PRINCIPAL)
        self.assertEqual(self.captura.trocas, 2)

    def test_sondagem_so_roda_na_hora_marcada(self):
        self.preparar_na_reserva()
        self.rede.vivas[CAM_P] = True
        abertas = len(self.rede.aberturas)
        self.relogio.avancar(10)  # ainda faltam 20 s
        self.captura.passo_sondagem()
        self.assertEqual(len(self.rede.aberturas), abertas)

    def test_principal_ainda_morta_continua_na_reserva(self):
        self.preparar_na_reserva()
        self.relogio.avancar(30)
        self.captura.passo_sondagem()
        self.assertFalse(self.captura._principal_voltou.is_set())
        with self.silencio():
            self.passos(3)
        self.assertEqual(self.captura.ativa, RESERVA)

    def test_sondagem_exige_quadros_seguidos(self):
        self.montar()

        class AbreEFalha(CameraFalsa):
            lidos = 0

            def read(self):
                AbreEFalha.lidos += 1
                return (True, np.zeros((4, 4, 3), np.uint8)) if AbreEFalha.lidos == 1 else (False, None)

        self.captura._abrir = lambda fonte: AbreEFalha(self.rede, fonte)
        self.assertFalse(self.captura._sondar(CAM_P))  # abriu e deu 1 quadro, mas não 3 seguidos
        self.assertEqual(self.rede.liberadas, 1)  # e a câmera da sondagem sempre é solta

    def test_voltar_a_cada_zero_nunca_sonda_a_principal(self):
        self.preparar_na_reserva(voltar_a_cada=0)
        self.rede.vivas[CAM_P] = True
        abertas = len(self.rede.aberturas)
        self.relogio.avancar(100000)
        self.captura.passo_sondagem()
        self.assertEqual(len(self.rede.aberturas), abertas)
        with self.silencio():
            self.passos(3)
        self.assertEqual(self.captura.ativa, RESERVA)  # só volta se a reserva cair

    def test_resultado_de_sondagem_de_antes_da_troca_e_descartado(self):
        self.montar()
        self.relogio.avancar(camera.PRIMEIRA_CHECAGEM_S)
        original = self.captura._sondar

        def sondar_e_trocar(fonte):
            self.captura.ativa = RESERVA  # a captura trocou enquanto a sondagem rodava
            return original(fonte)

        self.captura._sondar = sondar_e_trocar
        self.captura.passo_sondagem()
        self.assertIsNone(self.captura.reserva_ok)  # não registrou um resultado que já não vale

    # ---------- a reserva em espera ----------

    def test_checagem_da_reserva_so_fala_quando_muda(self):
        self.montar()
        self.relogio.avancar(camera.PRIMEIRA_CHECAGEM_S)
        with contextlib.redirect_stdout(io.StringIO()) as saida:
            self.captura.passo_sondagem()  # 1ª checagem: responde
            self.assertTrue(self.captura.reserva_ok)
            self.relogio.avancar(300)
            self.captura.passo_sondagem()  # continua respondendo: calada
            self.rede.vivas[CAM_R] = False
            self.relogio.avancar(300)
            self.captura.passo_sondagem()  # parou de responder: avisa
        linhas = saida.getvalue().splitlines()
        self.assertEqual(len(linhas), 2)
        self.assertIn("pronta para assumir", linhas[0])
        self.assertIn("ATENÇÃO", linhas[1])
        self.assertFalse(self.captura.reserva_ok)

    def test_reserva_em_espera_nao_e_aberta_enquanto_a_principal_vai_bem(self):
        self.montar()
        with self.silencio():
            self.passos(20)
        self.assertEqual(set(self.rede.aberturas), {CAM_P})  # nem uma abertura da reserva fora da checagem

    def test_estado_para_o_painel(self):
        self.montar()
        self.assertEqual(self.captura.estado(), {"camera_ativa": PRINCIPAL, "trocas_camera": 0})
        self.captura.reserva_ok = True
        self.assertEqual(self.captura.estado()["reserva_ok"], 1)
        self.captura.reserva_ok = False
        self.assertEqual(self.captura.estado()["reserva_ok"], 0)


class TestThreads(unittest.TestCase):
    def test_threads_encerram_com_parar_e_soltam_as_cameras(self):
        parar = threading.Event()
        soltas, abertas = [], []

        class Cam:
            def isOpened(self):
                return True

            def set(self, *args):
                return True

            def read(self):
                time.sleep(0.01)
                return True, np.zeros((48, 64, 3), np.uint8)

            def release(self):
                soltas.append(1)

        def abrir(fonte):
            abertas.append(fonte)
            return Cam()

        fila = queue.Queue(maxsize=1)
        captura = Captura(CAM_P, CAM_R, parar, abrir=abrir)
        with contextlib.redirect_stdout(io.StringIO()):
            captura.iniciar(fila)
            self.assertEqual({t.name for t in captura._threads}, {"captura", "sondagem"})
            quadro = fila.get(timeout=2)
            parar.set()
            captura.encerrar()
        self.assertEqual(quadro[3], PRINCIPAL)
        self.assertFalse(any(t.is_alive() for t in captura._threads))
        self.assertTrue(soltas)  # a thread de captura soltou a câmera ao sair

    def test_sem_reserva_nao_sobe_a_thread_de_sondagem(self):
        parar = threading.Event()
        captura = Captura(CAM_P, None, parar, abrir=lambda fonte: None)
        parar.set()  # sai sem tentar abrir nada
        captura.iniciar(queue.Queue(maxsize=1))
        captura.encerrar()
        self.assertEqual([t.name for t in captura._threads], ["captura"])


if __name__ == "__main__":
    unittest.main()
