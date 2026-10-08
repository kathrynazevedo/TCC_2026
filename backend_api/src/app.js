const fs = require('fs');
const path = require('path');
const express = require('express');
const cors = require('cors');

const env = require('./config/env');
const db = require('./config/db');
const { notFound, errorHandler } = require('./middlewares/errorHandler');

const systemRoutes = require('./routes/systemRoutes');
const violationRoutes = require('./routes/violationRoutes');
const metricsRoutes = require('./routes/metricsRoutes');
const areaRoutes = require('./routes/areaRoutes');
const workersRoutes = require('./routes/workersRoutes');

// Build do frontend (npm run build na pasta frontend). Se existir, o backend também serve o dashboard.
const FRONTEND_DIST = env.frontendDist || path.resolve(__dirname, '../../frontend/dist');

function createApp() {
  const app = express();
  app.disable('x-powered-by');

  app.use((req, res, next) => {
    res.setHeader('X-Content-Type-Options', 'nosniff');
    next();
  });

  // Em produção o CORS_ORIGIN lista as origens permitidas; em dev, vazio libera tudo.
  app.use(cors(env.corsOrigins.length > 0 ? { origin: env.corsOrigins } : undefined));
  app.use(express.json({ limit: '100kb' }));

  app.get('/api/health', async (req, res) => {
    try {
      await db.query('SELECT 1');
      res.status(200).json({ status: 'OK', database: 'up', message: 'API rodando!' });
    } catch (error) {
      console.error('[HEALTH] Banco indisponível:', error.message);
      res.status(503).json({ status: 'DEGRADED', database: 'down', message: 'API rodando, banco indisponível.' });
    }
  });

  app.use('/api/status', systemRoutes);
  app.use('/api/violations', violationRoutes);
  app.use('/api/metrics', metricsRoutes);
  app.use('/api/areas', areaRoutes);
  app.use('/api/workers', workersRoutes);
  app.use('/api', notFound);

  if (fs.existsSync(path.join(FRONTEND_DIST, 'index.html'))) {
    app.use(express.static(FRONTEND_DIST));
    // Fallback do React Router: qualquer GET fora de /api devolve o index.html.
    app.use((req, res, next) => {
      if (req.method !== 'GET') return next();
      // `root` evita que uma pasta com ponto no caminho (ex.: .claude, .config) faça o sendFile recusar o arquivo.
      res.sendFile('index.html', { root: FRONTEND_DIST });
    });
  }

  app.use(notFound);
  app.use(errorHandler);

  return app;
}

module.exports = createApp;
