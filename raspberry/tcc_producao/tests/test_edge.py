"""Testes da lógica da borda (rodam em qualquer PC, sem câmera, modelo ou GPIO).

    python -m unittest discover -s tests -v      (a partir de raspberry/tcc_producao)

O modelo tem 3 classes (pessoa, capacete, colete); a infração é a AUSÊNCIA do EPI dentro da caixa da pessoa.
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
from deteccao import AlertasPorPessoa, montar_pessoas, ocorrencia_da_cena  # noqa: E402
from rastreador import Rastreador  # noqa: E402

CAP, COL = "no-helmet", "no-vest"


# Quadro 640x480; pessoas em pé com 360 px de altura. Cada detecção é (nome da classe, confiança, caixa).
def pessoa(x, y=40, largura=140, altura=360, conf=0.90):
    return ("person", conf, (x, y, x + largura, y + altura))


def capacete(x, y=40, largura=140, conf=0.85):  # na região da cabeça da pessoa que começa em (x, y)
    return ("helmet", conf, (x + 25, y - 2, x + largura - 25, y + 58))


def colete(x, y=40, largura=140, conf=0.80):  # na região do tronco
    return ("vest", conf, (x + 20, y + 90, x + largura - 20, y + 220))


A, B, C = 60, 400, 230  # posições x de três pessoas lado a lado
COM_TUDO = [pessoa(A), capacete(A), colete(A)]
SEM_CAPACETE = [pessoa(B), colete(B)]
SEM_COLETE = [pessoa(C), capacete(C)]
SEM_NADA = [pessoa(B)]


def novo(realerta=0.0, ausente=10.0, presente=3.0, confirmacao=1.0):
    return AlertasPorPessoa(
        intervalo_realerta=realerta, tempo_ausente=ausente, dist_maxima=150, tempo_presente=presente,
        confianca_pessoa=0.50, confianca_epi=0.35, altura_minima=120, tempo_confirmacao=confirmacao,
    )


def rodar(alertas, deteccoes, inicio, fim, fps=5):
    """Alimenta o sistema com a mesma cena de `inicio` a `fim` (s); devolve [(instante, tipo, numero)] dos alertas."""
    disparos = []
    for f in range(int(inicio * fps), int(fim * fps)):
        t = f / fps
        for tipo, _, numero in alertas.filtrar(deteccoes, t).alertas:
            disparos.append((t, tipo, numero))
    return disparos


class TestClasses(unittest.TestCase):
    def test_papel_aceita_variacoes_de_nome(self):
        for nome in ("person", "Person", "pessoa", "Trabalhador"):
            self.assertEqual(deteccao.papel(nome), deteccao.PESSOA, nome)
        for nome in ("helmet", "Hard-Hat", "hardhat", "Capacete"):
            self.assertEqual(deteccao.papel(nome), deteccao.CAPACETE, nome)
        for nome in ("vest", "safety-vest", "Colete_Refletivo", "colete"):
            self.assertEqual(deteccao.papel(nome), deteccao.COLETE, nome)
        self.assertIsNone(deteccao.papel("Sem_Capacete"))

    def test_modelo_compativel_tem_pessoa_capacete_e_colete(self):
        self.assertEqual(deteccao.papeis_faltando({0: "helmet", 1: "person", 2: "vest"}), [])
        self.assertEqual(deteccao.papeis_faltando(["Capacete", "Colete_Refletivo", "Pessoa"]), [])

    def test_modelo_antigo_com_classes_sem_epi_e_recusado(self):
        antigo = {0: "Capacete", 1: "Colete_Refletivo", 2: "Sem_Capacete", 3: "Sem_Colete"}
        self.assertEqual(deteccao.papeis_faltando(antigo), [deteccao.PESSOA])  # sem "pessoa" nunca alertaria


class TestMontagemDePessoas(unittest.TestCase):
    def montar(self, deteccoes, **kw):
        args = dict(confianca_pessoa=0.50, confianca_epi=0.35, altura_minima=120)
        args.update(kw)
        return montar_pessoas(deteccoes, **args)

    def test_cada_epi_vai_para_a_pessoa_dona_dele(self):
        pessoas = {p.caixa[0]: p for p in self.montar(COM_TUDO + SEM_CAPACETE + SEM_COLETE)}
        self.assertEqual(len(pessoas), 3)
        self.assertEqual((pessoas[A].estado(CAP), pessoas[A].estado(COL)), ("ok", "ok"))
        self.assertEqual((pessoas[B].estado(CAP), pessoas[B].estado(COL)), ("ausente", "ok"))
        self.assertEqual((pessoas[C].estado(CAP), pessoas[C].estado(COL)), ("ok", "ausente"))

    def test_limiar_por_classe_um_colete_duvidoso_nao_esconde_a_falta(self):
        # A pessoa está sem colete, mas o modelo "viu" um a 53% (camiseta clara): com limiar 0,65 isso é falta.
        cena = [pessoa(A), capacete(A), colete(A, conf=0.53)]
        (p,) = self.montar(cena, confianca_epi={deteccao.CAPACETE: 0.50, deteccao.COLETE: 0.65})
        self.assertEqual((p.estado(CAP), p.estado(COL)), ("ok", "ausente"))
        (p,) = self.montar(cena, confianca_epi=0.35)  # com o limiar antigo, único e baixo, o colete falso passa
        self.assertEqual(p.estado(COL), "ok")

    def test_limiar_por_classe_nao_afeta_o_outro_epi(self):
        cena = [pessoa(A), capacete(A, conf=0.55), colete(A, conf=0.80)]
        (p,) = self.montar(cena, confianca_epi={deteccao.CAPACETE: 0.50, deteccao.COLETE: 0.65})
        self.assertEqual((p.estado(CAP), p.estado(COL)), ("ok", "ok"))

    def test_limiar_da_pessoa_respeita_o_piso_do_banco(self):
        # o banco recusa infração com score_confianca < 0,50 (CHECK em infracao): abaixo disso o alerta vira erro 500
        self.assertGreaterEqual(config.CONFIANCA_PESSOA, 0.50)

    def test_config_usa_limiares_separados_e_o_modelo_filtra_pelo_menor(self):
        self.assertEqual(set(config.LIMIARES_EPI), {deteccao.CAPACETE, deteccao.COLETE})
        self.assertEqual(config.CONFIANCA_MODELO, min(config.CONFIANCA_PESSOA, *config.LIMIARES_EPI.values()))

    def test_capacete_e_colete_sem_pessoa_sao_ignorados(self):
        self.assertEqual(self.montar([capacete(A), colete(A)]), [])

    def test_capacete_duplicado_na_mesma_cabeca_nao_cria_nada_nem_quebra(self):
        duplicado = ("helmet", 0.60, (A + 35, 40, A + 105, 90))  # dentro do capacete certo
        (p,) = self.montar([pessoa(A), capacete(A), duplicado, colete(A)])
        self.assertEqual(p.capacete.confianca, 0.85)  # fica a de maior confiança

    def test_pessoas_sobrepostas_o_capacete_vai_para_a_cabeca_mais_proxima(self):
        frente = pessoa(60)  # 60..200
        atras = pessoa(120)  # 120..260: o capacete dela (centro x 190) também cai na faixa da pessoa da frente
        pessoas = {p.caixa[0]: p for p in self.montar([frente, atras, capacete(120)])}
        self.assertEqual(pessoas[120].estado(CAP), "ok")
        self.assertEqual(pessoas[60].estado(CAP), "ausente")

    def test_pessoa_pequena_demais_nao_e_julgada(self):
        longe = ("person", 0.9, (300, 200, 340, 290))  # 90 px de altura
        (p,) = self.montar([longe])
        self.assertEqual((p.estado(CAP), p.estado(COL)), ("desconhecido", "desconhecido"))

    def test_cabeca_cortada_pela_borda_de_cima_nao_cobra_capacete(self):
        (p,) = self.montar([pessoa(A, y=0), colete(A, y=0)])
        self.assertEqual(p.estado(CAP), "desconhecido")  # não dá para saber se há capacete fora do quadro
        self.assertEqual(p.estado(COL), "ok")

    def test_limiares_capacete_baixo_aceita_o_duvidoso_pessoa_alta_ignora_a_fraca(self):
        (p,) = self.montar([pessoa(A), capacete(A, conf=0.40)])
        self.assertEqual(p.estado(CAP), "ok")  # 0,40 >= 0,35: duvidoso, mas conta como presente
        (p,) = self.montar([pessoa(A), capacete(A, conf=0.30)])
        self.assertEqual(p.estado(CAP), "ausente")  # abaixo de 0,35 não conta
        self.assertEqual(self.montar([pessoa(A, conf=0.45)]), [])  # pessoa com 0,45 < 0,50 é ignorada


class TestAlertasPorPessoa(unittest.TestCase):
    def test_falta_so_vira_alerta_depois_de_confirmada(self):
        disparos = rodar(novo(), SEM_CAPACETE, 0, 5)
        self.assertEqual([(t, tipo) for t, tipo, _ in disparos], [(1.0, CAP)])  # confirmação de 1,0 s: não antes

    def test_sem_confirmacao_alerta_no_primeiro_quadro(self):
        disparos = rodar(novo(confirmacao=0), SEM_CAPACETE, 0, 2)
        self.assertEqual([(t, tipo) for t, tipo, _ in disparos], [(0.0, CAP)])

    def test_oscilacao_do_modelo_nao_vira_alarme_falso(self):
        # O modelo "perde" o capacete em 2 de cada 3 quadros (a 5 FPS, 0,4 s sem ver): nunca chega a 1,0 s contínuo.
        a = novo()
        alertas = []
        for f in range(5 * 60):
            deteccoes = COM_TUDO if f % 3 == 2 else [pessoa(A), colete(A)]
            alertas += a.filtrar(deteccoes, f / 5).alertas
        self.assertEqual(alertas, [])

    def test_pessoa_parada_sem_capacete_gera_um_unico_alerta_em_qualquer_fps(self):
        for fps in (2, 5, 15):
            disparos = rodar(novo(), SEM_CAPACETE, 0, 60, fps)
            self.assertEqual([(tipo, n) for _, tipo, n in disparos], [(CAP, 1)], f"{fps} FPS")

    def test_pessoa_com_todos_os_epis_conta_mas_nao_alerta(self):
        a = novo()
        self.assertEqual(rodar(a, COM_TUDO, 0, 10), [])
        self.assertEqual(a.filtrar(COM_TUDO, 10.0).situacao, ((1, ()),))

    def test_duas_pessoas_cada_uma_com_a_sua_falta(self):
        disparos = rodar(novo(), SEM_CAPACETE + SEM_COLETE, 0, 5)
        self.assertEqual(sorted((tipo, n) for _, tipo, n in disparos), [(CAP, 1), (COL, 2)])

    def test_sem_nenhum_epi_acusa_os_dois_na_mesma_pessoa(self):
        disparos = rodar(novo(), SEM_NADA, 0, 5)
        self.assertEqual(sorted((tipo, n) for _, tipo, n in disparos), [(CAP, 1), (COL, 1)])

    def test_quem_nao_da_para_julgar_nunca_gera_alerta(self):
        longe = [("person", 0.9, (300, 200, 340, 290))]
        cortada = [("person", 0.9, (60, 0, 200, 360)), colete(A, y=0)]
        self.assertEqual(rodar(novo(), longe, 0, 30), [])
        self.assertEqual(rodar(novo(), cortada, 0, 30), [])  # tem colete; capacete não é julgável no topo cortado

    def test_realerta_configuravel(self):
        disparos = rodar(novo(realerta=10.0), SEM_CAPACETE, 0, 25)
        self.assertEqual([t for t, _, _ in disparos], [1.0, 11.0, 21.0])

    def test_volta_logo_nao_repete_mas_depois_de_muito_tempo_alerta_de_novo(self):
        a = novo()
        rodar(a, SEM_CAPACETE, 0, 3)  # alerta em 1,0; última vez vista em 2,8
        a.filtrar([], 6.0)
        self.assertEqual(rodar(a, SEM_CAPACETE, 8, 11), [])  # voltou em 5 s: mesma falta, sem novo alerta
        a.filtrar([], 12.0)
        a.filtrar([], 25.0)  # sumiu por mais de 10 s: é uma nova ocorrência
        disparos = rodar(a, SEM_CAPACETE, 26, 30)
        self.assertEqual(len(disparos), 1)

    def test_tira_poe_e_tira_o_capacete_dentro_da_janela_nao_repete(self):
        a = novo()
        sem, com = [pessoa(A), colete(A)], COM_TUDO
        self.assertEqual(len(rodar(a, sem, 0, 2)), 1)  # alerta
        rodar(a, com, 2, 5)  # põe o capacete
        self.assertEqual(rodar(a, sem, 5, 8), [])  # tira de novo em 5 s: mesma ocorrência
        rodar(a, com, 8, 25)  # fica 17 s regularizado
        self.assertEqual(len(rodar(a, sem, 25, 28)), 1)  # tira de novo: nova ocorrência

    def test_numeracao_se_recompacta_quando_alguem_sai(self):
        a = novo(confirmacao=0)
        p1, p2, p3 = SEM_CAPACETE, SEM_COLETE, [pessoa(A)]
        self.assertEqual([(t, n) for t, _, n in a.filtrar(p1, 0.0).alertas], [(CAP, 1)])
        cena = a.filtrar(p1 + p2, 1.0)
        self.assertEqual([(t, n) for t, _, n in cena.alertas], [(COL, 2)])
        self.assertEqual(len(a.filtrar(p2, 3.5).situacao), 2)  # a 1 saiu há 2,5 s: ainda conta
        cena = a.filtrar(p2, 4.2)  # saiu há 3,2 s: a 2 vira 1, e renumerar não gera alerta
        self.assertEqual(cena.situacao, ((1, (COL,)),))
        self.assertEqual(cena.alertas, [])
        cena = a.filtrar(p2 + p3, 5.0)  # quem chega depois ocupa o número seguinte
        self.assertEqual([(t, n) for t, _, n in cena.alertas], [(CAP, 2), (COL, 2)])

    def test_memoria_e_limpa_depois_que_todos_saem(self):
        a = novo(realerta=10.0)
        rodar(a, SEM_NADA + SEM_COLETE, 0, 3)
        for f in range(80):
            a.filtrar([], 3 + f / 5)
        self.assertEqual(a._rastreador.objetos, {})
        self.assertEqual((a._episodios, a._sem_epi), ({}, {}))

    def test_a_mesma_pessoa_com_a_caixa_piscando_continua_sendo_uma_so(self):
        a = novo()
        for f in range(100):
            deteccoes = SEM_CAPACETE if f % 4 else []  # a caixa some em 1 de cada 4 quadros
            cena = a.filtrar(deteccoes, f / 5)
            self.assertLessEqual(len(cena.situacao), 1)


class TestRastreador(unittest.TestCase):
    def test_casamento_por_menor_distancia_nao_depende_da_ordem(self):
        def ponto(cx, cy):
            return {"centro": (cx, cy)}

        r = Rastreador(10.0, 150)
        r.atualizar([ponto(100, 100), ponto(140, 100)], 0.0)  # ids 0 e 1
        ids = r.atualizar([ponto(120, 100), ponto(100, 100)], 0.2)
        self.assertEqual(ids, [1, 0])

    def test_quem_ficou_ausente_alem_do_limite_nao_herda_a_nova_observacao(self):
        r = Rastreador(10.0, 150)
        self.assertEqual(r.atualizar([{"centro": (100, 100)}], 0.0), [0])
        self.assertEqual(r.atualizar([{"centro": (105, 100)}], 13.0), [1])


class TestOcorrencia(unittest.TestCase):
    def test_documento_enviado_a_api_traz_a_cena_inteira(self):
        cena = novo(confirmacao=0).filtrar(COM_TUDO + SEM_CAPACETE, 0.0)
        oc = ocorrencia_da_cena(cena, 1, "2026-10-10T20:13:36+00:00")
        self.assertEqual((oc["id_dispositivo"], oc["total_pessoas"], len(oc["pessoas"])), (1, 2, 2))
        (p1, p2) = oc["pessoas"] if oc["pessoas"][0]["caixa"][0] == A else reversed(oc["pessoas"])
        self.assertEqual(p1["capacete"], {"estado": "ok", "confianca": 0.85, "novo": False})  # pessoa de EPI correto
        self.assertEqual(p2["colete"]["estado"], "ok")
        # sem capacete: a confiança que vai é a da PESSOA (não há detecção de capacete para medir)
        self.assertEqual(p2["capacete"], {"estado": "ausente", "confianca": 0.9, "novo": True})

    def test_so_o_que_disparou_agora_e_novo(self):
        a = novo(confirmacao=0)
        a.filtrar(SEM_CAPACETE, 0.0)
        oc = ocorrencia_da_cena(a.filtrar(SEM_CAPACETE + SEM_COLETE, 0.2), 1, "t")
        novos = [(p["numero"], k) for p in oc["pessoas"] for k in ("capacete", "colete") if p[k]["novo"]]
        ausentes = [(p["numero"], k) for p in oc["pessoas"] for k in ("capacete", "colete") if p[k]["estado"] == "ausente"]
        self.assertEqual(novos, [(2, "colete")])
        self.assertEqual(len(ausentes), 2)  # o capacete da pessoa 1 segue na cena, mas já tinha sido alertado

    def test_pessoa_que_nao_da_para_julgar_e_desconhecida_nunca_ausente(self):
        cena = novo(confirmacao=0).filtrar([("person", 0.9, (300, 200, 340, 290))], 0.0)
        (p,) = ocorrencia_da_cena(cena, 1, "t")["pessoas"]
        self.assertEqual(p["capacete"], {"estado": "desconhecido", "confianca": None, "novo": False})
        self.assertEqual(p["colete"]["estado"], "desconhecido")

    def test_falta_ainda_nao_confirmada_aparece_como_desconhecida(self):
        cena = novo(confirmacao=1.0).filtrar(SEM_CAPACETE, 0.0)
        (p,) = ocorrencia_da_cena(cena, 1, "t")["pessoas"]
        self.assertEqual(p["capacete"]["estado"], "desconhecido")


class TestFilaOffline(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(config, "PASTA_PENDENTES", Path(self._tmp.name) / "pendentes")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._tmp.cleanup)
        self.oc = ocorrencia_da_cena(
            novo(confirmacao=0).filtrar(COM_TUDO + SEM_CAPACETE, 0.0), 1, "2026-01-01T00:00:00+00:00"
        )

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

    def test_heartbeat_leva_a_telemetria_so_quando_ha(self):
        with mock.patch.object(cliente_api.requests, "post", return_value=self._resposta(200)) as post:
            self.assertTrue(cliente_api.enviar_heartbeat({"temperatura_c": 51.0, "fps": 2.0}))
            self.assertEqual(post.call_args.kwargs["json"]["telemetria"], {"temperatura_c": 51.0, "fps": 2.0})
            cliente_api.enviar_heartbeat()  # placa antiga/sem dados: o corpo continua sendo só o id do dispositivo
            self.assertEqual(post.call_args.kwargs["json"], {"id_dispositivo": config.ID_DISPOSITIVO})

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
