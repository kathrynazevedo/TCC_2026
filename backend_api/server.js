const env = require('./src/config/env');
const db = require('./src/config/db');
const createApp = require('./src/app');

if (env.isProduction && !env.edgeApiKey) {
  console.error('[CONFIG] Defina EDGE_API_KEY: em produção as rotas da placa exigem autenticação.');
  process.exit(1);
}
if (!env.databaseUrl) {
  console.error('[CONFIG] DATABASE_URL não definida. Copie .env.example para .env e preencha.');
  process.exit(1);
}
if (!env.edgeApiKey) {
  console.warn('[CONFIG] EDGE_API_KEY vazia: as rotas da placa estão abertas (aceitável só em desenvolvimento).');
}

const app = createApp();

const server = app.listen(env.port, async () => {
  console.log(`Servidor rodando na porta ${env.port}`);
  try {
    await db.checkConnection();
    console.log('Conectado ao banco de dados com sucesso!');
  } catch (error) {
    console.error('Falha ao conectar no banco (verifique DATABASE_URL e SSL no .env):', error.message);
  }
});

// Encerramento limpo: para de aceitar conexões, termina as em andamento e fecha o pool.
function shutdown(signal) {
  console.log(`\n${signal} recebido, encerrando...`);
  server.close(async () => {
    await db.end().catch(() => {});
    process.exit(0);
  });
  setTimeout(() => process.exit(1), 10000).unref();
}
process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));

process.on('unhandledRejection', (reason) => {
  console.error('[PROCESSO] Promise rejeitada sem tratamento:', reason);
});
