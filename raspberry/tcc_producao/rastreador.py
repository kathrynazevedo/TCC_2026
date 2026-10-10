"""Rastreamento por centroide: mantém um ID estável para cada objeto entre frames consecutivos.

Cada objeto (uma pessoa) é descrito por âncoras nomeadas, ex.: {"cabeca": (x, y), "tronco": (x, y)}. Duas
observações são a mesma pessoa se QUALQUER parte em comum estiver perto: se a cabeça deixar de ser detectada, o
tronco mantém a identidade, e vice-versa.

Só matemática básica (sem dependências), leve o bastante para a Raspberry Pi 4.
"""
import math


def _distancia(novas, antigas):
    """Menor distância entre as partes que os dois têm em comum (infinito se não houver nenhuma)."""
    return min(
        (math.hypot(novas[p][0] - antigas[p][0], novas[p][1] - antigas[p][1]) for p in novas.keys() & antigas.keys()),
        default=math.inf,
    )


class Rastreador:
    def __init__(self, tempo_ausente=10.0, dist_maxima=150):
        # tempo_ausente: segundos que o objeto pode ficar sem aparecer antes de ser esquecido
        # dist_maxima: distância máxima (px) entre dois frames para ser considerado o mesmo objeto
        self.tempo_ausente = tempo_ausente
        self.dist_maxima = dist_maxima
        self.objetos = {}  # id -> {parte: (cx, cy)} última posição conhecida de cada parte
        self._visto_em = {}  # id -> instante em que foi visto pela última vez
        self._proximo_id = 0

    def presentes(self, agora, janela):
        """IDs vistos nos últimos `janela` segundos, de quem chegou primeiro a quem chegou por último."""
        return sorted(i for i, visto in self._visto_em.items() if agora - visto <= janela)

    def atualizar(self, ancoras, agora):
        """Recebe, para cada objeto do frame, {parte: (cx, cy)} e devolve o ID de cada um, na mesma ordem.

        Chame a cada frame, inclusive sem objetos: é assim que o rastreador percebe quem saiu de cena.
        `agora` é um relógio em segundos (ex.: time.monotonic()).
        """
        # Esquece antes de casar: quem ficou ausente além do limite não pode herdar a nova observação.
        for id_obj in [i for i, visto in self._visto_em.items() if agora - visto > self.tempo_ausente]:
            del self.objetos[id_obj]
            del self._visto_em[id_obj]

        # Casa primeiro os pares mais próximos, para o resultado não depender da ordem das observações.
        pares = sorted(
            (dist, i, id_obj)
            for i, novas in enumerate(ancoras)
            for id_obj, antigas in self.objetos.items()
            if (dist := _distancia(novas, antigas)) < self.dist_maxima
        )
        ids = [None] * len(ancoras)
        usados = set()
        for _, i, id_obj in pares:
            if ids[i] is None and id_obj not in usados:
                ids[i] = id_obj
                usados.add(id_obj)
                self.objetos[id_obj].update(ancoras[i])
                self._visto_em[id_obj] = agora

        # Observação que não casou com ninguém é um objeto novo.
        for i, id_obj in enumerate(ids):
            if id_obj is None:
                ids[i] = self._proximo_id
                self._proximo_id += 1
                self.objetos[ids[i]] = dict(ancoras[i])
                self._visto_em[ids[i]] = agora

        return ids
