const multer = require('multer');
const HttpError = require('../utils/httpError');

function notFound(req, res) {
  res.status(404).json({ error: 'Rota não encontrada.' });
}

// Handler central: o Express 5 encaminha para cá qualquer erro lançado em handlers async.
// eslint-disable-next-line no-unused-vars
function errorHandler(err, req, res, next) {
  if (err instanceof HttpError) {
    return res.status(err.status).json({ error: err.message });
  }

  if (err instanceof multer.MulterError) {
    if (err.code === 'LIMIT_FILE_SIZE') {
      return res.status(413).json({ error: 'Imagem maior que o limite permitido.' });
    }
    return res.status(400).json({ error: 'Upload inválido.' });
  }

  if (err.type === 'entity.parse.failed') {
    return res.status(400).json({ error: 'JSON inválido.' });
  }
  if (err.type === 'entity.too.large') {
    return res.status(413).json({ error: 'Requisição grande demais.' });
  }

  console.error(`[ERRO] ${req.method} ${req.originalUrl}:`, err);
  res.status(500).json({ error: 'Erro interno do servidor.' });
}

module.exports = { notFound, errorHandler };
