"""Regras de negócio da detecção, sem dependências pesadas (testável fora da Raspberry)."""

TIPO_CAPACETE = "no-helmet"
TIPO_COLETE = "no-vest"
TIPO_AMBOS = "no-helmet-no-vest"  # sem capacete E sem colete no mesmo quadro: um único alerta

# Alerta "ambos" já dado cobre os dois tipos simples durante a janela do debounce.
_COBERTO_POR = {TIPO_CAPACETE: TIPO_AMBOS, TIPO_COLETE: TIPO_AMBOS}

# Nomes de classe que o modelo pode emitir -> código canônico enviado à API.
_CLASSES = {
    "sem_capacete": TIPO_CAPACETE,
    "no_helmet": TIPO_CAPACETE,
    "sem_colete": TIPO_COLETE,
    "no_vest": TIPO_COLETE,
}


def classificar(nome_classe):
    """Devolve 'no-helmet', 'no-vest' ou None (classe que não é infração, ex.: 'Capacete')."""
    chave = str(nome_classe).strip().lower().replace("-", "_").replace(" ", "_")
    return _CLASSES.get(chave)


class Debounce:
    """Evita alertas repetidos do mesmo tipo dentro de uma janela de tempo."""

    def __init__(self, intervalo):
        self.intervalo = intervalo
        self._ultimo = {}

    def permitir(self, tipo, agora):
        """True (e registra o disparo) se já passou o intervalo desde o último alerta do tipo."""
        # Se acabou de sair um alerta "ambos", uma oscilação do modelo para só-capacete/só-colete não repete o aviso.
        cobertor = _COBERTO_POR.get(tipo)
        if cobertor and agora - self._ultimo.get(cobertor, float("-inf")) < self.intervalo:
            return False
        if agora - self._ultimo.get(tipo, float("-inf")) < self.intervalo:
            return False
        self._ultimo[tipo] = agora
        return True


def resumir_infracoes(deteccoes, confianca_minima):
    """Recebe [(nome_classe, confianca)] e devolve {tipo: maior_confianca} só das infrações válidas."""
    resumo = {}
    for nome, confianca in deteccoes:
        tipo = classificar(nome)
        if tipo is None or confianca < confianca_minima:
            continue
        resumo[tipo] = max(confianca, resumo.get(tipo, 0.0))
    return resumo


def combinar_infracoes(resumo):
    """Junta 'no-helmet' + 'no-vest' do mesmo quadro em um único 'no-helmet-no-vest'.

    A confiança do alerta combinado é a menor das duas: as duas ausências precisam ser verdadeiras.
    Observação: o modelo detecta classes, não pessoas; com duas pessoas no quadro (uma sem capacete e
    outra sem colete) o resultado também é 'ambos'.
    """
    combinado = dict(resumo)
    if TIPO_CAPACETE in combinado and TIPO_COLETE in combinado:
        combinado[TIPO_AMBOS] = min(combinado.pop(TIPO_CAPACETE), combinado.pop(TIPO_COLETE))
    return combinado
