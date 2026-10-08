require('dotenv').config({ quiet: true });

const toInt = (value, fallback) => {
  const parsed = parseInt(value, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
};

const isProduction = process.env.NODE_ENV === 'production';

module.exports = {
  isProduction,
  port: toInt(process.env.PORT, 3000),

  databaseUrl: process.env.DATABASE_URL,
  // Neon exige SSL. Use DATABASE_SSL=false apenas para um Postgres local.
  databaseSsl: process.env.DATABASE_SSL !== 'false',
  // Só desligue a verificação do certificado se o driver reclamar do certificado do provedor.
  databaseSslVerify: process.env.DATABASE_SSL_VERIFY !== 'false',

  // Chave que a Raspberry Pi envia no header x-api-key (POST /violations e POST /status/heartbeat).
  edgeApiKey: process.env.EDGE_API_KEY || '',

  // Lista separada por vírgula. Vazio = qualquer origem (apenas em desenvolvimento).
  corsOrigins: (process.env.CORS_ORIGIN || '')
    .split(',')
    .map((origin) => origin.trim())
    .filter(Boolean),

  // Pasta do build do React (padrão: ../frontend/dist). Útil quando o front é publicado em outro lugar.
  frontendDist: process.env.FRONTEND_DIST || '',

  uploadMaxMb: toInt(process.env.UPLOAD_MAX_MB, 5),
  // Tempo sem heartbeat para considerar a placa offline (a placa envia a cada 30s).
  edgeOfflineAfterSeconds: toInt(process.env.EDGE_OFFLINE_AFTER_SECONDS, 90),
};
