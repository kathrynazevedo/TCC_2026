"""Testes do programa principal e das ferramentas (sem câmera, modelo, rede nem GPIO).

    python -m unittest discover -s tests -v      (a partir de raspberry/tcc_producao)
"""
import contextlib
import importlib
import importlib.util
import io
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cliente_api  # noqa: E402
import config  # noqa: E402
import main  # noqa: E402
import teste_conexao  # noqa: E402
import testar_modelo  # noqa: E402
from metricas import Metricas, RegistroCsv, RegistroExecucao  # noqa: E402


def ultralytics_falso(classes=None, erro=None):
    """Módulo `ultralytics` de mentira: o YOLO devolve as classes pedidas ou falha ao abrir o modelo."""
    modulo = types.ModuleType("ultralytics")

    class YOLO:
        names = classes or {}

        def __init__(self, *args, **kwargs):
            if erro:
                raise erro

    modulo.YOLO = YOLO
    return mock.patch.dict(sys.modules, {"ultralytics": modulo})


class TestCodigoDeSaida(unittest.TestCase):
    """O serviço systemd não reinicia em loop quando o problema é de configuração (código 2)."""

    def rodar(self, **falso):
        with ultralytics_falso(**falso), contextlib.redirect_stdout(io.StringIO()) as saida:
            return main.main(), saida.getvalue()

    def test_modelo_que_nao_abre_sai_com_2(self):
        codigo, texto = self.rodar(erro=OSError("arquivo sumiu"))
        self.assertEqual(codigo, main.SAIDA_CONFIG_INVALIDA)
        self.assertEqual(main.SAIDA_CONFIG_INVALIDA, 2)
        self.assertIn("Não foi possível carregar o modelo", texto)

    def test_modelo_sem_as_tres_classes_sai_com_2(self):
        codigo, texto = self.rodar(classes={0: "capacete", 1: "colete"})
        self.assertEqual(codigo, 2)
        self.assertIn("pessoa", texto)


class TestCameraComPrazo(unittest.TestCase):
    def test_camera_de_rede_abre_com_prazo_de_abertura_e_de_leitura(self):
        with mock.patch.object(main.cv2, "VideoCapture") as abrir:
            main.abrir_camera("rtsp://usuario:senha@192.168.1.208:554/cam")
        argumentos = abrir.call_args.args
        self.assertEqual(argumentos[1], main.cv2.CAP_FFMPEG)
        prazos = argumentos[2]
        self.assertIn(main.cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, prazos)
        self.assertIn(main.cv2.CAP_PROP_READ_TIMEOUT_MSEC, prazos)

    def test_webcam_e_arquivo_abrem_do_jeito_simples(self):
        for fonte in (0, "cena.mp4"):
            with mock.patch.object(main.cv2, "VideoCapture") as abrir:
                main.abrir_camera(fonte)
            self.assertEqual(abrir.call_args.args, (fonte,))

    def test_opencv_antigo_sem_os_parametros_cai_para_a_abertura_simples(self):
        chamadas = []

        def abrir(*args):
            chamadas.append(args)
            if len(args) > 1:
                raise TypeError("overload não existe neste OpenCV")
            return "camera"

        with mock.patch.object(main.cv2, "VideoCapture", side_effect=abrir):
            self.assertEqual(main.abrir_camera("rtsp://host/cam"), "camera")
        self.assertEqual([len(c) for c in chamadas], [3, 1])


class TestSaida(unittest.TestCase):
    def test_caractere_fora_da_codificacao_nao_derruba_o_programa(self):
        # console do Windows em cp1252 + seta de "borda→decisão": imprimia e dava UnicodeEncodeError
        pipe = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")
        with mock.patch.object(sys, "stdout", pipe), mock.patch.object(sys, "stderr", pipe):
            main.configurar_saida()
            print("borda→decisão")
            pipe.flush()


