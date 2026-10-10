"""Testes da lógica da borda (rodam em qualquer PC, sem câmera, modelo ou GPIO).

    python -m unittest discover -s tests -v      (a partir de raspberry/tcc_producao)
"""
import json
import random
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cliente_api  # noqa: E402
import config  # noqa: E402
import deteccao  # noqa: E402
from deteccao import AlertasPorPessoa, montar_pessoas, ocorrencia_da_cena  # noqa: E402
from rastreador import Rastreador  # noqa: E402

CAP, COL = "no-helmet", "no-vest"

# Caixas medidas na foto de um teste real (coordenadas do frame 640x480): o homem de capacete e sem colete, a mulher
# sem capacete; o modelo desenhou um colete estreito sobre o homem e outro, largo, cobrindo os dois.
HOMEM_CAPACETE = ("Capacete", 0.91, (185, 39, 400, 196))
MULHER_SEM_CAPACETE = ("Sem_Capacete", 0.87, (469, 174, 640, 263))
COLETE_ESTREITO = ("Sem_Colete", 0.83, (140, 312, 391, 479))
COLETE_LARGO = ("Sem_Colete", 0.78, (154, 312, 640, 479))
DUAS_PESSOAS = [HOMEM_CAPACETE, MULHER_SEM_CAPACETE, COLETE_ESTREITO, COLETE_LARGO]

# Uma pessoa sozinha, parada, com o modelo desenhando duas caixas aninhadas na mesma cabeça.
CABECA_LARGA = ("Sem_Capacete", 0.88, (15, 0, 460, 140))
CABECA_ANINHADA = ("Sem_Capacete", 0.74, (185, 0, 465, 130))
COLETE_1 = ("Sem_Colete", 0.85, (120, 290, 430, 400))


def novo(realerta=0.0, ausente=10.0, presente=3.0):
    return AlertasPorPessoa(
        intervalo_realerta=realerta, tempo_ausente=ausente, dist_maxima=150, tempo_presente=presente,
        confianca_minima=0.70,
    )


class TestClasses(unittest.TestCase):
    def test_classificar_aceita_variacoes_de_nome(self):
        for nome in ("Sem_Capacete", "sem-capacete", "no-helmet", "No Helmet"):
            self.assertEqual(deteccao.classificar(nome), "no-helmet", nome)
        for nome in ("sem_colete", "Sem-Colete", "no-vest"):
            self.assertEqual(deteccao.classificar(nome), "no-vest", nome)

    def test_classes_conformes_nao_sao_infracao(self):
        for nome in ("Capacete", "Colete_Refletivo", "Pessoa", ""):
            self.assertIsNone(deteccao.classificar(nome), nome)

    def test_interpretar_diz_em_que_parte_do_corpo_fica_o_epi(self):
        self.assertEqual(deteccao.interpretar("Capacete"), (deteccao.CABECA, None))
        self.assertEqual(deteccao.interpretar("Sem_Capacete"), (deteccao.CABECA, CAP))
        self.assertEqual(deteccao.interpretar("Colete_Refletivo"), (deteccao.TRONCO, None))
        self.assertEqual(deteccao.interpretar("Sem_Colete"), (deteccao.TRONCO, COL))
        self.assertIsNone(deteccao.interpretar("Pessoa"))


