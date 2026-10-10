/**
 * Junta as infrações da mesma captura. A placa envia a cena inteira de uma vez (uma foto, várias pessoas); no banco
 * cada EPI ausente vira uma infração própria (com status próprio), mas na tela elas pertencem a um único cartão.
 * Registros antigos, sem ocorrência, formam um grupo de um item cada.
 *
 * Mantém a ordem de entrada (a API já devolve do mais recente para o mais antigo).
 */
export function groupByOccurrence(violations) {
  const groups = new Map();
  for (const v of violations) {
    const key = v.occurrence_id ? `oc-${v.occurrence_id}` : `inf-${v.id}`;
    if (!groups.has(key)) {
      groups.set(key, {
        key,
        occurrence_id: v.occurrence_id ?? null,
        id_dispositivo: v.id_dispositivo,
        imagem_url: v.imagem_url,
        detected_at: v.detected_at,
        zone: v.zone,
        people: v.people ?? null,
        people_total: v.people_total ?? null,
        items: [],
      });
    }
    groups.get(key).items.push(v);
  }
  return [...groups.values()];
}
