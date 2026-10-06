const { Pool } = require('pg');
require('dotenv').config();

// Cria o pool de conexões com o Neon usando a URL do arquivo .env
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: {
    rejectUnauthorized: false // Obrigatório para conexões seguras em nuvem (Neon)
  }
});

// Testa a conexão com o banco
pool.connect((err, client, release) => {
  if (err) {
    return console.error('Erro ao conectar no banco de dados Neon (verifique a DATABASE_URL no .env):', err.message);
  }
  console.log('Conectado ao banco de dados Neon com sucesso!');
  release();
});

module.exports = pool;