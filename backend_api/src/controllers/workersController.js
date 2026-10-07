const pool = require('../config/db');

const getWorkers = async (req, res) => {
    try {
        const query = `
            SELECT 
                id_trabalhador AS id,
                nome AS name,
                cargo AS role,
                status,
                zona AS zone
            FROM trabalhador
            ORDER BY nome ASC;
        `;
        const result = await pool.query(query);
        res.status(200).json({ data: result.rows });
    } catch (error) {
        console.error('Erro ao buscar trabalhadores:', error);
        res.status(500).json({ error: 'Erro ao buscar trabalhadores do banco de dados' });
    }
};

module.exports = { getWorkers };