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

// "https://res.cloudinary.com/x/image/upload/v123/tcc_infracoes_epi/abc.jpg" -> "tcc_infracoes_epi/abc".
// Só aceita imagens da pasta do projeto: nunca apaga algo que este sistema não enviou.
function publicIdFromUrl(url) {
  if (typeof url !== 'string') return null;
  const match = url.match(/\/upload\/(?:v\d+\/)?(.+)\.[A-Za-z0-9]+(?:\?.*)?$/);
  return match && match[1].startsWith(`${FOLDER}/`) ? match[1] : null;
}

const BULK_DELETE_LIMIT = 100; // limite da API do Cloudinary por chamada

// Remove as evidências de infrações excluídas. Melhor esforço: nunca lança erro, porque o
// registro já saiu do banco e uma imagem sobrando não pode derrubar a exclusão.
async function deleteEvidencesByUrl(urls) {
  const publicIds = urls.map(publicIdFromUrl).filter(Boolean);
  for (let i = 0; i < publicIds.length; i += BULK_DELETE_LIMIT) {
    const chunk = publicIds.slice(i, i + BULK_DELETE_LIMIT);
    try {
      await cloudinary.api.delete_resources(chunk);
    } catch (error) {
      console.error('[CLOUDINARY] Não foi possível remover imagens:', chunk.length, error.message);
    }
  }
}

module.exports = { uploadEvidence, deleteEvidence, deleteEvidencesByUrl, publicIdFromUrl };
