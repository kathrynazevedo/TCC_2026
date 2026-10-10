const HttpError = require('./httpError');

const SEVERITIES = ['low', 'medium', 'high', 'critical'];
const STATUSES = ['active', 'acknowledged', 'resolved'];

// Códigos canônicos usados em todo o sistema (placa, banco e dashboard).
// 'no-helmet-no-vest' = a mesma pessoa/quadro sem capacete E sem colete (um único registro, não dois).
const EPI_ALIASES = {
  'no-helmet-no-vest': 'no-helmet-no-vest',
  'sem_capacete_colete': 'no-helmet-no-vest',
  'sem-capacete-colete': 'no-helmet-no-vest',
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

// ---------- ocorrência (cena inteira enviada pela placa) ----------

const EPI_STATES = ['ok', 'ausente', 'desconhecido'];
const MAX_PEOPLE = 50;
// Chave do JSON da placa -> código canônico da infração.
const EPI_KEYS = { capacete: 'no-helmet', colete: 'no-vest' };
const BOTH_TYPE = 'no-helmet-no-vest'; // mesma pessoa sem capacete e sem colete: um registro só

function parseBox(value, label) {
  if (value === undefined || value === null) return null;
  if (!Array.isArray(value) || value.length !== 4 || !value.every((n) => Number.isFinite(n))) {
    throw new HttpError(400, `${label} deve ser [x1, y1, x2, y2].`);
  }
  return value.map((n) => Math.round(n));
}

// { estado, confianca, novo } de um EPI de uma pessoa. Ausente do JSON = "desconhecido" (não detectado).
function parseEpiState(value, label) {
  if (value === undefined || value === null) return { estado: 'desconhecido', confianca: null, novo: false };
  if (typeof value !== 'object' || Array.isArray(value)) {
    throw new HttpError(400, `${label} inválido.`);
  }
  if (!EPI_STATES.includes(value.estado)) {
    throw new HttpError(400, `${label}.estado inválido. Use: ${EPI_STATES.join(', ')}.`);
  }
  const confianca =
    value.confianca === undefined || value.confianca === null ? null : parseConfidence(value.confianca);
  const novo = value.novo === true;
  if (novo && (value.estado !== 'ausente' || confianca === null)) {
    throw new HttpError(400, `${label}: "novo" exige estado "ausente" e confianca.`);
  }
  return { estado: value.estado, confianca, novo };
}

/**
 * Valida a ocorrência enviada pela placa (campo "occurrence" do multipart, em JSON) e a normaliza:
 *   { id_dispositivo, timestamp, severity, total_pessoas, pessoas: [{ numero, caixa, capacete, colete }] }
 * Devolve também `infracoes`: o que deve virar registro em "infracao" (EPI "ausente" marcado como "novo"),
 * já com capacete + colete da mesma pessoa fundidos em um único registro 'no-helmet-no-vest'.
 */
function parseOccurrence(raw) {
  let data = raw;
  if (typeof raw === 'string') {
    try {
      data = JSON.parse(raw);
    } catch {
      throw new HttpError(400, 'occurrence não é um JSON válido.');
    }
  }
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    throw new HttpError(400, 'occurrence é obrigatório (JSON com a cena detectada).');
  }

  const idDispositivo = parseId(data.id_dispositivo, 'id_dispositivo');
  const severity = data.severity || 'high';
  if (!SEVERITIES.includes(severity)) {
    throw new HttpError(400, `severity inválida. Use: ${SEVERITIES.join(', ')}.`);
  }

  if (!Array.isArray(data.pessoas) || data.pessoas.length === 0 || data.pessoas.length > MAX_PEOPLE) {
    throw new HttpError(400, `pessoas deve ser uma lista de 1 a ${MAX_PEOPLE} itens.`);
  }

  const seen = new Set();
  const pessoas = [];
  const infracoes = [];
  for (const [index, item] of data.pessoas.entries()) {
    const label = `pessoas[${index}]`;
    if (!item || typeof item !== 'object' || Array.isArray(item)) {
      throw new HttpError(400, `${label} inválido.`);
    }
    const numero = parseId(item.numero, `${label}.numero`);
    if (seen.has(numero)) {
      throw new HttpError(400, `${label}.numero repetido (${numero}).`);
    }
    seen.add(numero);

    const pessoa = { numero, caixa: parseBox(item.caixa, `${label}.caixa`) };
    for (const [key, tipo] of Object.entries(EPI_KEYS)) {
      const epi = parseEpiState(item[key], `${label}.${key}`);
      pessoa[key] = epi;
      if (epi.novo) infracoes.push({ tipo, numero, confianca: epi.confianca });
    }
    pessoas.push(pessoa);
  }

  if (infracoes.length === 0) {
    throw new HttpError(400, 'A ocorrência não traz nenhum EPI ausente marcado como novo.');
  }

  // A MESMA pessoa sem capacete E sem colete na mesma captura vira um registro só ("ambos"), não dois; a
  // confiança do registro combinado é a menor das duas (as duas ausências precisam ser verdadeiras).
  // Pessoas diferentes (uma sem capacete, outra sem colete) continuam em registros separados.
  const registros = [];
  for (const numero of seen) {
    const dela = infracoes.filter((infracao) => infracao.numero === numero);
    const capacete = dela.find((infracao) => infracao.tipo === EPI_KEYS.capacete);
    const colete = dela.find((infracao) => infracao.tipo === EPI_KEYS.colete);
    if (capacete && colete) {
      registros.push({
        tipo: BOTH_TYPE,
        numero,
        confianca: Math.min(capacete.confianca, colete.confianca),
      });
    } else {
      registros.push(...dela);
    }
  }

  const total =
    data.total_pessoas === undefined || data.total_pessoas === null
      ? pessoas.length
      : parseId(data.total_pessoas, 'total_pessoas');
  if (total < pessoas.length) {
    throw new HttpError(400, 'total_pessoas não pode ser menor que a quantidade de pessoas listadas.');
  }

  return {
    id_dispositivo: idDispositivo,
    timestamp: parseTimestamp(data.timestamp),
    severity,
    total_pessoas: total,
    pessoas,
    infracoes: registros,
  };
}

module.exports = {
  SEVERITIES,
  STATUSES,
  EPI_STATES,
  normalizeEpiType,
  isKnownEpiType,
  parseId,
  parseConfidence,
  parseTimestamp,
  parseOccurrence,
};
