const multer = require('multer');
const env = require('../config/env');
const HttpError = require('../utils/httpError');

const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

// Memória RAM, um único arquivo, com limite de tamanho e de tipo.
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: env.uploadMaxMb * 1024 * 1024, files: 1 },
  fileFilter: (req, file, cb) => {
    if (!ALLOWED_TYPES.includes(file.mimetype)) {
      return cb(new HttpError(400, 'Formato de imagem não suportado. Use JPEG, PNG ou WebP.'));
    }
    cb(null, true);
  },
});

module.exports = upload;
