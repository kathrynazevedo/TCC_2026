"""Regras de negócio da detecção, sem dependências pesadas (testável fora da Raspberry)."""
from collections import namedtuple

from rastreador import Rastreador

TIPO_CAPACETE = "no-helmet"
TIPO_COLETE = "no-vest"
ROTULOS = {TIPO_CAPACETE: "sem capacete", TIPO_COLETE: "sem colete"}  # para mensagens ao operador

CABECA, TRONCO = "cabeca", "tronco"  # onde cada EPI fica no corpo

# Nome de classe que o modelo pode emitir -> (parte do corpo, tipo de infração ou None se o EPI está correto).
_CLASSES = {
    "sem_capacete": (CABECA, TIPO_CAPACETE),
    "no_helmet": (CABECA, TIPO_CAPACETE),
    "capacete": (CABECA, None),
    "helmet": (CABECA, None),
    "sem_colete": (TRONCO, TIPO_COLETE),
    "no_vest": (TRONCO, TIPO_COLETE),
    "colete_refletivo": (TRONCO, None),
    "vest": (TRONCO, None),
}

# Duas caixas da mesma parte que se sobrepõem mais que isso (da menor) são a mesma coisa vista duas vezes.
SOBREPOSICAO_MAXIMA = 0.5


def interpretar(nome_classe):
    """Devolve (parte do corpo, tipo de infração ou None) ou None se a classe não é um EPI conhecido."""
    chave = str(nome_classe).strip().lower().replace("-", "_").replace(" ", "_")
    return _CLASSES.get(chave)


def classificar(nome_classe):
    """Devolve 'no-helmet', 'no-vest' ou None (classe que não é infração, ex.: 'Capacete')."""
    item = interpretar(nome_classe)
    return item[1] if item else None


# ==========================================
# GEOMETRIA
# ==========================================
def _centro(caixa):
    return (caixa[0] + caixa[2]) // 2, (caixa[1] + caixa[3]) // 2


def _sobreposicao(a, b):
    """Interseção dividida pela área da MENOR caixa: 1.0 = uma está inteira dentro da outra.

    Usa a menor área (e não o IoU) porque o modelo costuma desenhar uma segunda caixa menor dentro da primeira
    sobre a mesma cabeça/tronco; o IoU dessas fica baixo e o NMS do YOLO não as funde.
    """
    largura = min(a[2], b[2]) - max(a[0], b[0])
    altura = min(a[3], b[3]) - max(a[1], b[1])
    if largura <= 0 or altura <= 0:
        return 0.0
    menor = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return largura * altura / menor if menor > 0 else 0.0


def _sem_duplicadas(partes):
    """Entre caixas que se sobrepõem demais, fica a de maior confiança."""
    mantidas = []
    for parte in sorted(partes, key=lambda p: p.confianca, reverse=True):
        if all(_sobreposicao(parte.caixa, outra.caixa) < SOBREPOSICAO_MAXIMA for outra in mantidas):
            mantidas.append(parte)
    return mantidas


def _afinidade(cabeca, tronco):
    """Pode esta cabeça ser da pessoa deste tronco? Devolve None, ou (nível, custo) para ordenar os pares.

    Nível 0 = bem alinhados (o centro da cabeça cai na faixa horizontal do tronco, com 25% de folga, e a cabeça
    começa na metade de cima dele). Nível 1 = só plausível (a cabeça pode estar inclinada, na borda do vídeo ou
    perto da câmera): o centro dela passa da faixa do tronco por até uma largura de cabeça. Os pares de nível 0
    são ligados primeiro, então o nível 1 só vale para o que sobrar; isso evita que uma mesma pessoa vire duas
    ("só cabeça" + "só tronco") quando a detecção não encaixa certinho.
    """
    cx, cy = _centro(cabeca)
    custo = abs(cx - _centro(tronco)[0])
    if cy >= tronco[3]:  # centro da cabeça abaixo do fim do tronco: não é a mesma pessoa
        return None

    largura_tronco = tronco[2] - tronco[0]
    altura_tronco = tronco[3] - tronco[1]
    fora = max(tronco[0] - cx, cx - tronco[2], 0)  # quanto o centro da cabeça passa da faixa do tronco
    if fora <= 0.25 * largura_tronco and cabeca[1] < tronco[1] + 0.6 * altura_tronco:
        return 0, custo
    if fora <= cabeca[2] - cabeca[0]:
        return 1, custo
    return None


# ==========================================
# PESSOAS
# ==========================================
Parte = namedtuple("Parte", "nome infracao confianca caixa")  # infracao: tipo ou None (EPI correto)


