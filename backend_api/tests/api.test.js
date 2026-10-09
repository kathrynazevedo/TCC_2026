// Testes de integração da API. Usam Postgres em memória (pg-mem) e um Cloudinary falso,
// então não precisam de .env, internet nem do banco real.
const { test, before, after, beforeEach } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

process.env.NODE_ENV = 'test';
process.env.EDGE_API_KEY = 'chave-de-teste';
process.env.EDGE_OFFLINE_AFTER_SECONDS = '90';

const { newDb } = require('pg-mem');

const mem = newDb();
const { Pool } = mem.adapters.createPg();
const pool = new Pool();

const uploads = [];
const deletions = [];
const fakeStorage = {
  uploadEvidence: async () => {
    uploads.push(Date.now());
    return { url: `https://img.test/evidencia-${uploads.length}.jpg`, publicId: `evidencia-${uploads.length}` };
  },
  deleteEvidence: async (publicId) => {
    deletions.push(publicId);
  },
};

function mockModule(relativePath, exports) {
  const resolved = require.resolve(relativePath);
  require.cache[resolved] = { id: resolved, filename: resolved, loaded: true, exports };
}
mockModule('../src/config/db', pool);
mockModule('../src/services/imageStorage', fakeStorage);

const createApp = require('../src/app');

let server;
let base;
const AUTH = { 'x-api-key': 'chave-de-teste' };

const api = async (method, url, { body, headers = {}, form } = {}) => {
  const init = { method, headers: { ...headers } };
  if (form) {
    init.body = form;
  } else if (body !== undefined) {
    init.headers['content-type'] = 'application/json';
    init.body = JSON.stringify(body);
  }
  const res = await fetch(`${base}${url}`, init);
  const text = await res.text();
  let json = null;
  try {
    json = JSON.parse(text);
  } catch {
    /* resposta sem JSON */
  }
  return { status: res.status, json };
};

const violationForm = (fields = {}, { file = true, mime = 'image/jpeg' } = {}) => {
  const form = new FormData();
  const values = { id_dispositivo: '1', tipo_epi_ausente: 'no-helmet', confidence: '0.91', severity: 'high', ...fields };
  for (const [key, value] of Object.entries(values)) {
    if (value !== undefined) form.append(key, value);
  }
  if (file) form.append('image', new Blob([Buffer.from('fake-jpeg-bytes')], { type: mime }), 'infracao.jpg');
  return form;
};

before(async () => {
  await pool.query(fs.readFileSync(path.join(__dirname, '../db/schema.sql'), 'utf8'));
  server = createApp().listen(0);
  await new Promise((resolve) => server.once('listening', resolve));
  base = `http://127.0.0.1:${server.address().port}`;
});

after(async () => {
  await new Promise((resolve) => server.close(resolve));
});

beforeEach(async () => {
  await pool.query('DELETE FROM infracao');
  await pool.query('DELETE FROM trabalhador');
  await pool.query('DELETE FROM dispositivo_borda');
  await pool.query('DELETE FROM area');
  await pool.query("INSERT INTO area (id_area, nome_area, descricao) VALUES (1, 'Zona Norte', 'Frente norte'), (2, 'Almoxarifado', NULL)");
  await pool.query("INSERT INTO dispositivo_borda (id_dispositivo, numero_serie, id_area) VALUES (1, 'RPI-001', 1)");
  await pool.query("INSERT INTO trabalhador (nome, cargo, status, zona) VALUES ('Zé', 'Pedreiro', 'Ativo', 'Zona Norte')");
  uploads.length = 0;
  deletions.length = 0;
});

// ---------- saúde e roteamento ----------

test('GET /api/health informa que API e banco estão no ar', async () => {
  const { status, json } = await api('GET', '/api/health');
  assert.equal(status, 200);
  assert.equal(json.database, 'up');
});

test('rota inexistente em /api devolve 404 em JSON', async () => {
  const { status, json } = await api('GET', '/api/nao-existe');
  assert.equal(status, 404);
  assert.ok(json.error);
});

// ---------- POST /api/violations (Raspberry Pi) ----------

test('POST /violations sem chave de API é recusado e nada é enviado ao Cloudinary', async () => {
  const { status } = await api('POST', '/api/violations', { form: violationForm() });
  assert.equal(status, 401);
  assert.equal(uploads.length, 0);
});