class TestFerramentas(unittest.TestCase):
    def conferir_classes(self, classes):
        with ultralytics_falso(classes=classes), mock.patch.object(sys, "argv", ["testar_modelo.py", "--so-classes"]), \
             contextlib.redirect_stdout(io.StringIO()) as saida:
            return testar_modelo.main(), saida.getvalue()

    def test_modelo_compativel(self):
        codigo, texto = self.conferir_classes({0: "capacete", 1: "colete", 2: "pessoa"})
        self.assertEqual(codigo, 0)
        self.assertIn("COMPATÍVEL", texto)

    def test_modelo_de_outro_projeto_nao_serve_e_diz_o_que_falta(self):
        codigo, texto = self.conferir_classes({0: "Capacete", 1: "Sem_Capacete"})
        self.assertEqual(codigo, 1)
        self.assertIn("NÃO SERVE", texto)

    def test_modelo_so_de_pessoas_tambem_nao_serve_mais(self):
        # o antigo modo "só pessoas" (yolov8n genérico) saiu: sem capacete/colete o sistema não tem o que julgar
        codigo, _ = self.conferir_classes({0: "person"})
        self.assertEqual(codigo, 1)

    def test_ocorrencia_de_teste_cobre_a_mesma_pessoa_sem_capacete_e_sem_colete(self):
        enviadas = []

        def enviar(jpeg, ocorrencia):
            enviadas.append(ocorrencia)
            return cliente_api.OK

        with mock.patch.object(cliente_api, "enviar_ocorrencia", side_effect=enviar), \
             mock.patch.object(teste_conexao.requests, "get", side_effect=teste_conexao.requests.RequestException("sem rede")), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(teste_conexao.enviar_infracao_de_teste())
        (pessoa,) = enviadas[0]["pessoas"]
        self.assertEqual((pessoa["capacete"]["estado"], pessoa["colete"]["estado"]), ("ausente", "ausente"))
        self.assertTrue(pessoa["capacete"]["novo"] and pessoa["colete"]["novo"])
        self.assertGreaterEqual(pessoa["capacete"]["confianca"], 0.5)  # o banco recusa score < 0,50


