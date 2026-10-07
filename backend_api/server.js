require('dotenv').config();
const express = require('express');
const cors = require('cors');

// Importação da conexão com o banco (opcional manter aqui se não for usar direto no server)
const pool = require('./src/config/db');

// Importando todas as rotas
const systemRoutes = require('./src/routes/systemRoutes');
const violationRoutes = require('./src/routes/violationRoutes');
const metricsRoutes = require('./src/routes/metricsRoutes');
const areaRoutes = require('./src/routes/areaRoutes');
const workersRoutes = require('./src/routes/workersRoutes'); // <-- Adicionado

const app = express();
const PORT = process.env.PORT || 3000;

// Middlewares
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Rota de Health Check (Teste simples)
app.get('/api/health', (req, res) => {
  res.status(200).json({ status: 'OK', message: 'API rodando!' });
});

// Registrando as Rotas da API
app.use('/api/status', systemRoutes);
app.use('/api/violations', violationRoutes);
app.use('/api/metrics', metricsRoutes);
app.use('/api/areas', areaRoutes);
app.use('/api/workers', workersRoutes); // <-- Adicionado

app.listen(PORT, () => {
  console.log(`🚀 Servidor rodando na porta ${PORT}`);
});