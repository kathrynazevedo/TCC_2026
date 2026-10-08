"""Testes da lógica da borda (rodam em qualquer PC, sem câmera, modelo ou GPIO).

    python -m unittest discover -s tests -v      (a partir de raspberry/tcc_producao)
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cliente_api  # noqa: E402
import config  # noqa: E402
import deteccao  # noqa: E402


class TestDeteccao(unittest.TestCase):
    def test_classificar_aceita_variacoes_de_nome(self):
        for nome in ("Sem_Capacete", "sem-capacete", "no-helmet", "No Helmet"):
            self.assertEqual(deteccao.classificar(nome), "no-helmet", nome)
        for nome in ("sem_colete", "Sem-Colete", "no-vest"):
            self.assertEqual(deteccao.classificar(nome), "no-vest", nome)

    def test_classes_conformes_nao_sao_infracao(self):
        for nome in ("Capacete", "Colete", "Pessoa", ""):
            self.assertIsNone(deteccao.classificar(nome), nome)

    def test_resumir_ignora_baixa_confianca_e_fica_com_a_maior(self):
        deteccoes = [("sem_capacete", 0.72), ("sem_capacete", 0.91), ("sem_colete", 0.40), ("Capacete", 0.99)]
        self.assertEqual(deteccao.resumir_infracoes(deteccoes, 0.70), {"no-helmet": 0.91})

    def test_debounce_bloqueia_repeticao_dentro_da_janela(self):
        d = deteccao.Debounce(10)
        self.assertTrue(d.permitir("no-helmet", 100.0))
        self.assertFalse(d.permitir("no-helmet", 105.0))
        self.assertTrue(d.permitir("no-vest", 105.0))  # tipos independentes
        self.assertTrue(d.permitir("no-helmet", 110.0))

    def test_debounce_libera_o_primeiro_alerta_mesmo_com_relogio_perto_de_zero(self):
        self.assertTrue(deteccao.Debounce(10).permitir("no-vest", 0.5))


class TestFilaOffline(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(config, "PASTA_PENDENTES", Path(self._tmp.name) / "pendentes")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._tmp.cleanup)

    def _pendentes(self):
        return sorted(config.PASTA_PENDENTES.glob("*.jpg")) if config.PASTA_PENDENTES.exists() else []

    def test_falha_de_rede_guarda_o_alerta_em_disco(self):
        with mock.patch.object(cliente_api, "enviar_infracao", return_value=cliente_api.RETENTAR):
            cliente_api.processar_alerta(b"jpeg", "no-helmet", 0.9)
        self.assertEqual(len(self._pendentes()), 1)
        meta = json.loads(self._pendentes()[0].with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual(meta["tipo"], "no-helmet")

    def test_envio_ok_nao_guarda_nada(self):
        with mock.patch.object(cliente_api, "enviar_infracao", return_value=cliente_api.OK):
            cliente_api.processar_alerta(b"jpeg", "no-vest", 0.8)
        self.assertEqual(self._pendentes(), [])

    def test_recusa_definitiva_da_api_nao_vira_pendencia(self):
        with mock.patch.object(cliente_api, "enviar_infracao", return_value=cliente_api.DESCARTAR):
            cliente_api.processar_alerta(b"jpeg", "no-vest", 0.8)
        self.assertEqual(self._pendentes(), [])

    def test_sincronizacao_envia_e_limpa_as_pendencias(self):
        cliente_api.salvar_pendente(b"a", "no-helmet", 0.9, "2026-01-01T00:00:00+00:00")
        cliente_api.salvar_pendente(b"b", "no-vest", 0.8, "2026-01-01T00:00:05+00:00")
        with mock.patch.object(cliente_api, "enviar_infracao", return_value=cliente_api.OK) as enviar:
            enviados, restantes = cliente_api.sincronizar_pendentes()
        self.assertEqual((enviados, restantes), (2, 0))
        self.assertEqual(enviar.call_count, 2)
        self.assertEqual(self._pendentes(), [])
        self.assertEqual(list(config.PASTA_PENDENTES.glob("*.json")), [])

    def test_sincronizacao_para_no_primeiro_erro_de_rede_e_mantem_o_resto(self):
        cliente_api.salvar_pendente(b"a", "no-helmet", 0.9, "t1")
        cliente_api.salvar_pendente(b"b", "no-vest", 0.8, "t2")
        with mock.patch.object(cliente_api, "enviar_infracao", return_value=cliente_api.RETENTAR) as enviar:
            enviados, restantes = cliente_api.sincronizar_pendentes()
        self.assertEqual((enviados, restantes), (0, 2))
        self.assertEqual(enviar.call_count, 1)
        self.assertEqual(len(self._pendentes()), 2)

    def test_limite_de_pendencias_descarta_as_mais_antigas(self):
        with mock.patch.object(config, "MAX_PENDENTES", 3):
            for i in range(5):
                cliente_api.salvar_pendente(bytes([i]), "no-helmet", 0.9, f"t{i}")
        fotos = self._pendentes()
        self.assertEqual(len(fotos), 3)
        self.assertEqual([f.read_bytes() for f in fotos], [bytes([2]), bytes([3]), bytes([4])])

    def test_pendencia_corrompida_e_removida_sem_travar_a_fila(self):
        config.PASTA_PENDENTES.mkdir(parents=True)
        (config.PASTA_PENDENTES / "x.jpg").write_bytes(b"x")  # sem .json
        enviados, restantes = cliente_api.sincronizar_pendentes()
        self.assertEqual((enviados, restantes), (0, 0))
        self.assertEqual(self._pendentes(), [])


class TestEnvioHttp(unittest.TestCase):
    def _resposta(self, status):
        return mock.Mock(status_code=status, text="x")

    def test_classificacao_das_respostas_da_api(self):
        casos = {201: cliente_api.OK, 400: cliente_api.DESCARTAR, 404: cliente_api.DESCARTAR,
                 401: cliente_api.RETENTAR, 500: cliente_api.RETENTAR, 503: cliente_api.RETENTAR}
        for status, esperado in casos.items():
            with mock.patch.object(cliente_api.requests, "post", return_value=self._resposta(status)):
                self.assertEqual(cliente_api.enviar_infracao(b"j", "no-vest", 0.8, "t"), esperado, status)

    def test_sem_rede_pede_nova_tentativa(self):
        erro = cliente_api.requests.ConnectionError("fora do ar")
        with mock.patch.object(cliente_api.requests, "post", side_effect=erro):
            self.assertEqual(cliente_api.enviar_infracao(b"j", "no-vest", 0.8, "t"), cliente_api.RETENTAR)
            self.assertFalse(cliente_api.enviar_heartbeat())

    def test_payload_e_chave_de_api(self):
        with mock.patch.object(config, "EDGE_API_KEY", "segredo"), \
             mock.patch.object(cliente_api.requests, "post", return_value=self._resposta(201)) as post:
            cliente_api.enviar_infracao(b"j", "no-helmet", 0.91234, "2026-01-01T00:00:00+00:00")
        kwargs = post.call_args.kwargs
        self.assertEqual(kwargs["headers"], {"x-api-key": "segredo"})
        self.assertEqual(kwargs["data"]["tipo_epi_ausente"], "no-helmet")
        self.assertEqual(kwargs["data"]["confidence"], "0.9123")
        self.assertIn("image", kwargs["files"])  # nome do campo que o multer espera

    def test_timestamp_em_utc_com_fuso(self):
        self.assertTrue(cliente_api.agora_utc().endswith("+00:00"))


if __name__ == "__main__":
    unittest.main()