class TestMontagemDePessoas(unittest.TestCase):
    def test_cada_epi_vai_para_a_pessoa_certa_mesmo_com_colete_largo_cobrindo_os_dois(self):
        pessoas = montar_pessoas(DUAS_PESSOAS, 0.70)
        por_cabeca = {p.cabeca.nome: p for p in pessoas}
        homem, mulher = por_cabeca["Capacete"], por_cabeca["Sem_Capacete"]
        self.assertEqual(len(pessoas), 2)
        self.assertEqual(homem.tronco.caixa, COLETE_ESTREITO[2])
        self.assertEqual(mulher.tronco.caixa, COLETE_LARGO[2])
        self.assertEqual(set(homem.infracoes()), {COL})
        self.assertEqual(set(mulher.infracoes()), {CAP, COL})

    def test_atribuicao_independe_da_ordem_das_deteccoes(self):
        rnd = random.Random(1)
        for _ in range(30):
            deteccoes = list(DUAS_PESSOAS)
            rnd.shuffle(deteccoes)
            por_cabeca = {p.cabeca.nome: p for p in montar_pessoas(deteccoes, 0.70)}
            self.assertEqual(por_cabeca["Capacete"].tronco.caixa, COLETE_ESTREITO[2])
            self.assertEqual(por_cabeca["Sem_Capacete"].tronco.caixa, COLETE_LARGO[2])

    def test_caixa_aninhada_na_mesma_cabeca_nao_vira_outra_pessoa(self):
        pessoas = montar_pessoas([CABECA_LARGA, CABECA_ANINHADA, COLETE_1], 0.70)
        self.assertEqual(len(pessoas), 1)
        self.assertEqual(pessoas[0].cabeca.confianca, 0.88)  # fica a de maior confiança

    def test_segunda_caixa_do_mesmo_colete_nao_e_entregue_ao_vizinho(self):
        duplicata = ("Sem_Colete", 0.70, (180, 330, 370, 479))  # dentro do colete estreito do homem
        pessoas = montar_pessoas([HOMEM_CAPACETE, MULHER_SEM_CAPACETE, COLETE_ESTREITO, duplicata], 0.70)
        por_cabeca = {p.cabeca.nome: p for p in pessoas}
        self.assertEqual(len(pessoas), 2)
        self.assertIsNone(por_cabeca["Sem_Capacete"].tronco)  # colete dela não detectado: não é acusada

    def test_cabeca_e_tronco_levemente_desalinhados_continuam_sendo_a_mesma_pessoa(self):
        tronco = ("Sem_Colete", 0.77, (300, 300, 460, 479))
        cabeca = ("Sem_Capacete", 0.79, (440, 350, 560, 450))  # centro fora da faixa do tronco e abaixo do centro
        pessoas = montar_pessoas([cabeca, tronco], 0.70)
        self.assertEqual(len(pessoas), 1)
        self.assertIsNotNone(pessoas[0].cabeca)
        self.assertIsNotNone(pessoas[0].tronco)

    def test_cabeca_e_tronco_afastados_nao_sao_fundidos(self):
        cabeca = ("Sem_Capacete", 0.9, (40, 40, 140, 130))
        tronco = ("Sem_Colete", 0.85, (400, 150, 560, 479))
        self.assertEqual(len(montar_pessoas([cabeca, tronco], 0.70)), 2)

    def test_tronco_sem_cabeca_vira_pessoa_so_com_tronco(self):
        pessoas = montar_pessoas([("Sem_Colete", 0.85, (200, 250, 420, 470))], 0.70)
        self.assertEqual(len(pessoas), 1)
        self.assertIsNone(pessoas[0].cabeca)

    def test_baixa_confianca_e_classes_desconhecidas_sao_ignoradas(self):
        deteccoes = [("Sem_Capacete", 0.5, (300, 100, 400, 200)), ("Pessoa", 0.99, (10, 10, 100, 100))]
        self.assertEqual(montar_pessoas(deteccoes, 0.70), [])


