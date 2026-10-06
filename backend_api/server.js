require('dotenv').config();
const express = require('express');
const cors = require('cors');
const pool = require('./src/config/db');

// Importando as rotas
const violationRoutes = require('./src/routes/violationRoutes');
const metricsRoutes = require('./src/routes/metricsRoutes'); // <-- Adicione esta linha
const app = express();
const PORT = process.env.PORT || 3000;
const areaRoutes = require('./src/routes/areaRoutes'); // <-- Adicione esta linha

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.get('/api/health', (req, res) => {
  res.status(200).json({ status: 'OK', message: 'API rodando!' });
});
app.use('/api/metrics', metricsRoutes); // <-- E adicione esta linha
// Adicionando a rota de violações ao servidor
app.use('/api/violations', violationRoutes);
app.use('/api/areas', areaRoutes); // <-- E adicione esta linha
app.listen(PORT, () => {
  console.log(`Servidor rodando na porta ${PORT}`);
});