test('POST /violations válido grava a infração com o código canônico do EPI', async () => {
  const { status, json } = await api('POST', '/api/violations', {
    headers: AUTH,
    form: violationForm({ tipo_epi_ausente: 'Capacete' }), // apelido antigo da placa
  });
  assert.equal(status, 201);
  assert.equal(json.data.tipo_epi_ausente, 'no-helmet');
  assert.equal(uploads.length, 1);

  const { rows } = await pool.query('SELECT * FROM infracao');
  assert.equal(rows.length, 1);
  assert.equal(rows[0].tipo_epi_ausente, 'no-helmet');
  assert.equal(rows[0].status_resolucao, 'active');
  assert.equal(rows[0].imagem_url, 'https://img.test/evidencia-1.jpg');
});

test('POST /violations rejeita dados inválidos sem tocar no Cloudinary', async () => {
  const cases = [
    ['sem imagem', violationForm({}, { file: false }), 400],
    ['tipo desconhecido', violationForm({ tipo_epi_ausente: 'oculos' }), 400],
    ['confiança fora do intervalo', violationForm({ confidence: '1.7' }), 400],
    ['confiança ausente', violationForm({ confidence: undefined }), 400],
    ['severidade inválida', violationForm({ severity: 'urgentissima' }), 400],
    ['dispositivo inválido', violationForm({ id_dispositivo: 'abc' }), 400],
    ['dispositivo inexistente', violationForm({ id_dispositivo: '99' }), 404],
    ['arquivo que não é imagem', violationForm({}, { mime: 'text/html' }), 400],
  ];
  for (const [nome, form, esperado] of cases) {
    const { status } = await api('POST', '/api/violations', { headers: AUTH, form });
    assert.equal(status, esperado, nome);
  }
  assert.equal(uploads.length, 0);
  const { rows } = await pool.query('SELECT COUNT(*)::int AS n FROM infracao');
  assert.equal(rows[0].n, 0);
});

test('POST /violations remove a imagem do Cloudinary se o banco falhar', async () => {
  const original = pool.query.bind(pool);
  pool.query = (sql, ...rest) =>
    typeof sql === 'string' && sql.includes('INSERT INTO infracao') ? Promise.reject(new Error('banco caiu')) : original(sql, ...rest);
  try {
    const { status } = await api('POST', '/api/violations', { headers: AUTH, form: violationForm() });
    assert.equal(status, 500);
    assert.deepEqual(deletions, ['evidencia-1']);
  } finally {
    pool.query = original;
  }
});

test('POST /violations com timestamp no futuro é limitado ao horário do servidor', async () => {
  const futuro = new Date(Date.now() + 3600 * 1000).toISOString();
  const { status } = await api('POST', '/api/violations', { headers: AUTH, form: violationForm({ timestamp: futuro }) });
  assert.equal(status, 201);
  const { rows } = await pool.query('SELECT timestamp_deteccao FROM infracao');
  assert.ok(new Date(rows[0].timestamp_deteccao) <= new Date());
});

// ---------- GET/PATCH /api/violations (dashboard) ----------

const insertViolation = (tipo, status, minutosAtras = 0) =>
  pool.query(
    `INSERT INTO infracao (id_dispositivo, tipo_epi_ausente, score_confianca, timestamp_deteccao, imagem_url, status_resolucao, severidade)
     VALUES (1, $1, 0.9, $2, 'https://img.test/x.jpg', $3, 'high')`,
    [tipo, new Date(Date.now() - minutosAtras * 60000), status]
  );

test('GET /violations devolve mais recentes primeiro, com zona e tipo normalizado', async () => {
  await insertViolation('Colete', 'active', 10); // registro legado
  await insertViolation('no-helmet', 'resolved', 1);
  const { status, json } = await api('GET', '/api/violations');
  assert.equal(status, 200);
  assert.deepEqual(json.data.map((v) => v.type), ['no-helmet', 'no-vest']);
  assert.equal(json.data[0].zone, 'Zona Norte');
});

