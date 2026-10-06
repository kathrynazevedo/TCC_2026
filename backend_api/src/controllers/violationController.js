const pool = require('../config/db');

// Busca todas as violações para mostrar no Dashboard
const getViolations = async (req, res) => {
  try {
    // Fazemos um JOIN para buscar o nome da área e formatamos com "AS" 
    // para o Frontend receber os nomes em inglês que ele já espera.
    const query = `
      SELECT 
        i.id_infracao AS id,
        i.tipo_epi_ausente AS type,
        a.nome_area AS zone,
        'high' AS severity, 
        i.status_resolucao AS status,
        i.imagem_url,
        i.timestamp_deteccao AS detected_at,
        i.score_confianca AS confidence
      FROM infracao i
      JOIN dispositivo_borda d ON i.id_dispositivo = d.id_dispositivo
      JOIN area a ON d.id_area = a.id_area
      ORDER BY i.timestamp_deteccao DESC;
    `;
    
    const result = await pool.query(query);
    res.status(200).json({ data: result.rows });
  } catch (error) {
    console.error('Erro ao buscar violações:', error);
    res.status(500).json({ error: 'Erro interno do servidor' });
  }
};

// Atualiza o status (ex: de 'active' para 'resolved')
const updateStatus = async (req, res) => {
  const { id } = req.params;
  const { status } = req.body;
  try {
    const result = await pool.query(
      'UPDATE infracao SET status_resolucao = $1 WHERE id_infracao = $2 RETURNING *',
      [status, id]
    );
    res.status(200).json(result.rows[0]);
  } catch (error) {
    console.error('Erro ao atualizar status:', error);
    res.status(500).json({ error: 'Erro ao atualizar status' });
  }
};

module.exports = { getViolations, updateStatus };