class TestAlertasPorPessoa(unittest.TestCase):
    def test_pessoa_parada_gera_um_alerta_por_tipo_e_nao_repete(self):
        rnd = random.Random(7)
        for fps in (2, 5, 15):
            a = novo()
            alertas = []
            for f in range(60 * fps):
                deteccoes = [CABECA_LARGA, COLETE_1]
                if rnd.random() < 0.4:
                    deteccoes.append(CABECA_ANINHADA)  # a caixa duplicada pisca
                alertas += a.filtrar(deteccoes, f / fps).alertas
            self.assertEqual(sorted(t for t, _, _ in alertas), [CAP, COL], f"{fps} FPS")

    def test_realerta_configuravel(self):
        a = novo(realerta=10.0)
        instantes = [t for t in (f / 5 for f in range(25 * 5)) if a.filtrar([CABECA_LARGA], t).alertas]
        self.assertEqual(instantes, [0.0, 10.0, 20.0])

    def test_dois_trabalhadores_no_mesmo_quadro_geram_dois_alertas(self):
        cena = novo().filtrar(DUAS_PESSOAS, 0.0)
        self.assertEqual(sorted((t, n) for t, _, n in cena.alertas if t == COL), [(COL, 1), (COL, 2)])
        self.assertEqual(len(cena.situacao), 2)

    def test_some_poucos_segundos_e_volta_sem_alerta_novo_mas_depois_de_muito_tempo_alerta(self):
        a = novo()
        a.filtrar([CABECA_LARGA], 0.0)
        self.assertEqual(a.filtrar([CABECA_LARGA], 5.0).alertas, [])
        a.filtrar([], 6.0)
        self.assertEqual(len(a.filtrar([CABECA_LARGA], 18.5).alertas), 1)

    def test_frame_vazio_nao_gera_alerta_fantasma(self):
        a = novo(realerta=10.0)
        a.filtrar([CABECA_LARGA], 0.0)
        self.assertEqual(a.filtrar([], 10.5).alertas, [])

    def test_tira_poe_e_tira_o_capacete_dentro_da_janela_nao_repete(self):
        sem = [("Sem_Capacete", 0.9, (250, 100, 350, 180))]
        com = [("Capacete", 0.9, (250, 100, 350, 180))]
        a = novo()
        self.assertEqual(len(a.filtrar(sem, 0.0).alertas), 1)
        a.filtrar(com, 2.0)
        self.assertEqual(a.filtrar(sem, 5.0).alertas, [])
        for t in range(6, 18):
            a.filtrar(com, float(t))
        self.assertEqual(len(a.filtrar(sem, 18.0).alertas), 1)

    def test_pessoa_de_epi_correto_conta_mas_nao_alerta(self):
        conforme = [("Capacete", 0.9, (80, 40, 180, 120)), ("Colete_Refletivo", 0.9, (60, 130, 200, 300))]
        cena = novo().filtrar(conforme, 0.0)
        self.assertEqual(cena.alertas, [])
        self.assertEqual(cena.situacao, ((1, ()),))

    def test_numeracao_se_recompacta_quando_alguem_sai(self):
        p1 = [("Sem_Capacete", 0.9, (80, 60, 180, 160))]
        p2 = [("Sem_Capacete", 0.8, (420, 200, 520, 300))]
        p3 = [("Sem_Capacete", 0.7, (250, 330, 350, 430))]
        a = novo()
        a.filtrar(p1, 0.0)
        cena = a.filtrar(p1 + p2, 1.0)
        self.assertEqual([(t, n) for t, _, n in cena.alertas], [(CAP, 2)])
        self.assertEqual(len(a.filtrar(p2, 3.5).situacao), 2)  # a 1 saiu há 2,5 s: ainda conta
        cena = a.filtrar(p2, 4.2)  # saiu há 3,2 s: a 2 vira 1, e renumerar não gera alerta
        self.assertEqual(cena.situacao, ((1, (CAP,)),))
        self.assertEqual(cena.alertas, [])
        cena = a.filtrar(p2 + p3, 5.0)  # quem chega depois ocupa o número seguinte
        self.assertEqual([(t, n) for t, _, n in cena.alertas], [(CAP, 2)])

    def test_pessoa_partida_em_cabeca_e_tronco_nao_vira_duas(self):
        # O caso do log de campo: o tronco aparece sozinho e a cabeça entra depois, desalinhada.
        a_cabeca = ("Sem_Capacete", 0.88, (60, 40, 160, 130))
        a_tronco = ("Sem_Colete", 0.80, (40, 140, 180, 300))
        b_tronco = ("Sem_Colete", 0.77, (300, 300, 460, 479))
        b_cabeca = ("Sem_Capacete", 0.79, (480, 350, 600, 450))
        a = novo()
        maximo = 0
        for f in range(10):
            maximo = max(maximo, len(a.filtrar([a_cabeca, a_tronco, b_tronco], f / 5).situacao))
        for f in range(10, 40):
            cena = a.filtrar([a_cabeca, a_tronco, b_tronco, b_cabeca], f / 5)
            maximo = max(maximo, len(cena.situacao))
        self.assertEqual(maximo, 2)

    def test_memoria_e_limpa_depois_que_todos_saem(self):
        a = novo(realerta=10.0)
        a.filtrar(DUAS_PESSOAS, 0.0)
        for f in range(1, 80):
            a.filtrar([], f / 5)
        self.assertEqual(a._rastreador.objetos, {})
        self.assertEqual(a._episodios, {})


class TestRastreador(unittest.TestCase):
    def test_casamento_por_menor_distancia_nao_depende_da_ordem(self):
        def caixa(cx, cy):
            return {"cabeca": (cx, cy)}

        r = Rastreador(10.0, 150)
        r.atualizar([caixa(100, 100), caixa(140, 100)], 0.0)  # ids 0 e 1
        ids = r.atualizar([caixa(120, 100), caixa(100, 100)], 0.2)
        self.assertEqual(ids, [1, 0])

    def test_quem_ficou_ausente_alem_do_limite_nao_herda_a_nova_observacao(self):
        r = Rastreador(10.0, 150)
        self.assertEqual(r.atualizar([{"cabeca": (100, 100)}], 0.0), [0])
        self.assertEqual(r.atualizar([{"cabeca": (105, 100)}], 13.0), [1])


