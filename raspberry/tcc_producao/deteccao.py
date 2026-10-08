"""Regras de negócio da detecção, sem dependências pesadas (testável fora da Raspberry)."""

TIPO_CAPACETE = "no-helmet"
TIPO_COLETE = "no-vest"

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
