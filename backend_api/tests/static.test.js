// O backend serve o build do React (monolito). Cobre o fallback do React Router.
const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

// Pasta com ponto no caminho (como ".claude" ou ".config"): o sendFile puro recusaria o arquivo.
const dist = fs.mkdtempSync(path.join(os.tmpdir(), '.dist-'));
fs.writeFileSync(path.join(dist, 'index.html'), '<!doctype html><title>SafeWork</title>');
fs.mkdirSync(path.join(dist, 'assets'));
fs.writeFileSync(path.join(dist, 'assets', 'app.js'), 'console.log(1)');
process.env.FRONTEND_DIST = dist;
process.env.NODE_ENV = 'test';

const mockModule = (relativePath, exports) => {
  const resolved = require.resolve(relativePath);
  require.cache[resolved] = { id: resolved, filename: resolved, loaded: true, exports };
};
mockModule('../src/config/db', { query: async () => ({ rows: [] }) });
mockModule('../src/services/imageStorage', {});

let server;
let base;

before(async () => {
  server = require('../src/app')().listen(0);
  await new Promise((resolve) => server.once('listening', resolve));
  base = `http://127.0.0.1:${server.address().port}`;
});

after(async () => {
  await new Promise((resolve) => server.close(resolve));
  fs.rmSync(dist, { recursive: true, force: true });
});

test('rotas do React (ex.: /violations) devolvem o index.html', async () => {
  for (const route of ['/', '/violations', '/zones']) {
    const res = await fetch(base + route);
    assert.equal(res.status, 200, route);
    assert.match(await res.text(), /SafeWork/);
  }
});

test('arquivos estáticos são servidos normalmente', async () => {
  const res = await fetch(`${base}/assets/app.js`);
  assert.equal(res.status, 200);
  assert.equal(await res.text(), 'console.log(1)');
});

test('/api inexistente continua devolvendo 404 em JSON, não o index.html', async () => {
  const res = await fetch(`${base}/api/nada`);
  assert.equal(res.status, 404);
  assert.ok((await res.json()).error);
});