class Pessoa:
    """Uma pessoa no frame: a cabeça e/ou o tronco detectados (None = não detectado)."""

    def __init__(self, cabeca=None, tronco=None):
        self.cabeca = cabeca
        self.tronco = tronco

    def partes(self):
        return [p for p in (self.cabeca, self.tronco) if p is not None]

    def caixa(self):
        """Caixa que envolve todas as partes detectadas."""
        caixas = [p.caixa for p in self.partes()]
        return (min(c[0] for c in caixas), min(c[1] for c in caixas), max(c[2] for c in caixas), max(c[3] for c in caixas))

    def infracoes(self):
        """{tipo: confiança} das infrações visíveis neste frame."""
        return {p.infracao: p.confianca for p in self.partes() if p.infracao}

    def ancoras(self):
        return {
            nome: _centro(parte.caixa)
            for nome, parte in ((CABECA, self.cabeca), (TRONCO, self.tronco))
            if parte is not None
        }


def montar_pessoas(deteccoes, confianca_minima):
    """Recebe [(nome_classe, confianca, caixa)] e agrupa cabeça + tronco do mesmo corpo em `Pessoa`s.

    Toda cabeça detectada (de capacete ou sem) é uma pessoa. Cada tronco vai para a cabeça mais bem alinhada (ver
    `_afinidade`), e uma caixa de tronco nunca serve a duas pessoas: é assim que duas pessoas lado a lado não
    misturam o colete.
    """
    cabecas, troncos = [], []
    for nome, confianca, caixa in deteccoes:
        item = interpretar(nome)
        if item is None or confianca < confianca_minima:
            continue
        parte, infracao = item
        (cabecas if parte == CABECA else troncos).append(Parte(nome, infracao, confianca, tuple(caixa)))

    pessoas = [Pessoa(cabeca=c) for c in _sem_duplicadas(cabecas)]

    candidatos = []
    for i, pessoa in enumerate(pessoas):
        for j, tronco in enumerate(troncos):
            afinidade = _afinidade(pessoa.cabeca.caixa, tronco.caixa)
            if afinidade is not None:
                candidatos.append((*afinidade, i, j))
    candidatos.sort()  # melhores pares primeiro: (nível, custo, cabeça, tronco)

    usados = set()  # troncos já ligados a uma cabeça
    duplicados = set()  # troncos que são só uma segunda caixa de um tronco já ligado

    def ligar(nivel):
        for n, _, i, j in candidatos:
            if n == nivel and pessoas[i].tronco is None and j not in usados and j not in duplicados:
                pessoas[i].tronco = troncos[j]
                usados.add(j)

    def repete_um_ligado(j):
        return any(_sobreposicao(troncos[j].caixa, troncos[k].caixa) >= SOBREPOSICAO_MAXIMA for k in usados)

    ligar(0)
    # Antes de aceitar pares "só plausíveis", a segunda caixa de um tronco já ligado sai de cena: senão ela
    # poderia ser entregue à cabeça de um vizinho, que passaria a ser acusado de um colete que ninguém detectou.
    duplicados.update(j for j in range(len(troncos)) if j not in usados and repete_um_ligado(j))
    ligar(1)

    # Tronco que sobrou: ou é uma segunda caixa de um tronco já atribuído (descarta) ou é alguém cuja cabeça não
    # foi detectada / está fora do enquadramento (vira uma pessoa só com tronco).
    aceitos = [troncos[j] for j in usados]
    for j in sorted(set(range(len(troncos))) - usados - duplicados, key=lambda j: troncos[j].confianca, reverse=True):
        if all(_sobreposicao(troncos[j].caixa, outro.caixa) < SOBREPOSICAO_MAXIMA for outro in aceitos):
            pessoas.append(Pessoa(tronco=troncos[j]))
            aceitos.append(troncos[j])
    return pessoas


# ==========================================
# ALERTAS
# ==========================================
# numero: posição por ordem de chegada entre quem está em cena | pessoa: `Pessoa` | infracoes: tipos visíveis agora
PessoaEmCena = namedtuple("PessoaEmCena", "numero pessoa infracoes")
# alertas: [(tipo, confianca, numero)] a enviar agora | pessoas: [PessoaEmCena] vistas neste frame
# situacao: ((numero, (tipos em infração)), ...) de todos em cena; só muda quando entra/sai alguém ou muda a infração
Cena = namedtuple("Cena", "alertas pessoas situacao")


