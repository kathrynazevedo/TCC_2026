const pool = require('../config/db');

const getMetrics = async (req, res) => {
  try {
    // Fazemos três contagens simultâneas direto no banco
    const query = `
      SELECT 
        (SELECT COUNT(*)::int FROM infracao) AS total_eventos,
        (SELECT COUNT(*)::int FROM infracao WHERE status_resolucao = 'active') AS nao_conformidades,
        (SELECT COUNT(*)::int FROM dispositivo_borda) AS total_cameras
    `;
    
    const result = await pool.query(query);
    const { total_eventos, nao_conformidades, total_cameras } = result.rows[0];
    
    // Calcula a taxa de segurança (compliance rate) no backend
    let taxa_seguranca = 100;
    if (total_eventos > 0) {
      taxa_seguranca = Math.round(((total_eventos - nao_conformidades) / total_eventos) * 100);
    }

    res.status(200).json({
      total_eventos,
      nao_conformidades,
      taxa_seguranca,
      total_cameras
    });
  } catch (error) {
    console.error('Erro ao buscar métricas:', error);
    res.status(500).json({ error: 'Erro ao calcular métricas' });
  }
};

module.exports = { getMetrics };