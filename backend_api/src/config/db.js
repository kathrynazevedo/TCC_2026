const { Pool } = require('pg');
const env = require('./env');

const pool = new Pool({
  connectionString: env.databaseUrl,
  ssl: env.databaseSsl ? { rejectUnauthorized: env.databaseSslVerify } : false,
  max: 10,
  idleTimeoutMillis: 30000,
  // O Neon "dorme" quando ocioso; a primeira conexão pode demorar alguns segundos.
  connectionTimeoutMillis: 15000,
});

// Sem este handler, um erro em conexão ociosa derruba o processo inteiro.
pool.on('error', (err) => {
  console.error('[DB] Erro em conexão ociosa do pool:', err.message);
});

async function checkConnection() {
  await pool.query('SELECT 1');
}

module.exports = pool;
module.exports.checkConnection = checkConnection;