class TestOcorrencia(unittest.TestCase):
    def test_documento_enviado_a_api_traz_a_cena_inteira(self):
        cena = novo().filtrar(DUAS_PESSOAS, 0.0)
        oc = ocorrencia_da_cena(cena, 1, "2026-10-10T20:13:36+00:00")
        self.assertEqual((oc["id_dispositivo"], oc["total_pessoas"], len(oc["pessoas"])), (1, 2, 2))
        p1, p2 = oc["pessoas"]
        self.assertEqual((p1["numero"], p2["numero"]), (1, 2))
        self.assertEqual(p1["capacete"]["estado"], "ok")  # a pessoa de EPI correto também fica na cena
        self.assertFalse(p1["capacete"]["novo"])
        self.assertTrue(p1["colete"]["novo"])
        self.assertTrue(p2["capacete"]["novo"] and p2["colete"]["novo"])

    def test_so_o_que_disparou_agora_e_novo(self):
        a = novo()
        a.filtrar(DUAS_PESSOAS, 0.0)
        entra = DUAS_PESSOAS + [("Sem_Capacete", 0.8, (20, 20, 120, 110))]
        oc = ocorrencia_da_cena(a.filtrar(entra, 0.4), 1, "t")
        novos = [(p["numero"], k) for p in oc["pessoas"] for k in ("capacete", "colete") if p[k]["novo"]]
        ausentes = [(p["numero"], k) for p in oc["pessoas"] for k in ("capacete", "colete") if p[k]["estado"] == "ausente"]
        self.assertEqual(novos, [(3, "capacete")])
        self.assertEqual(len(ausentes), 4)  # as demais seguem na cena, só que sem disparar de novo

    def test_parte_nao_detectada_e_desconhecida_nunca_ausente(self):
        cena = novo().filtrar([("Sem_Colete", 0.85, (200, 250, 420, 470))], 0.0)  # só tronco
        (pessoa,) = ocorrencia_da_cena(cena, 1, "t")["pessoas"]
        self.assertEqual(pessoa["capacete"], {"estado": "desconhecido", "confianca": None, "novo": False})