test('GET /violations aceita filtro de status e limite, e valida os parâmetros', async () => {
  await insertViolation('no-vest', 'active', 3);
  await insertViolation('no-vest', 'resolved', 2);
  await insertViolation('no-helmet', 'active', 1);

  const ativas = await api('GET', '/api/violations?status=active');
  assert.equal(ativas.json.data.length, 2);

  const limitado = await api('GET', '/api/violations?limit=1');
  assert.equal(limitado.json.data.length, 1);

  assert.equal((await api('GET', '/api/violations?status=qualquer')).status, 400);
  assert.equal((await api('GET', '/api/violations?limit=-5')).status, 400);
});

test('PATCH /violations/:id altera o status e valida entrada', async () => {
  await insertViolation('no-helmet', 'active');
  const { rows } = await pool.query('SELECT id_infracao FROM infracao');
  const id = rows[0].id_infracao;

  const ok = await api('PATCH', `/api/violations/${id}`, { body: { status: 'acknowledged' } });
  assert.equal(ok.status, 200);
  assert.equal(ok.json.data.status_resolucao, 'acknowledged');

  assert.equal((await api('PATCH', `/api/violations/${id}`, { body: { status: 'apagada' } })).status, 400);
  assert.equal((await api('PATCH', `/api/violations/${id}`, { body: {} })).status, 400);
  assert.equal((await api('PATCH', '/api/violations/abc', { body: { status: 'resolved' } })).status, 400);
  assert.equal((await api('PATCH', '/api/violations/9999', { body: { status: 'resolved' } })).status, 404);
});

test('JSON malformado devolve 400 (não 500)', async () => {
  const res = await fetch(`${base}/api/violations/1`, {
    method: 'PATCH',
    headers: { 'content-type': 'application/json' },
    body: '{quebrado',
  });
  assert.equal(res.status, 400);
});

// ---------- métricas, áreas, equipe ----------

test('GET /metrics calcula totais e taxa de segurança', async () => {
  await insertViolation('no-helmet', 'active');
  await insertViolation('no-vest', 'resolved');
  await insertViolation('no-vest', 'resolved');
  await insertViolation('no-vest', 'acknowledged');
  const { json } = await api('GET', '/api/metrics');
  assert.deepEqual(json, { total_eventos: 4, nao_conformidades: 1, taxa_seguranca: 75, total_cameras: 1 });
});

test('GET /metrics sem infrações indica 100% de segurança', async () => {
  const { json } = await api('GET', '/api/metrics');
  assert.equal(json.taxa_seguranca, 100);
});

test('GET /areas agrupa dispositivos por área e informa se estão online', async () => {
  await pool.query('UPDATE dispositivo_borda SET ultima_atividade = NOW() WHERE id_dispositivo = 1');
  const { json } = await api('GET', '/api/areas');
  assert.equal(json.data.length, 2);
  assert.equal(json.data[0].dispositivos.length, 1);
  assert.equal(json.data[0].dispositivos[0].online, true);
  assert.deepEqual(json.data[1].dispositivos, []); // área sem câmera
});

test('GET /workers lista a equipe', async () => {
  const { json } = await api('GET', '/api/workers');
  assert.equal(json.data[0].name, 'Zé');
});

// ---------- heartbeat e status da borda ----------

test('heartbeat exige chave, valida o dispositivo e deixa a placa online', async () => {
  assert.equal((await api('POST', '/api/status/heartbeat', { body: { id_dispositivo: 1 } })).status, 401);
  assert.equal((await api('POST', '/api/status/heartbeat', { headers: AUTH, body: {} })).status, 400);
  assert.equal((await api('POST', '/api/status/heartbeat', { headers: AUTH, body: { id_dispositivo: 77 } })).status, 404);

  assert.equal((await api('POST', '/api/status/heartbeat', { headers: AUTH, body: { id_dispositivo: 1 } })).status, 200);
  const { json } = await api('GET', '/api/status/edge');
  assert.equal(json.online, true);
  assert.ok(json.segundos_inativo <= 5);
});

test('GET /status/edge marca offline sem heartbeat recente e quando nunca houve', async () => {
  const nunca = await api('GET', '/api/status/edge');
  assert.equal(nunca.json.online, false);

  await pool.query("UPDATE dispositivo_borda SET ultima_atividade = NOW() - INTERVAL '10 minutes' WHERE id_dispositivo = 1");
  const velho = await api('GET', '/api/status/edge');
  assert.equal(velho.json.online, false);
  assert.ok(velho.json.segundos_inativo >= 590);
});
