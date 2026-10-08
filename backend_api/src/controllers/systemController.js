const db = require('../config/db');
const env = require('../config/env');
const HttpError = require('../utils/httpError');
const { parseId } = require('../utils/validators');

// GET /api/status/edge — painel "Sistema" do dashboard.
exports.getEdgeStatus = async (req, res) => {
  // A diferença é calculada no próprio banco: evita erro de fuso entre Node e Postgres.
  const result = await db.query(
    `SELECT id_dispositivo,
            numero_serie,
            ultima_atividade,
            (EXTRACT(EPOCH FROM NOW()) - EXTRACT(EPOCH FROM ultima_atividade))::float AS segundos_inativo
       FROM dispositivo_borda
      WHERE ultima_atividade IS NOT NULL
      ORDER BY ultima_atividade DESC
      LIMIT 1`
  );

  if (result.rows.length === 0) {
    return res.status(200).json({
      online: false,
      segundos_inativo: null,
      limite_offline_segundos: env.edgeOfflineAfterSeconds,
      detalhes: null,
    });
  }

  const { segundos_inativo, ...detalhes } = result.rows[0];
  res.status(200).json({
    online: segundos_inativo <= env.edgeOfflineAfterSeconds,
    segundos_inativo: Math.max(0, Math.round(segundos_inativo)),
    limite_offline_segundos: env.edgeOfflineAfterSeconds,
    detalhes,
  });
};

// POST /api/status/heartbeat — chamada pela Raspberry Pi a cada 30s.
exports.edgeHeartbeat = async (req, res) => {
  const idDispositivo = parseId((req.body || {}).id_dispositivo, 'id_dispositivo');

  const result = await db.query(
    `UPDATE dispositivo_borda
        SET ultima_atividade = NOW()
      WHERE id_dispositivo = $1
      RETURNING id_dispositivo`,
    [idDispositivo]
  );

  if (result.rows.length === 0) {
    throw new HttpError(404, 'Dispositivo não encontrado no banco.');
  }

  res.status(200).json({ message: 'Heartbeat registrado com sucesso' });
};
