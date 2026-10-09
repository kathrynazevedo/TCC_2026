const db = require('../config/db');
const imageStorage = require('../services/imageStorage');
const HttpError = require('../utils/httpError');
const {
  SEVERITIES,
  STATUSES,
  normalizeEpiType,
  isKnownEpiType,
  parseId,
  parseConfidence,
  parseTimestamp,
} = require('../utils/validators');

const DEFAULT_LIMIT = 500;
const MAX_LIMIT = 1000;

// POST /api/violations — chamada pela Raspberry Pi (multipart/form-data, campo "image").
exports.registrarInfracao = async (req, res) => {
  const { id_dispositivo, tipo_epi_ausente, timestamp, confidence, severity } = req.body;

  // 1. Valida tudo ANTES de gastar upload no Cloudinary.
  if (!req.file) {
    throw new HttpError(400, 'Nenhuma imagem de infração foi enviada (campo "image").');
  }
  const idDispositivo = parseId(id_dispositivo, 'id_dispositivo');

  const tipoEpi = normalizeEpiType(tipo_epi_ausente);
  if (!isKnownEpiType(tipoEpi)) {
    throw new HttpError(400, 'tipo_epi_ausente inválido. Use "no-helmet" ou "no-vest".');
  }

  const severidade = severity || 'high';
  if (!SEVERITIES.includes(severidade)) {
    throw new HttpError(400, `severity inválida. Use: ${SEVERITIES.join(', ')}.`);
  }

  const scoreConfianca = parseConfidence(confidence);
  const dataInfracao = parseTimestamp(timestamp);

  const device = await db.query('SELECT 1 FROM dispositivo_borda WHERE id_dispositivo = $1', [idDispositivo]);
  if (device.rows.length === 0) {
    throw new HttpError(404, 'Dispositivo não cadastrado.');
  }

  // 2. Guarda a evidência e só então grava no banco; se o banco falhar, remove a imagem órfã.
  const { url, publicId } = await imageStorage.uploadEvidence(req.file.buffer);

  try {
    const result = await db.query(
      `INSERT INTO infracao
         (id_dispositivo, tipo_epi_ausente, score_confianca, timestamp_deteccao,
          imagem_url, sincronizado_nuvem, status_resolucao, severidade)
       VALUES ($1, $2, $3, $4, $5, TRUE, 'active', $6)
       RETURNING id_infracao`,
      [idDispositivo, tipoEpi, scoreConfianca, dataInfracao, url, severidade]
    );

    return res.status(201).json({
      message: 'Infração registrada com sucesso no sistema!',
      data: {
        id_infracao: result.rows[0].id_infracao,
        id_dispositivo: idDispositivo,
        tipo_epi_ausente: tipoEpi,
        image_url: url,
        timestamp: dataInfracao,
      },
    });
  } catch (error) {
    await imageStorage.deleteEvidence(publicId);
    throw error;
  }
};

// GET /api/violations?limit=500&status=active — dashboard e tela de violações.
exports.getViolations = async (req, res) => {
  const requested = req.query.limit === undefined ? DEFAULT_LIMIT : parseId(req.query.limit, 'limit');
  const limit = Math.min(requested, MAX_LIMIT);

  const params = [limit];
  let where = '';
  if (req.query.status !== undefined) {
    if (!STATUSES.includes(req.query.status)) {
      throw new HttpError(400, `status inválido. Use: ${STATUSES.join(', ')}.`);
    }
    params.push(req.query.status);
    where = 'WHERE COALESCE(i.status_resolucao, \'active\') = $2';
  }

  const result = await db.query(
    `SELECT
        i.id_infracao AS id,
        i.id_dispositivo,
        COALESCE(a.nome_area, 'Zona Geral') AS zone,
        i.tipo_epi_ausente AS type,
        COALESCE(i.severidade, 'high') AS severity,
        COALESCE(i.status_resolucao, 'active') AS status,
        i.score_confianca AS confidence,
        i.timestamp_deteccao AS detected_at,
        i.imagem_url
     FROM infracao i
     LEFT JOIN dispositivo_borda d ON i.id_dispositivo = d.id_dispositivo
     LEFT JOIN area a ON d.id_area = a.id_area
     ${where}
     ORDER BY i.timestamp_deteccao DESC
     LIMIT $1`,
    params
  );

  // Registros antigos podem ter "Capacete"/"Colete"; o dashboard sempre recebe o código canônico.
  const data = result.rows.map((row) => ({ ...row, type: normalizeEpiType(row.type) }));
  res.status(200).json({ data });
};

// PATCH /api/violations/:id — Ativa -> Reconhecida -> Resolvida.
exports.updateStatus = async (req, res) => {
  const id = parseId(req.params.id);
  const { status } = req.body || {};

  if (!STATUSES.includes(status)) {
    throw new HttpError(400, `status inválido. Use: ${STATUSES.join(', ')}.`);
  }

  const result = await db.query(
    `UPDATE infracao
        SET status_resolucao = $1
      WHERE id_infracao = $2
      RETURNING id_infracao, status_resolucao`,
    [status, id]
  );

  if (result.rows.length === 0) {
    throw new HttpError(404, 'Infração não encontrada.');
  }

  res.status(200).json({ message: 'Status atualizado com sucesso', data: result.rows[0] });
};
