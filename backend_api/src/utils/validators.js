const HttpError = require('./httpError');

const SEVERITIES = ['low', 'medium', 'high', 'critical'];
const STATUSES = ['active', 'acknowledged', 'resolved'];

// Códigos canônicos usados em todo o sistema (placa, banco e dashboard).
const EPI_ALIASES = {
  'no-helmet': 'no-helmet',
  'sem_capacete': 'no-helmet',
  'sem-capacete': 'no-helmet',
  'capacete': 'no-helmet',
  'no-vest': 'no-vest',
  'sem_colete': 'no-vest',
  'sem-colete': 'no-vest',
  'colete': 'no-vest',
};

// Aceita apelidos antigos ("Capacete", "Colete"); valores desconhecidos voltam como estão.
function normalizeEpiType(value) {
  if (typeof value !== 'string') return value;
  return EPI_ALIASES[value.trim().toLowerCase()] || value;
}

function isKnownEpiType(value) {
  return typeof value === 'string' && Object.values(EPI_ALIASES).includes(normalizeEpiType(value));
}

function parseId(value, label = 'id') {
  const text = String(value ?? '').trim();
  if (!/^\d+$/.test(text)) {
    throw new HttpError(400, `${label} inválido.`);
  }
  const id = Number(text);
  if (!Number.isSafeInteger(id) || id < 1 || id > 2147483647) {
    throw new HttpError(400, `${label} inválido.`);
  }
  return id;
}

function parseConfidence(value) {
  const number = Number(value);
  if (value === undefined || value === null || value === '' || !Number.isFinite(number) || number < 0 || number > 1) {
    throw new HttpError(400, 'confidence deve ser um número entre 0 e 1.');
  }
  return number;
}

// Sem timestamp (ou inválido) usa o horário do servidor, que é a fonte confiável.
function parseTimestamp(value) {
  if (!value) return new Date();
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return new Date();
  // Relógio da placa adiantado não pode gerar infrações "no futuro".
  return date > new Date() ? new Date() : date;
}

module.exports = {
  SEVERITIES,
  STATUSES,
  normalizeEpiType,
  isKnownEpiType,
  parseId,
  parseConfidence,
  parseTimestamp,
};