class TestFilaOffline(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(config, "PASTA_PENDENTES", Path(self._tmp.name) / "pendentes")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._tmp.cleanup)
        self.oc = ocorrencia_da_cena(novo().filtrar(DUAS_PESSOAS, 0.0), 1, "2026-01-01T00:00:00+00:00")

    def _pendentes(self):
        return sorted(config.PASTA_PENDENTES.glob("*.jpg")) if config.PASTA_PENDENTES.exists() else []

    def test_falha_de_rede_guarda_a_ocorrencia_inteira_em_disco(self):
        with mock.patch.object(cliente_api, "enviar_ocorrencia", return_value=cliente_api.RETENTAR):
            cliente_api.processar_ocorrencia(b"jpeg", self.oc)
        self.assertEqual(len(self._pendentes()), 1)
        meta = json.loads(self._pendentes()[0].with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual(meta["ocorrencia"], self.oc)

    def test_envio_ok_nao_guarda_nada(self):
        with mock.patch.object(cliente_api, "enviar_ocorrencia", return_value=cliente_api.OK):
            cliente_api.processar_ocorrencia(b"jpeg", self.oc)
        self.assertEqual(self._pendentes(), [])

    def test_recusa_definitiva_da_api_nao_vira_pendencia(self):
        with mock.patch.object(cliente_api, "enviar_ocorrencia", return_value=cliente_api.DESCARTAR):
            cliente_api.processar_ocorrencia(b"jpeg", self.oc)
        self.assertEqual(self._pendentes(), [])

    def test_sincronizacao_envia_e_limpa_as_pendencias(self):
        cliente_api.salvar_pendente_ocorrencia(b"a", self.oc)
        cliente_api.salvar_pendente_ocorrencia(b"b", self.oc)
        with mock.patch.object(cliente_api, "enviar_ocorrencia", return_value=cliente_api.OK) as enviar:
            enviados, restantes = cliente_api.sincronizar_pendentes()
        self.assertEqual((enviados, restantes), (2, 0))
        self.assertEqual(enviar.call_count, 2)
        self.assertEqual(self._pendentes(), [])
        self.assertEqual(list(config.PASTA_PENDENTES.glob("*.json")), [])

    def test_pendencia_no_formato_antigo_ainda_e_reenviada_como_infracao_isolada(self):
        config.PASTA_PENDENTES.mkdir(parents=True)
        (config.PASTA_PENDENTES / "0000_antiga.jpg").write_bytes(b"jpeg-antigo")
        (config.PASTA_PENDENTES / "0000_antiga.json").write_text(
            json.dumps({"tipo": "no-helmet", "confianca": 0.9, "timestamp": "2026-01-01T00:00:00+00:00"}),
            encoding="utf-8",
        )
        with mock.patch.object(cliente_api, "enviar_infracao", return_value=cliente_api.OK) as enviar:
            enviados, restantes = cliente_api.sincronizar_pendentes()
        self.assertEqual((enviados, restantes), (1, 0))
        enviar.assert_called_once_with(b"jpeg-antigo", "no-helmet", 0.9, "2026-01-01T00:00:00+00:00")

    def test_sincronizacao_para_no_primeiro_erro_de_rede_e_mantem_o_resto(self):
        cliente_api.salvar_pendente_ocorrencia(b"a", self.oc)
        cliente_api.salvar_pendente_ocorrencia(b"b", self.oc)
        with mock.patch.object(cliente_api, "enviar_ocorrencia", return_value=cliente_api.RETENTAR) as enviar:
            enviados, restantes = cliente_api.sincronizar_pendentes()
        self.assertEqual((enviados, restantes), (0, 2))
        self.assertEqual(enviar.call_count, 1)
        self.assertEqual(len(self._pendentes()), 2)

    def test_limite_de_pendencias_descarta_as_mais_antigas(self):
        with mock.patch.object(config, "MAX_PENDENTES", 3):
            for i in range(5):
                cliente_api.salvar_pendente_ocorrencia(bytes([i]), self.oc)
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
    def _resposta(self, status, texto="x"):
        return mock.Mock(status_code=status, text=texto)

    def test_classificacao_das_respostas_da_api(self):
        casos = {201: cliente_api.OK, 400: cliente_api.DESCARTAR, 404: cliente_api.DESCARTAR,
                 401: cliente_api.RETENTAR, 500: cliente_api.RETENTAR, 503: cliente_api.RETENTAR}
        for status, esperado in casos.items():
            with mock.patch.object(cliente_api.requests, "post", return_value=self._resposta(status)):
                self.assertEqual(cliente_api.enviar_infracao(b"j", "no-vest", 0.8, "t"), esperado, status)
                self.assertEqual(cliente_api.enviar_ocorrencia(b"j", {"pessoas": []}), esperado, status)

    def test_servidor_sem_a_rota_nova_guarda_em_vez_de_descartar(self):
        # Placa atualizada antes da API: o 404 "Rota não encontrada" não pode perder o alerta.
        resposta = self._resposta(404, '{"error":"Rota não encontrada."}')
        with mock.patch.object(cliente_api.requests, "post", return_value=resposta):
            self.assertEqual(cliente_api.enviar_ocorrencia(b"j", {"pessoas": []}), cliente_api.RETENTAR)

    def test_sem_rede_pede_nova_tentativa(self):
        erro = cliente_api.requests.ConnectionError("fora do ar")
        with mock.patch.object(cliente_api.requests, "post", side_effect=erro):
            self.assertEqual(cliente_api.enviar_ocorrencia(b"j", {"pessoas": []}), cliente_api.RETENTAR)
            self.assertFalse(cliente_api.enviar_heartbeat())

    def test_payload_da_ocorrencia_e_chave_de_api(self):
        oc = {"id_dispositivo": 1, "pessoas": [{"numero": 1}]}
        with mock.patch.object(config, "EDGE_API_KEY", "segredo"), \
             mock.patch.object(cliente_api.requests, "post", return_value=self._resposta(201)) as post:
            cliente_api.enviar_ocorrencia(b"j", oc)
        kwargs = post.call_args.kwargs
        self.assertTrue(post.call_args.args[0].endswith("/api/occurrences"))
        self.assertEqual(kwargs["headers"], {"x-api-key": "segredo"})
        self.assertEqual(json.loads(kwargs["data"]["occurrence"]), oc)
        self.assertIn("image", kwargs["files"])  # nome do campo que o multer espera

    def test_payload_da_infracao_isolada_continua_igual(self):
        with mock.patch.object(config, "EDGE_API_KEY", "segredo"), \
             mock.patch.object(cliente_api.requests, "post", return_value=self._resposta(201)) as post:
            cliente_api.enviar_infracao(b"j", "no-helmet", 0.91234, "2026-01-01T00:00:00+00:00")
        kwargs = post.call_args.kwargs
        self.assertEqual(kwargs["data"]["tipo_epi_ausente"], "no-helmet")
        self.assertEqual(kwargs["data"]["confidence"], "0.9123")

    def test_timestamp_em_utc_com_fuso(self):
        self.assertTrue(cliente_api.agora_utc().endswith("+00:00"))


if __name__ == "__main__":
    unittest.main()
