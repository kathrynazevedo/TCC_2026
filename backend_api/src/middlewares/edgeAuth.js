const crypto = require('crypto');
const env = require('../config/env');

// Protege as rotas chamadas pela Raspberry Pi. Sem EDGE_API_KEY (apenas dev) deixa passar.
module.exports = function edgeAuth(req, res, next) {
  if (!env.edgeApiKey) return next();

  const provided = Buffer.from(req.get('x-api-key') || '');
  const expected = Buffer.from(env.edgeApiKey);

  if (provided.length !== expected.length || !crypto.timingSafeEqual(provided, expected)) {
    return res.status(401).json({ error: 'Chave de API inválida ou ausente.' });
  }
  next();
};
