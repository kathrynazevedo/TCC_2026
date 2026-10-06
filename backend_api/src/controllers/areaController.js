const pool = require('../config/db');

const getAreasAndDevices = async (req, res) => {
  try {
    // Fazemos um LEFT JOIN para listar as áreas e verificar qual dispositivo de borda (câmera) está lá alocado
    const query = `
      SELECT 
        a.id_area,
        a.nome_area,
        a.descricao,
        d.id_dispositivo,
        d.numero_serie,
        d.ultima_atividade
      FROM area a
      LEFT JOIN dispositivo_borda d ON a.id_area = d.id_area;
    `;
    
    const result = await pool.query(query);
    res.status(200).json({ data: result.rows });
  } catch (error) {
    console.error('Erro ao buscar áreas e dispositivos:', error);
    res.status(500).json({ error: 'Erro ao buscar áreas e dispositivos' });
  }
};

module.exports = { getAreasAndDevices };