class TestRotacaoDoCsv(unittest.TestCase):
    def resumo(self):
        metricas = Metricas(lambda: 100.0)
        metricas.quadro()
        for nome in ("redim", "pre", "inf", "pos", "regras", "total", "borda_decisao"):
            metricas.registrar(nome, 10.0)
        return metricas.fechar_intervalo(50.0)

    def test_arquivo_cheio_vira_o_backup_e_um_novo_comeca_com_cabecalho(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "metricas.csv"
            registro = RegistroExecucao(Path(pasta) / "estado.json")
            csv_ = RegistroCsv(caminho, limite_bytes=600)
            for i in range(12):
                csv_.gravar(self.resumo(), registro, "0x0", f"2026-10-31T00:00:{i:02d}+00:00")
            backup = Path(pasta) / "metricas.csv.1"
            self.assertTrue(backup.exists())
            self.assertTrue(caminho.read_text(encoding="utf-8").startswith("data_hora_utc;"))  # o novo tem cabeçalho
            linhas = caminho.read_text(encoding="utf-8").count("\n") + backup.read_text(encoding="utf-8").count("\n")
            self.assertLessEqual(linhas, 12 + 2 * 2)  # nada se perdeu além do que o backup anterior substituiu
            self.assertLess(caminho.stat().st_size, 600 + 400)  # e o arquivo atual não passa do limite por mais de uma linha

    def test_abaixo_do_limite_nao_roda(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "metricas.csv"
            registro = RegistroExecucao(Path(pasta) / "estado.json")
            RegistroCsv(caminho).gravar(self.resumo(), registro, "0x0", "2026-10-31T00:00:00+00:00")
            self.assertFalse((Path(pasta) / "metricas.csv.1").exists())


class TestLeituraDoEnv(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("dotenv"), "python-dotenv não está instalado neste Python")
    def test_env_gravado_no_bloco_de_notas_com_bom_e_lido_sem_aviso(self):
        with tempfile.TemporaryDirectory() as pasta, mock.patch.dict(os.environ):
            os.environ.pop("TESTE_BOM_X", None)
            arquivo = Path(pasta) / ".env"
            conteudo = b"\xef\xbb\xbf# Copie para .env\r\nTESTE_BOM_X=ok\r\n"  # BOM + final de linha do Windows
            arquivo.write_bytes(conteudo)
            if hasattr(self, "assertNoLogs"):  # Python 3.10+: o python-dotenv avisa por log quando não entende uma linha
                with self.assertNoLogs("dotenv.main", level="WARNING"), self.assertNoLogs("dotenv.parser", level="WARNING"):
                    config.carregar_env(arquivo)
            else:
                config.carregar_env(arquivo)
            self.assertEqual(os.environ.get("TESTE_BOM_X"), "ok")

    def test_sem_o_dotenv_instalado_so_valem_as_variaveis_do_sistema(self):
        with mock.patch.dict(sys.modules, {"dotenv": None}):  # None força ImportError no import
            self.assertFalse(config.carregar_env(Path("nao-importa.env")))


class TestConfigFinal(unittest.TestCase):
    def test_padroes_de_producao_sem_depender_do_env_de_quem_roda(self):
        # Recarrega o config sem ler o .env nem as variáveis de ambiente do projeto: o que vale são os PADRÕES do código.
        prefixos = ("CONFIANCA_", "REINICI", "PINO_", "SIRENE_", "DURACAO_", "MODELO_")
        ambiente = {k: v for k, v in os.environ.items() if not k.startswith(prefixos)}
        dotenv_falso = types.ModuleType("dotenv")
        dotenv_falso.load_dotenv = lambda *args, **kwargs: None
        try:
            with mock.patch.dict(os.environ, ambiente, clear=True), mock.patch.dict(sys.modules, {"dotenv": dotenv_falso}):
                importlib.reload(config)
                self.assertEqual((config.CONFIANCA_PESSOA, config.CONFIANCA_CAPACETE, config.CONFIANCA_COLETE), (0.65, 0.50, 0.65))
                self.assertEqual(config.REINICIAR_APOS_HORAS, 8.0)
                self.assertEqual(config.REINICIO_MODO, "programa")
                self.assertEqual((config.PINO_SIRENE, config.SIRENE_ATIVA_EM_BAIXO), (11, True))
                self.assertEqual(config.CONFIANCA_MODELO, 0.50)  # o modelo devolve tudo a partir do menor limiar
                self.assertEqual(config.INTERVALO_METRICAS, 10.0)
                self.assertEqual(Path(config.MODELO_PATH).name, "modelo_pessoa_epi.tflite")
        finally:
            importlib.reload(config)  # devolve o config ao que o restante dos testes espera

    def test_intervalo_de_metricas_invalido_volta_ao_padrao(self):
        # 0 (que antes "desligava") ou negativo não pode parar os resumos: o painel depende deles
        dotenv_falso = types.ModuleType("dotenv")
        dotenv_falso.load_dotenv = lambda *args, **kwargs: None
        try:
            for valor in ("0", "-5", "abc"):
                with mock.patch.dict(os.environ, {"INTERVALO_METRICAS": valor}),                      mock.patch.dict(sys.modules, {"dotenv": dotenv_falso}):
                    importlib.reload(config)
                    self.assertEqual(config.INTERVALO_METRICAS, 10.0, valor)
            with mock.patch.dict(os.environ, {"INTERVALO_METRICAS": "2.5", "REINICIO_MODO": "talvez"}),                  mock.patch.dict(sys.modules, {"dotenv": dotenv_falso}):
                importlib.reload(config)
                self.assertEqual(config.INTERVALO_METRICAS, 2.5)
                self.assertEqual(config.REINICIO_MODO, "programa")  # modo desconhecido volta ao seguro
        finally:
            importlib.reload(config)


if __name__ == "__main__":
    unittest.main()
