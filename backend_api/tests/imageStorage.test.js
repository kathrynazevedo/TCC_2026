const { test } = require('node:test');
const assert = require('node:assert/strict');

process.env.NODE_ENV = 'test';
const { publicIdFromUrl } = require('../src/services/imageStorage');

test('publicIdFromUrl extrai o public_id só de imagens da pasta do projeto', () => {
  assert.equal(
    publicIdFromUrl('https://res.cloudinary.com/demo/image/upload/v1712345678/tcc_infracoes_epi/abc123.jpg'),
    'tcc_infracoes_epi/abc123'
  );
  assert.equal(publicIdFromUrl('https://res.cloudinary.com/demo/image/upload/tcc_infracoes_epi/abc123.png'), 'tcc_infracoes_epi/abc123');

  // fora da pasta do projeto, ou sem ser URL do Cloudinary: nunca apaga
  assert.equal(publicIdFromUrl('https://res.cloudinary.com/demo/image/upload/v1/outra_pasta/abc.jpg'), null);
  assert.equal(publicIdFromUrl('https://img.test/x.jpg'), null);
  assert.equal(publicIdFromUrl(null), null);
});
