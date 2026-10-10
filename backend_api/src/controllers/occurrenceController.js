const db = require('../config/db');
const imageStorage = require('../services/imageStorage');
const HttpError = require('../utils/httpError');
const { parseOccurrence } = require('../utils/validators');

// POST /api/occurrences — chamada pela Raspberry Pi (multipart/form-data: "image" + "occurrence" em JSON).
// Uma requisição = uma captura: a foto sobe uma vez e a cena inteira (todas as pessoas, com ou sem EPI)
// é gravada junto com as infrações novas, numa única transação.
exports.registrarOcorrencia = async (req, res) => {
  // 1. Valida tudo ANTES de gastar upload no Cloudinary.
  if (!req.file) {
    throw new HttpError(400, 'Nenhuma imagem da ocorrência foi enviada (campo "image").');
  }
  const ocorrencia = parseOccurrence(req.body.occurrence);

  const device = await db.query('SELECT 1 FROM dispositivo_borda WHERE id_dispositivo = $1', [ocorrencia.id_dispositivo]);
  if (device.rows.length === 0) {
    throw new HttpError(404, 'Dispositivo não cadastrado.');
  }

  // 2. Guarda a evidência e só então grava no banco; se o banco falhar, desfaz tudo e remove a imagem órfã.
  const { url, publicId } = await imageStorage.uploadEvidence(req.file.buffer);

  const client = await db.connect();
  try {
    await client.query('BEGIN');

    const criada = await client.query(
      `INSERT INTO ocorrencia (id_dispositivo, timestamp_deteccao, imagem_url, total_pessoas, pessoas)
       VALUES ($1, $2, $3, $4, $5)
       RETURNING id_ocorrencia`,
      [ocorrencia.id_dispositivo, ocorrencia.timestamp, url, ocorrencia.total_pessoas, JSON.stringify(ocorrencia.pessoas)]
    );
    const idOcorrencia = criada.rows[0].id_ocorrencia;

    const infracoes = [];
    for (const infracao of ocorrencia.infracoes) {
      const inserida = await client.query(
        `INSERT INTO infracao
           (id_dispositivo, tipo_epi_ausente, score_confianca, timestamp_deteccao,
            imagem_url, sincronizado_nuvem, status_resolucao, severidade, id_ocorrencia, numero_pessoa)
         VALUES ($1, $2, $3, $4, $5, TRUE, 'active', $6, $7, $8)
         RETURNING id_infracao`,
        [
          ocorrencia.id_dispositivo,
          infracao.tipo,
          infracao.confianca,
          ocorrencia.timestamp,
          url,
          ocorrencia.severity,
          idOcorrencia,
          infracao.numero,
        ]
      );
      infracoes.push({
        id_infracao: inserida.rows[0].id_infracao,
        tipo_epi_ausente: infracao.tipo,
        numero_pessoa: infracao.numero,
      });
    }

    await client.query('COMMIT');

    return res.status(201).json({
      message: 'Ocorrência registrada com sucesso no sistema!',
      data: {
        id_ocorrencia: idOcorrencia,
        id_dispositivo: ocorrencia.id_dispositivo,
        total_pessoas: ocorrencia.total_pessoas,
        image_url: url,
        timestamp: ocorrencia.timestamp,
        infracoes,
      },
    });
  } catch (error) {
    await client.query('ROLLBACK').catch(() => {});
    await imageStorage.deleteEvidence(publicId);
    throw error;
  } finally {
    client.release();
  }
};