class AlertasPorPessoa:
    """Rastreia as pessoas e decide quais infrações viram alerta: um por pessoa e tipo, por episódio.

    Um episódio termina quando a infração some por `tempo_ausente` segundos (ou a pessoa sai de cena); a mesma
    infração só gera novo alerta se um novo episódio começar ou, se configurado, a cada `intervalo_realerta`.
    """

    def __init__(self, intervalo_realerta, tempo_ausente, dist_maxima, tempo_presente, confianca_minima):
        # intervalo_realerta: segundos para repetir o alerta de quem continua em infração (0 = nunca repete)
        # tempo_ausente: segundos até o rastreador esquecer a pessoa (evita alerta repetido se a detecção piscar)
        # tempo_presente: segundos sem aparecer até a pessoa deixar de contar como "em cena" (numeração e contagem)
        self.intervalo_realerta = intervalo_realerta
        self.confianca_minima = confianca_minima
        self._tempo_ausente = tempo_ausente
        self._tempo_presente = tempo_presente
        self._rastreador = Rastreador(tempo_ausente, dist_maxima)
        self._episodios = {}  # (id_pessoa, tipo) -> [instante em que a infração foi vista, instante do alerta]

    def filtrar(self, deteccoes, agora):
        """Recebe [(nome_classe, confianca, caixa)] do frame e devolve uma `Cena`.

        O ID do rastreador é único e só cresce (é ele que evita o alerta repetido). O número mostrado ao operador é
        outro: a posição por ordem de chegada entre quem está em cena, então quando a pessoa 1 sai a 2 vira 1 e
        quem chegar depois ocupa o número seguinte.

        Chame a cada frame, mesmo sem detecções, para o rastreamento perceber quem saiu de cena.
        """
        pessoas = montar_pessoas(deteccoes, self.confianca_minima)
        ids = self._rastreador.atualizar([p.ancoras() for p in pessoas], agora)

        em_cena = self._rastreador.presentes(agora, self._tempo_presente)
        numero_de = {id_pessoa: posicao for posicao, id_pessoa in enumerate(em_cena, start=1)}

        alertas, vistas = [], []
        for id_pessoa, pessoa in zip(ids, pessoas):
            infracoes = pessoa.infracoes()
            for tipo, confianca in infracoes.items():
                episodio = self._episodios.get((id_pessoa, tipo))
                if episodio is None or agora - episodio[0] > self._tempo_ausente:
                    novo = True  # primeira vez, ou a infração tinha sumido por tempo suficiente para ser outra
                else:
                    novo = self.intervalo_realerta > 0 and agora - episodio[1] >= self.intervalo_realerta
                if novo:
                    self._episodios[(id_pessoa, tipo)] = [agora, agora]
                    alertas.append((tipo, confianca, numero_de[id_pessoa]))
                else:
                    episodio[0] = agora
            vistas.append(PessoaEmCena(numero_de[id_pessoa], pessoa, tuple(sorted(infracoes))))

        # Esquece quem o rastreador já descartou, para a memória não crescer com o tempo.
        for chave in [k for k in self._episodios if k[0] not in self._rastreador.objetos]:
            del self._episodios[chave]

        situacao = tuple(
            (
                numero_de[id_pessoa],
                tuple(
                    sorted(
                        tipo
                        for (i, tipo), episodio in self._episodios.items()
                        if i == id_pessoa and agora - episodio[0] <= self._tempo_presente
                    )
                ),
            )
            for id_pessoa in em_cena
        )
        return Cena(alertas, vistas, situacao)


# ==========================================
# OCORRÊNCIA (o que é enviado à API)
# ==========================================
def _estado_epi(parte, tipo, numero, novos):
    """{estado, confianca, novo} de um EPI: 'ausente' | 'ok' | 'desconhecido' (parte não detectada)."""
    if parte is None:
        return {"estado": "desconhecido", "confianca": None, "novo": False}
    ausente = parte.infracao is not None
    return {
        "estado": "ausente" if ausente else "ok",
        "confianca": round(parte.confianca, 4),
        "novo": ausente and (tipo, numero) in novos,
    }


def ocorrencia_da_cena(cena, id_dispositivo, timestamp, severidade="high"):
    """Monta o documento enviado à API: a cena inteira de um frame, não uma infração isolada.

    Traz TODAS as pessoas vistas no frame, com ou sem EPI, para o painel mostrar o contexto; `novo` marca o que
    disparou um alerta agora e que a API deve registrar como infração (o resto já foi alertado antes).
    `total_pessoas` é a contagem em cena, que pode incluir quem acabou de sair do enquadramento.
    """
    novos = {(tipo, numero) for tipo, _, numero in cena.alertas}
    pessoas = [
        {
            "numero": numero,
            "caixa": list(pessoa.caixa()),
            "capacete": _estado_epi(pessoa.cabeca, TIPO_CAPACETE, numero, novos),
            "colete": _estado_epi(pessoa.tronco, TIPO_COLETE, numero, novos),
        }
        for numero, pessoa, _ in sorted(cena.pessoas, key=lambda p: p.numero)
    ]
    return {
        "id_dispositivo": id_dispositivo,
        "timestamp": timestamp,
        "severity": severidade,
        "total_pessoas": max(len(cena.situacao), len(pessoas)),
        "pessoas": pessoas,
    }
