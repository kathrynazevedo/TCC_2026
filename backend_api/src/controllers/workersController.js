const db = require('../config/db');

// GET /api/workers
exports.getWorkers = async (req, res) => {
  const result = await db.query(
    `SELECT id_trabalhador AS id,
            nome AS name,
            cargo AS role,
            status,
            zona AS zone
       FROM trabalhador
      ORDER BY nome ASC`
  );

  res.status(200).json({ data: result.rows });
};
