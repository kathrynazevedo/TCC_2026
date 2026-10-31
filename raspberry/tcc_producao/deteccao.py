"""Regras de negócio da detecção, sem dependências pesadas (testável fora da Raspberry).

O modelo detecta três coisas: a PESSOA, o CAPACETE e o COLETE (os equipamentos presentes). Não existe classe "sem
EPI": a infração é a AUSÊNCIA. Para cada pessoa o sistema procura um capacete na região da cabeça e um colete na
região do tronco, dentro da caixa dela; quem não tem, de forma contínua por `tempo_confirmacao` segundos, está em
infração.

Como a infração nasce de uma NÃO-detecção, três cuidados evitam alarme falso:
  - a falta tem de durar `tempo_confirmacao` segundos (um capacete que o modelo deixa de ver por um quadro não alerta);
  - só se avalia quem dá para avaliar: pessoa pequena demais (longe) ou com a cabeça cortada pela borda não conta;
  - capacete/colete entram com um limiar BAIXO de confiança (melhor aceitar um duvidoso como presente).
"""
from collections import namedtuple

from rastreador import Rastreador

TIPO_CAPACETE = "no-helmet"
TIPO_COLETE = "no-vest"
ROTULOS = {TIPO_CAPACETE: "sem capacete", TIPO_COLETE: "sem colete"}  # para mensagens ao operador

# Estado de um EPI de uma pessoa (as mesmas palavras que a API recebe).
OK, AUSENTE, DESCONHECIDO = "ok", "ausente", "desconhecido"

# Papel de cada classe do modelo; o modelo é identificado pelo NOME da classe, não pela ordem.
PESSOA, CAPACETE, COLETE = "pessoa", "capacete", "colete"
_NOMES = {
    PESSOA: {"person", "pessoa", "people", "worker", "trabalhador", "human"},
    CAPACETE: {"helmet", "hardhat", "hard_hat", "safety_helmet", "capacete"},
    COLETE: {"vest", "safety_vest", "reflective_vest", "safetyvest", "colete", "colete_refletivo"},
}
_PAPEL_DO_NOME = {nome: papel for papel, nomes in _NOMES.items() for nome in nomes}

# Caixas do mesmo EPI que se sobrepõem mais que isso (da menor) são a mesma coisa vista duas vezes.
SOBREPOSICAO_MAXIMA = 0.5
MARGEM_TOPO = 3  # px: pessoa encostada no topo do quadro está com a cabeça cortada


def papel(nome_classe):
    """'Helmet' -> 'capacete', 'person' -> 'pessoa', ...; None se a classe não é nenhuma das três."""
    chave = str(nome_classe).strip().lower().replace("-", "_").replace(" ", "_")
    return _PAPEL_DO_NOME.get(chave)


def papeis_faltando(nomes_das_classes):
    """Papéis (pessoa, capacete, colete) que o modelo NÃO tem. Vazio = modelo compatível.

    Aceita o `model.names` do Ultralytics (dict id -> nome) ou uma lista de nomes. Serve para o sistema recusar,
    na partida, um modelo que nunca conseguiria alertar (sem classe de pessoa, de capacete ou de colete).
    """
    nomes = nomes_das_classes.values() if hasattr(nomes_das_classes, "values") else nomes_das_classes
    presentes = {papel(n) for n in nomes}
    return [p for p in (PESSOA, CAPACETE, COLETE) if p not in presentes]


# ==========================================
# GEOMETRIA
# ==========================================
def _centro(caixa):
    return (caixa[0] + caixa[2]) // 2, (caixa[1] + caixa[3]) // 2


