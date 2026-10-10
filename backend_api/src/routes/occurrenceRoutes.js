const express = require('express');
const upload = require('../middlewares/uploadMiddleware');
const edgeAuth = require('../middlewares/edgeAuth');
const occurrenceController = require('../controllers/occurrenceController');

const router = express.Router();

// A autenticação vem antes do multer: requisição sem chave nem chega a ser carregada em memória.
router.post('/', edgeAuth, upload.single('image'), occurrenceController.registrarOcorrencia);

module.exports = router;
