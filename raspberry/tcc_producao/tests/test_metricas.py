"""Testes das métricas de desempenho e estabilidade (rodam em qualquer PC).

    python -m unittest discover -s tests -v      (a partir de raspberry/tcc_producao)
"""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from metricas import (  # noqa: E402
    COLUNAS_CSV, Metricas, RegistroCsv, RegistroExecucao, Telemetria, descrever_limitacao, ler_carga, ler_memoria,
    ler_temperatura, linhas_janela, linhas_terminal,
)


class Relogio:
    """Relógio controlado pelo teste (segundos)."""

    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


def preencher(m, relogio, quadros, segundos, inf=70.0):
    for _ in range(quadros):
        m.quadro()
        m.registrar("redim", 0.2)
        m.registrar("pre", 4.0)
        m.registrar("inf", inf)
        m.registrar("pos", 1.0)
        m.registrar("regras", 0.3)
        m.registrar("total", 0.2 + 4.0 + inf + 1.0 + 0.3)
        m.registrar("borda_decisao", 80.0)
    relogio.t += segundos


class TestMetricas(unittest.TestCase):
    def test_estatistica_do_intervalo(self):
        r = Relogio()
        m = Metricas(r)
        preencher(m, r, quadros=50, segundos=10)
        resumo = m.fechar_intervalo(temperatura=55.0)
        self.assertAlmostEqual(resumo["fps"], 5.0)
        self.assertEqual(resumo["quadros"], 50)
        media, p95, pior, n = resumo["inf"]
        self.assertEqual((media, p95, pior, n), (70.0, 70.0, 70.0, 50))
        self.assertEqual(resumo["temp"], 55.0)

    def test_p95_e_pior_caso(self):
        r = Relogio()
        m = Metricas(r)
        for i in range(100):
            m.quadro()
            m.registrar("total", float(i + 1))  # 1..100 ms
        r.t += 10
        media, p95, pior, n = m.fechar_intervalo()["total"]
        self.assertEqual((media, p95, pior, n), (50.5, 96.0, 100.0, 100))

    def test_fps_minimo_ignora_o_primeiro_intervalo_de_aquecimento(self):
        r = Relogio()
        m = Metricas(r)
        preencher(m, r, 10, 10)  # 1 FPS no aquecimento: não vale como "mínimo"
        m.fechar_intervalo()
        self.assertIsNone(m.fps_minimo)
        preencher(m, r, 80, 10)  # 8 FPS
        m.fechar_intervalo()
        preencher(m, r, 120, 10)  # 12 FPS
        resumo = m.fechar_intervalo()
        self.assertAlmostEqual(resumo["fps"], 12.0)
        self.assertAlmostEqual(resumo["fps_minimo"], 8.0)  # a pior janela, não a média

    def test_intervalo_zera_mas_o_acumulado_continua(self):
        r = Relogio()
        m = Metricas(r)
        preencher(m, r, 10, 10)
        m.fechar_intervalo()
        self.assertIsNone(m.fechar_intervalo()["inf"])  # intervalo novo, sem amostras
        self.assertEqual(m.resumo_geral()["inf"][3], 10)  # mas o geral lembra dos 10

    def test_temperatura_maxima_guarda_o_pico(self):
        r = Relogio()
        m = Metricas(r)
        for temp in (50.0, 71.5, 60.0):
            r.t += 10
            resumo = m.fechar_intervalo(temp)
        self.assertEqual(resumo["temp_max"], 71.5)

    def test_sem_sensor_de_temperatura_nao_quebra(self):
        self.assertTrue(ler_temperatura() is None or isinstance(ler_temperatura(), float))