def _sobreposicao(a, b):
    """Interseção dividida pela área da MENOR caixa: 1.0 = uma está inteira dentro da outra.

    Usa a menor área (e não o IoU) porque o modelo costuma desenhar uma segunda caixa menor dentro da primeira
    sobre o mesmo equipamento; o IoU dessas fica baixo e o NMS do YOLO não as funde.
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


def _afinidade_capacete(corpo, capacete):
    """Custo (menor = melhor) se o capacete está na região da cabeça da pessoa; None se não está.

    A cabeça fica no alto da caixa da pessoa: o centro do capacete tem de cair na faixa horizontal dela (com 10% de
    folga) e entre um pouco acima do topo e 40% da altura.
    """
    x1, y1, x2, y2 = corpo
    largura, altura = x2 - x1, y2 - y1
    if largura <= 0 or altura <= 0:
        return None
    cx, cy = _centro(capacete)
    if not (x1 - 0.1 * largura <= cx <= x2 + 0.1 * largura and y1 - 0.15 * altura <= cy <= y1 + 0.40 * altura):
        return None
    return abs(cx - (x1 + x2) / 2) / largura + abs(cy - (y1 + 0.10 * altura)) / altura


def _afinidade_colete(corpo, colete):
    """Custo (menor = melhor) se o colete está na região do tronco da pessoa; None se não está."""
    x1, y1, x2, y2 = corpo
    largura, altura = x2 - x1, y2 - y1
    if largura <= 0 or altura <= 0:
        return None
    cx, cy = _centro(colete)
    if not (x1 - 0.1 * largura <= cx <= x2 + 0.1 * largura and y1 + 0.10 * altura <= cy <= y1 + 0.85 * altura):
        return None
    return abs(cx - (x1 + x2) / 2) / largura + abs(cy - (y1 + 0.40 * altura)) / altura


# ==========================================
# PESSOAS
# ==========================================
Parte = namedtuple("Parte", "nome confianca caixa")


class Pessoa:
    """Uma pessoa detectada no frame, com o capacete e o colete que o modelo achou dentro da caixa dela."""

    def __init__(self, corpo, avaliavel):
        self.corpo = corpo  # Parte da classe pessoa
        self.capacete = None  # Parte, ou None se nenhum capacete foi achado na região da cabeça
        self.colete = None
        self.avaliavel = avaliavel  # {TIPO_CAPACETE: bool, TIPO_COLETE: bool}: dá para julgar a falta?

    @property
    def caixa(self):
        return self.corpo.caixa

    @property
    def confianca(self):
        return self.corpo.confianca

    def epis(self):
        return [p for p in (self.capacete, self.colete) if p is not None]

    def estado(self, tipo):
        """ok (achou o EPI), ausente (não achou e dava para ver) ou desconhecido (não dá para julgar)."""
        parte = self.capacete if tipo == TIPO_CAPACETE else self.colete
        if parte is not None:
            return OK
        return AUSENTE if self.avaliavel[tipo] else DESCONHECIDO

    def ancoras(self):
        """Pontos para o rastreador: o centro e o topo da caixa (se um mudar de forma, o outro ainda casa)."""
        x1, y1, x2, y2 = self.caixa
        return {"centro": _centro(self.caixa), "topo": ((x1 + x2) // 2, y1)}


def _ligar(pessoas, epis, afinidade, atributo):
    """Entrega cada EPI à pessoa que mais combina com ele, no máximo um por pessoa e uma pessoa por EPI."""
    pares = sorted(
        (custo, i, j)
        for i, pessoa in enumerate(pessoas)
        for j, epi in enumerate(epis)
        if (custo := afinidade(pessoa.caixa, epi.caixa)) is not None
    )
    pessoas_usadas, epis_usados = set(), set()
    for _, i, j in pares:
        if i not in pessoas_usadas and j not in epis_usados:
            setattr(pessoas[i], atributo, epis[j])
            pessoas_usadas.add(i)
            epis_usados.add(j)


def _limiar_epi(confianca_epi, quem):
    """`confianca_epi` é um número (vale para os dois EPIs) ou {CAPACETE: x, COLETE: y}."""
    return confianca_epi[quem] if isinstance(confianca_epi, dict) else confianca_epi


def montar_pessoas(deteccoes, confianca_pessoa, confianca_epi, altura_minima):
    """Recebe [(nome_classe, confianca, caixa)] e devolve as `Pessoa`s, cada uma com o capacete e o colete achados.

    Capacete ou colete que não está dentro da caixa de nenhuma pessoa é ignorado: sem pessoa não há quem avaliar.
    Uma pessoa só é julgável se for grande o bastante (`altura_minima`, em px) e, para o capacete, se a cabeça não
    estiver cortada pela borda de cima do quadro; do contrário o estado é "desconhecido" e nada é cobrado dela.
    """
    corpos, capacetes, coletes = [], [], []
    for nome, confianca, caixa in deteccoes:
        quem = papel(nome)
        parte = Parte(nome, confianca, tuple(caixa))
        if quem == PESSOA and confianca >= confianca_pessoa:
            corpos.append(parte)
        elif quem == CAPACETE and confianca >= _limiar_epi(confianca_epi, CAPACETE):
            capacetes.append(parte)
        elif quem == COLETE and confianca >= _limiar_epi(confianca_epi, COLETE):
            coletes.append(parte)

    pessoas = []
    for corpo in corpos:
        grande = corpo.caixa[3] - corpo.caixa[1] >= altura_minima
        pessoas.append(
            Pessoa(corpo, {TIPO_CAPACETE: grande and corpo.caixa[1] > MARGEM_TOPO, TIPO_COLETE: grande})
        )
    _ligar(pessoas, _sem_duplicadas(capacetes), _afinidade_capacete, "capacete")
    _ligar(pessoas, _sem_duplicadas(coletes), _afinidade_colete, "colete")
    return pessoas


# ==========================================
# ALERTAS
# ==========================================
# numero: posição por ordem de chegada entre quem está em cena | pessoa: `Pessoa`
# infracoes: tipos em infração CONFIRMADA (ausência contínua pelo tempo de confirmação)
PessoaEmCena = namedtuple("PessoaEmCena", "numero pessoa infracoes")
# alertas: [(tipo, confianca, numero)] a enviar agora | pessoas: [PessoaEmCena] vistas neste frame
# situacao: ((numero, (tipos em infração)), ...) de todos em cena; só muda quando entra/sai alguém ou muda a infração
Cena = namedtuple("Cena", "alertas pessoas situacao")


class AlertasPorPessoa:
    """Rastreia as pessoas e decide quais faltas de EPI viram alerta: um por pessoa e tipo, por episódio.

    A falta só conta depois de `tempo_confirmacao` segundos contínuos. Um episódio termina quando a falta some por
    `tempo_ausente` segundos (ou a pessoa sai de cena); a mesma falta só gera novo alerta se um novo episódio
    começar ou, se configurado, a cada `intervalo_realerta`.
    """

    def __init__(
        self, intervalo_realerta, tempo_ausente, dist_maxima, tempo_presente,
        confianca_pessoa, confianca_epi, altura_minima, tempo_confirmacao,
    ):
        # intervalo_realerta: segundos para repetir o alerta de quem continua em infração (0 = nunca repete)
        # tempo_ausente: segundos até o rastreador esquecer a pessoa (evita alerta repetido se a detecção piscar)
        # tempo_presente: segundos sem aparecer até a pessoa deixar de contar como "em cena" (numeração e contagem)
        # tempo_confirmacao: segundos de falta contínua antes de acusar (0 = acusa no primeiro quadro)
        self.intervalo_realerta = intervalo_realerta
        self._tempo_ausente = tempo_ausente
        self._tempo_presente = tempo_presente
        self._confianca_pessoa = confianca_pessoa
        self._confianca_epi = confianca_epi
        self._altura_minima = altura_minima
        self._confirmacao = tempo_confirmacao
        self._rastreador = Rastreador(tempo_ausente, dist_maxima)
        self._sem_epi = {}  # (id_pessoa, tipo) -> [desde quando falta sem parar, última vez em que se viu faltando]
        self._episodios = {}  # (id_pessoa, tipo) -> [instante em que a falta foi vista, instante do alerta]

    def _confirmada(self, chave, pessoa, tipo, agora):
        """True se a pessoa está sem o EPI de forma contínua há tempo suficiente."""
        if pessoa.estado(tipo) != AUSENTE:  # tem o EPI ou não dá para julgar: recomeça a contagem
            self._sem_epi.pop(chave, None)
            return False
        corrida = self._sem_epi.get(chave)
        # Se a pessoa ficou um tempo sem ser vista, o que valia antes não conta: nova contagem.
        if corrida is None or agora - corrida[1] > self._confirmacao + 1.0:
            corrida = self._sem_epi[chave] = [agora, agora]
        corrida[1] = agora
        return agora - corrida[0] >= self._confirmacao

    def filtrar(self, deteccoes, agora):
        """Recebe [(nome_classe, confianca, caixa)] do frame e devolve uma `Cena`.

        O ID do rastreador é único e só cresce (é ele que evita o alerta repetido). O número mostrado ao operador é
        outro: a posição por ordem de chegada entre quem está em cena, então quando a pessoa 1 sai a 2 vira 1 e
        quem chegar depois ocupa o número seguinte.

        Chame a cada frame, mesmo sem detecções, para o rastreamento perceber quem saiu de cena.
        """
        pessoas = montar_pessoas(deteccoes, self._confianca_pessoa, self._confianca_epi, self._altura_minima)
        ids = self._rastreador.atualizar([p.ancoras() for p in pessoas], agora)

        em_cena = self._rastreador.presentes(agora, self._tempo_presente)
        numero_de = {id_pessoa: posicao for posicao, id_pessoa in enumerate(em_cena, start=1)}

        alertas, vistas = [], []
        for id_pessoa, pessoa in zip(ids, pessoas):
            confirmadas = []
            for tipo in (TIPO_CAPACETE, TIPO_COLETE):
                if not self._confirmada((id_pessoa, tipo), pessoa, tipo, agora):
                    continue
                confirmadas.append(tipo)
                episodio = self._episodios.get((id_pessoa, tipo))
                if episodio is None or agora - episodio[0] > self._tempo_ausente:
                    novo = True  # primeira vez, ou a falta tinha sumido por tempo suficiente para ser outra
                else:
                    novo = self.intervalo_realerta > 0 and agora - episodio[1] >= self.intervalo_realerta
                if novo:
                    self._episodios[(id_pessoa, tipo)] = [agora, agora]
                    alertas.append((tipo, pessoa.confianca, numero_de[id_pessoa]))
                else:
                    episodio[0] = agora
            vistas.append(PessoaEmCena(numero_de[id_pessoa], pessoa, tuple(sorted(confirmadas))))

        # Esquece quem o rastreador já descartou, para a memória não crescer com o tempo.
        vivos = self._rastreador.objetos
        for tabela in (self._episodios, self._sem_epi):
            for chave in [k for k in tabela if k[0] not in vivos]:
                del tabela[chave]

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
def _estado_epi(pessoa, tipo, confirmada, numero, novos):
    """{estado, confianca, novo} de um EPI.

    ok: a confiança é a do capacete/colete achado. ausente: não existe detecção para medir, então vai a confiança
    da PESSOA (a certeza de que há alguém ali sem o EPI). desconhecido: não dá para julgar ou a falta ainda não
    foi confirmada.
    """
    parte = pessoa.capacete if tipo == TIPO_CAPACETE else pessoa.colete
    if parte is not None:
        return {"estado": OK, "confianca": round(parte.confianca, 4), "novo": False}
    if confirmada:
        return {"estado": AUSENTE, "confianca": round(pessoa.confianca, 4), "novo": (tipo, numero) in novos}
    return {"estado": DESCONHECIDO, "confianca": None, "novo": False}


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
            "caixa": list(pessoa.caixa),
            "capacete": _estado_epi(pessoa, TIPO_CAPACETE, TIPO_CAPACETE in infracoes, numero, novos),
            "colete": _estado_epi(pessoa, TIPO_COLETE, TIPO_COLETE in infracoes, numero, novos),
        }
        for numero, pessoa, infracoes in sorted(cena.pessoas, key=lambda p: p.numero)
    ]
    return {
        "id_dispositivo": id_dispositivo,
        "timestamp": timestamp,
        "severity": severidade,
        "total_pessoas": max(len(cena.situacao), len(pessoas)),
        "pessoas": pessoas,
    }
