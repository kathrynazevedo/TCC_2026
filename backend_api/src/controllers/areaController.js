const db = require('../config/db');
const env = require('../config/env');

// GET /api/areas — áreas com os dispositivos de borda (câmeras) alocados em cada uma.
exports.getAreasAndDevices = async (req, res) => {
  const result = await db.query(
    `SELECT a.id_area,
            a.nome_area,
            a.descricao,
            d.id_dispositivo,
            d.numero_serie,
            d.ultima_atividade,
            (EXTRACT(EPOCH FROM NOW()) - EXTRACT(EPOCH FROM d.ultima_atividade))::float AS segundos_inativo
       FROM area a
       LEFT JOIN dispositivo_borda d ON a.id_area = d.id_area
      ORDER BY a.id_area, d.id_dispositivo`
  );

  // O JOIN devolve uma linha por dispositivo; agrupamos para o frontend receber 1 item por área.
  const areas = new Map();
  for (const row of result.rows) {
    if (!areas.has(row.id_area)) {
      areas.set(row.id_area, {
        id_area: row.id_area,
        nome_area: row.nome_area,
        descricao: row.descricao,
        dispositivos: [],
      });
    }
    if (row.id_dispositivo !== null) {
      areas.get(row.id_area).dispositivos.push({
        id_dispositivo: row.id_dispositivo,
        numero_serie: row.numero_serie,
        ultima_atividade: row.ultima_atividade,
        online: row.segundos_inativo !== null && row.segundos_inativo <= env.edgeOfflineAfterSeconds,
      });
    }
  }

  res.status(200).json({ data: [...areas.values()] });
};
