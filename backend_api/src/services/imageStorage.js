const cloudinary = require('../config/cloudinary');
const HttpError = require('../utils/httpError');

const FOLDER = 'tcc_infracoes_epi';

// Envia o buffer direto por stream (sem converter para base64, que incharia o upload em ~33%).
function uploadEvidence(buffer) {
  return new Promise((resolve, reject) => {
    const stream = cloudinary.uploader.upload_stream({ folder: FOLDER }, (error, result) => {
      if (error || !result) {
        console.error('[CLOUDINARY] Falha no upload:', error && error.message);
        return reject(new HttpError(502, 'Não foi possível armazenar a imagem da infração.'));
      }
      resolve({ url: result.secure_url, publicId: result.public_id });
    });
    stream.end(buffer);
  });
}

// Remove uma imagem órfã (upload feito, mas o registro no banco falhou). Nunca lança erro.
async function deleteEvidence(publicId) {
  try {
    await cloudinary.uploader.destroy(publicId);
  } catch (error) {
    console.error('[CLOUDINARY] Não foi possível remover imagem órfã:', publicId, error.message);
  }
}

module.exports = { uploadEvidence, deleteEvidence };