class TestRegistroExecucao(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.arquivo = Path(self._tmp.name) / "estado.json"
        self.relogio = Relogio(1_000_000.0)

    def abrir(self):
        return RegistroExecucao(self.arquivo, agora=self.relogio)

    def test_primeira_partida_nao_e_reinicio(self):
        r = self.abrir()
        self.assertEqual((r.numero, r.reinicios(8), r.anterior_caiu), (1, (0, 0), False))

    def test_encerramento_limpo_conta_reinicio_mas_nao_queda(self):
        a = self.abrir()
        self.relogio.t += 3600
        a.encerrar()
        self.relogio.t += 60
        b = self.abrir()
        self.assertEqual((b.numero, b.anterior_caiu, b.reinicios(8)), (2, False, (1, 0)))

    def test_processo_morto_sem_encerrar_conta_como_queda(self):
        a = self.abrir()
        self.relogio.t += 1800
        a.sinal()  # estava vivo até aqui; depois a energia caiu
        self.relogio.t += 600
        b = self.abrir()
        self.assertTrue(b.anterior_caiu)
        self.assertEqual(b.reinicios(8), (1, 1))

    def test_reinicios_antigos_fora_da_janela_de_8_horas_nao_contam(self):
        self.abrir().encerrar()  # 1ª partida
        self.relogio.t += 3600
        self.abrir().encerrar()  # reinício há 10 h (fora da janela quando olharmos)
        self.relogio.t += 10 * 3600
        agora = self.abrir()  # reinício de agora (dentro da janela)
        self.assertEqual(agora.numero, 3)
        self.assertEqual(agora.reinicios(8), (1, 0))  # só o de agora; o de 10 h atrás não conta
        self.assertEqual(agora.reinicios(24), (2, 0))  # numa janela maior, os dois

    def test_tempo_ligado(self):
        r = self.abrir()
        self.relogio.t += 7200
        self.assertEqual(r.ligado_ha(), 7200)

    def test_arquivo_corrompido_vira_historico_vazio(self):
        self.arquivo.write_text("{quebrado", encoding="utf-8")
        r = self.abrir()
        self.assertEqual((r.numero, r.anterior_caiu), (1, False))

    def test_guarda_no_maximo_as_ultimas_50_partidas(self):
        for _ in range(60):
            self.abrir().encerrar()
            self.relogio.t += 10
        self.assertLessEqual(self.abrir().numero, RegistroExecucao.MAXIMO)


class TestTelemetria(unittest.TestCase):
    def setUp(self):
        self.relogio = Relogio(1000.0)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.registro = RegistroExecucao(Path(self._tmp.name) / "e.json", agora=self.relogio)
        self.t = Telemetria()
        self.t.configurar(self.registro, "modelo.tflite")

    def intervalo(self, alerta):
        m = Metricas(self.relogio)
        preencher(m, self.relogio, 50, 10)
        if alerta:
            m.registrar("borda_sirene", 530.0)
            m.registrar("borda_api", 2400.0)
        return m.fechar_intervalo(50.0)

    def test_sem_resumo_ainda_leva_o_que_ja_se_sabe(self):
        dados = self.t.instantaneo()
        self.assertEqual((dados["modelo"], dados["execucao"], dados["reinicios_8h"]), ("modelo.tflite", 1, 0))
        self.assertNotIn("fps", dados)
        self.assertNotIn(None, dados.values())  # o que não existe (ex.: sensor no PC) simplesmente sai

    def test_desempenho_vem_do_ultimo_resumo(self):
        self.t.atualizar(self.intervalo(alerta=False))
        dados = self.t.instantaneo()
        self.assertEqual((dados["fps"], dados["inferencia_ms"], dados["pre_ms"]), (5.0, 70.0, 4.2))
        self.assertEqual(dados["total_ms"], 75.5)

    def test_sirene_e_api_guardam_o_ultimo_valor_conhecido(self):
        self.t.atualizar(self.intervalo(alerta=True))
        self.t.atualizar(self.intervalo(alerta=False))  # intervalo sem alerta não apaga o que já se mediu
        dados = self.t.instantaneo()
        self.assertEqual((dados["borda_sirene_ms"], dados["borda_api_ms"]), (530.0, 2400.0))

    def test_leitores_de_memoria_e_carga_nao_quebram_fora_do_linux(self):
        for valor in (ler_memoria(), ler_carga()):
            self.assertTrue(valor is None or 0 <= valor <= 1000)


class TestSaida(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        relogio = Relogio(5000.0)
        self.registro = RegistroExecucao(Path(self._tmp.name) / "e.json", agora=relogio)
        m = Metricas(relogio)
        preencher(m, relogio, 50, 10)
        m.registrar("borda_sirene", 95.0)
        m.registrar("borda_api", 900.0)
        self.resumo = m.fechar_intervalo(58.0)

    def test_linhas_do_terminal_trazem_todas_as_metricas_da_tabela(self):
        desempenho, sistema = linhas_terminal(self.resumo, self.registro, "0x0")
        for trecho in ("pré 4.2 ms", "inferência 70.0 ms", "pós 1.0 ms", "total 76 ms", "5.0 FPS", "borda→decisão 80 ms"):
            self.assertIn(trecho, desempenho)
        for trecho in ("CPU 58 °C", "limitação 0x0", "execução nº 1", "reinícios em 8 h: 0", "sirene 95 ms", "API 900 ms"):
            self.assertIn(trecho, sistema)

    def test_sem_limitacao_o_terminal_nao_acrescenta_texto(self):
        _, sistema = linhas_terminal(self.resumo, self.registro, "0x0")
        self.assertNotIn("(", sistema.split("limitação")[1].split("|")[0])  # só o código, sem tradução
        self.assertEqual(descrever_limitacao("0x0"), "")

    def test_subtensao_em_curso_e_traduzida_com_atencao(self):
        # 0x50005 foi o que a Pi reportou quando ficou 2,4x mais lenta: subtensão agora + CPU freada agora + histórico.
        texto = descrever_limitacao("0x50005")
        self.assertTrue(texto.startswith("ATENÇÃO: subtensão agora, CPU freada agora"))
        self.assertIn("houve subtensão desde que a Pi ligou", texto)
        self.assertIn("a CPU já foi freada", texto)
        _, sistema = linhas_terminal(self.resumo, self.registro, "0x50005")
        self.assertIn("limitação 0x50005 (ATENÇÃO: subtensão agora", sistema)

    def test_so_historico_nao_grita_atencao(self):
        # 0x50000: já aconteceu desde que a Pi ligou, mas nada em curso. Reiniciar a Pi zera o histórico.
        texto = descrever_limitacao("0x50000")
        self.assertEqual(texto, "houve subtensão desde que a Pi ligou, a CPU já foi freada")
        self.assertNotIn("ATENÇÃO", texto)

    def test_limitacao_ausente_ou_invalida_nao_quebra(self):
        for codigo in (None, "", "n/d", "xyz"):
            self.assertEqual(descrever_limitacao(codigo), "")

    def test_sem_dados_mostra_traco_em_vez_de_quebrar(self):
        vazio = Metricas(Relogio()).fechar_intervalo()
        desempenho, sistema = linhas_terminal(vazio, self.registro, None)
        self.assertIn("pré -", desempenho)
        self.assertIn("CPU -", sistema)
        self.assertIn("n/d", sistema)

    def test_faixa_da_janela_tem_duas_linhas_curtas(self):
        linhas = linhas_janela(self.resumo)
        self.assertEqual(len(linhas), 2)
        self.assertTrue(all(len(linha) < 70 for linha in linhas))

    def test_csv_tem_cabecalho_uma_vez_e_uma_linha_por_intervalo(self):
        csv_ = RegistroCsv(Path(self._tmp.name) / "m.csv")
        csv_.gravar(self.resumo, self.registro, "0x0", "2026-10-27T21:00:00+00:00")
        csv_.gravar(self.resumo, self.registro, "0x0", "2026-10-27T21:00:10+00:00")
        with (Path(self._tmp.name) / "m.csv").open(encoding="utf-8", newline="") as f:
            linhas = list(csv.reader(f, delimiter=";"))
        self.assertEqual(linhas[0], COLUNAS_CSV)
        self.assertEqual(len(linhas), 3)
        self.assertEqual(len(linhas[1]), len(COLUNAS_CSV))
        linha = dict(zip(COLUNAS_CSV, linhas[1]))
        self.assertEqual((linha["fps"], linha["inferencia_ms"], linha["temp_c"], linha["execucao"]), ("5.0", "70.00", "58.0", "1"))


if __name__ == "__main__":
    unittest.main()
