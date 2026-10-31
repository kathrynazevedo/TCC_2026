"""Testes dos resultados acumulados (confiança por classe, desempenho por carga de cena), da validação do modelo e do
reinício programado. Rodam em qualquer PC.

    python -m unittest discover -s tests -v      (a partir de raspberry/tcc_producao)
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import reinicio  # noqa: E402
from metricas import RegistroExecucao, Resultados, Telemetria, ler_validacao  # noqa: E402


class Relogio:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


class TestConfiancaPorClasse(unittest.TestCase):
    def setUp(self):
        self.r = Relogio()
        self.res = Resultados(relogio=self.r, espaco=1.0)

    def test_media_das_amostras_por_classe(self):
        for valor in (0.80, 0.90, 0.85):
            self.res.amostrar_confianca("capacete", valor)
            self.r.t += 1.0
        resumo = self.res.resumo()
        self.assertEqual((resumo["conf_capacete_pct"], resumo["conf_capacete_n"]), (85.0, 3))
        self.assertNotIn("conf_colete_pct", resumo)  # classe sem amostras não aparece (a tela mostra "—")

    def test_quadros_seguidos_contam_como_uma_amostra_so(self):
        for _ in range(30):  # 30 quadros em 0,3 s: é o mesmo capacete parado
            self.res.amostrar_confianca("colete", 0.70)
            self.r.t += 0.01
        self.assertEqual(self.res.resumo()["conf_colete_n"], 1)

    def test_classes_tem_espacamento_independente(self):
        self.res.amostrar_confianca("capacete", 0.9)
        self.res.amostrar_confianca("colete", 0.7)
        self.assertEqual((self.res.resumo()["conf_capacete_n"], self.res.resumo()["conf_colete_n"]), (1, 1))


class TestCargaDeCena(unittest.TestCase):
    def setUp(self):
        self.r = Relogio()
        self.res = Resultados(relogio=self.r)

    def quadros(self, pessoas, quantidade, dt=0.5, inferencia=490.0, borda=520.0):
        for _ in range(quantidade):
            self.r.t += dt
            self.res.registrar_quadro(pessoas, inferencia, borda)

    def test_fps_inferencia_e_latencia_por_quantidade_de_pessoas(self):
        self.res.registrar_quadro(1, 1, 1)  # 1º quadro: só marca o relógio
        self.quadros(1, 20, dt=0.5, inferencia=480.0, borda=510.0)  # 2 FPS
        self.quadros(2, 10, dt=0.5, inferencia=490.0, borda=520.0)
        self.quadros(4, 10, dt=1.0, inferencia=500.0, borda=540.0)  # 1 FPS
        carga = self.res.resumo()["carga_cena"]
        self.assertEqual((carga["1"]["fps"], carga["1"]["inferencia_ms"], carga["1"]["borda_decisao_ms"]), (2.0, 480.0, 510.0))
        self.assertEqual(carga["2"]["quadros"], 10)
        self.assertEqual((carga["4"]["fps"], carga["4"]["inferencia_ms"]), (1.0, 500.0))
        self.assertNotIn("3", carga)  # nunca houve 3 pessoas

    def test_quatro_ou_mais_pessoas_ficam_no_mesmo_grupo(self):
        self.res.registrar_quadro(1, 1, 1)
        self.quadros(4, 5)
        self.quadros(7, 5)
        self.assertEqual(self.res.resumo()["carga_cena"]["4"]["quadros"], 10)

    def test_quadro_sem_pessoas_nao_entra_na_tabela(self):
        self.res.registrar_quadro(0, 1, 1)
        self.quadros(0, 10)
        self.assertNotIn("carga_cena", self.res.resumo())

    def test_queda_de_camera_nao_estraga_o_fps(self):
        self.res.registrar_quadro(1, 1, 1)
        self.quadros(1, 10, dt=0.5)
        self.quadros(1, 1, dt=60.0)  # câmera caiu 1 min: esse intervalo não é ritmo de processamento
        self.quadros(1, 10, dt=0.5)
        self.assertEqual(self.res.resumo()["carga_cena"]["1"]["fps"], 2.0)

    def test_temperatura_vai_para_o_grupo_que_dominou_o_intervalo(self):
        self.res.registrar_quadro(1, 1, 1)
        self.quadros(2, 8)
        self.quadros(1, 2)
        self.res.registrar_temperatura(55.0)  # intervalo dominado por 2 pessoas
        self.quadros(1, 10)
        self.res.registrar_temperatura(61.0)  # intervalo dominado por 1 pessoa
        resumo = self.res.resumo()
        self.assertEqual((resumo["carga_cena"]["2"]["temperatura_c"], resumo["carga_cena"]["1"]["temperatura_c"]), (55.0, 61.0))
        self.assertEqual(resumo["temperatura_media_c"], 58.0)

    def test_sem_sensor_de_temperatura_nao_quebra(self):
        self.res.registrar_temperatura(None)
        self.assertNotIn("temperatura_media_c", self.res.resumo())


class TestValidacaoDoModelo(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.arquivo = Path(self._tmp.name) / "validacao.json"

    def gravar(self, conteudo):
        self.arquivo.write_text(conteudo if isinstance(conteudo, str) else json.dumps(conteudo), encoding="utf-8")

    def test_le_o_arquivo_gerado_no_colab(self):
        self.gravar({"modelo": "best.pt", "conjunto": "test", "imagens": 1272, "classes": {
            "capacete": {"precisao": 0.9, "recall": 0.85, "map50": 0.92, "map50_95": 0.6},
            "todas": {"precisao": 0.88, "recall": 0.84, "map50": 0.9, "map50_95": 0.55}}})
        valida = ler_validacao(self.arquivo)
        self.assertEqual((valida["conjunto"], valida["imagens"]), ("test", 1272))
        self.assertEqual(valida["classes"]["todas"]["map50"], 0.9)

    def test_valores_fora_de_0_a_1_ou_de_tipo_errado_sao_descartados(self):
        self.gravar({"classes": {"colete": {"precisao": 87, "recall": "alto", "map50": 0.9, "map50_95": True}}})
        self.assertEqual(ler_validacao(self.arquivo)["classes"]["colete"], {"map50": 0.9})

    def test_arquivo_ausente_ou_quebrado_vira_none(self):
        self.assertIsNone(ler_validacao(self.arquivo))
        self.gravar("{quebrado")
        self.assertIsNone(ler_validacao(self.arquivo))
        self.gravar({"classes": {}})
        self.assertIsNone(ler_validacao(self.arquivo))


class TestReinicioProgramado(unittest.TestCase):
    H = 3600

    def test_nao_reinicia_antes_do_tempo(self):
        self.assertFalse(reinicio.reinicio_devido(7.9 * self.H, 8, ninguem_em_cena=True))

    def test_depois_do_tempo_espera_a_cena_ficar_vazia(self):
        self.assertTrue(reinicio.reinicio_devido(8.1 * self.H, 8, ninguem_em_cena=True))
        self.assertFalse(reinicio.reinicio_devido(8.01 * self.H, 8, ninguem_em_cena=False))  # tem gente: espera

    def test_canteiro_sempre_movimentado_nao_adia_para_sempre(self):
        self.assertTrue(reinicio.reinicio_devido(8 * self.H + 601, 8, ninguem_em_cena=False, tolerancia_s=600))

    def test_zero_desliga(self):
        self.assertFalse(reinicio.reinicio_devido(100 * self.H, 0, ninguem_em_cena=True))
        self.assertIsNone(reinicio.segundos_para_reinicio(100 * self.H, 0))

    def test_quanto_falta(self):
        self.assertEqual(reinicio.segundos_para_reinicio(3 * self.H, 8), 5 * self.H)
        self.assertEqual(reinicio.segundos_para_reinicio(9 * self.H, 8), 0)

    def test_modo_programa_reabre_o_proprio_interpretador(self):
        chamadas = []
        self.assertTrue(reinicio.executar_reinicio("programa", executar=lambda *a: chamadas.append(a)))
        self.assertEqual(chamadas[0][0], sys.executable)

    def test_modo_placa_chama_reboot_sem_pedir_senha(self):
        comandos = []
        self.assertTrue(reinicio.executar_reinicio("placa", rodar=lambda cmd, **kw: comandos.append(cmd)))
        self.assertEqual(comandos, [["sudo", "-n", "reboot"]])

    def test_se_o_reboot_falhar_reinicia_so_o_programa(self):
        chamadas = []

        def rodar(*a, **kw):
            raise subprocess.CalledProcessError(1, "sudo")

        self.assertTrue(reinicio.executar_reinicio("placa", executar=lambda *a: chamadas.append(a), rodar=rodar))
        self.assertEqual(len(chamadas), 1)

    def test_falha_ao_reabrir_o_programa_devolve_false(self):
        def executar(*a):
            raise OSError("sem permissão")

        self.assertFalse(reinicio.executar_reinicio("programa", executar=executar))


class TestRegistroEReinicioProgramado(unittest.TestCase):
    def test_reinicio_programado_nao_e_queda_e_aparece_na_telemetria(self):
        with tempfile.TemporaryDirectory() as pasta:
            relogio = Relogio(1_000_000.0)
            primeira = RegistroExecucao(Path(pasta) / "e.json", agora=relogio)
            relogio.t += 8 * 3600
            primeira.encerrar("reinicio_programado")
            relogio.t += 30
            atual = RegistroExecucao(Path(pasta) / "e.json", agora=relogio)
            self.assertEqual(atual.reinicios(8), (1, 0))  # 1 reinício, 0 quedas
            self.assertEqual(atual.reinicios_programados(8), 1)

            t = Telemetria()
            t.configurar(atual, "m.tflite", Resultados(), reiniciar_apos_h=8)
            dados = t.instantaneo()
            self.assertEqual((dados["reinicios_8h"], dados["quedas_8h"], dados["reinicios_programados_8h"]), (1, 0, 1))
            self.assertEqual((dados["reinicio_apos_h"], dados["reinicio_programado_em_s"]), (8, 8 * 3600 - 30 + 30))

    def test_queda_nao_conta_como_reinicio_programado(self):
        with tempfile.TemporaryDirectory() as pasta:
            relogio = Relogio(1_000_000.0)
            RegistroExecucao(Path(pasta) / "e.json", agora=relogio)  # caiu sem encerrar
            relogio.t += 60
            atual = RegistroExecucao(Path(pasta) / "e.json", agora=relogio)
            self.assertEqual((atual.reinicios(8), atual.reinicios_programados(8)), ((1, 1), 0))

    def test_telemetria_leva_resultados_e_validacao(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "v.json"
            arquivo.write_text(json.dumps({"classes": {"todas": {"map50": 0.9}}}), encoding="utf-8")
            res = Resultados(relogio=Relogio())
            res.amostrar_confianca("colete", 0.8)
            t = Telemetria()
            t.configurar(None, "m.tflite", res, 0, arquivo)
            dados = t.instantaneo()
            self.assertEqual(dados["conf_colete_pct"], 80.0)
            self.assertEqual(dados["validacao"]["classes"]["todas"]["map50"], 0.9)
            self.assertNotIn("reinicio_programado_em_s", dados)  # desligado: nada de contagem regressiva


if __name__ == "__main__":
    unittest.main()
