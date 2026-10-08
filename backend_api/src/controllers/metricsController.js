const db = require('../config/db');

// GET /api/metrics — KPIs do topo do dashboard (calculados direto no banco).
exports.getMetrics = async (req, res) => {
  const [infracoes, cameras] = await Promise.all([
    db.query(
      `SELECT COUNT(*)::int AS total_eventos,
              COALESCE(SUM(CASE WHEN COALESCE(status_resolucao, 'active') = 'active' THEN 1 ELSE 0 END), 0)::int AS nao_conformidades
         FROM infracao`
    ),
    db.query('SELECT COUNT(*)::int AS total_cameras FROM dispositivo_borda'),
  ]);

  const { total_eventos, nao_conformidades } = infracoes.rows[0];
  const { total_cameras } = cameras.rows[0];

  // Taxa de segurança = parcela de ocorrências que não estão pendentes.
  const taxa_seguranca =
    total_eventos > 0 ? Math.round(((total_eventos - nao_conformidades) / total_eventos) * 100) : 100;

  res.status(200).json({ total_eventos, nao_conformidades, taxa_seguranca, total_cameras });
};
