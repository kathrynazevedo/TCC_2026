const express = require('express');
const upload = require('../middlewares/uploadMiddleware');
const edgeAuth = require('../middlewares/edgeAuth');
const violationController = require('../controllers/violationController');

const router = express.Router();

router.get('/', violationController.getViolations);
router.patch('/:id', violationController.updateStatus);
// A autenticação vem antes do multer: requisição sem chave nem chega a ser carregada em memória.
router.post('/', edgeAuth, upload.single('image'), violationController.registrarInfracao);

module.exports = router;
