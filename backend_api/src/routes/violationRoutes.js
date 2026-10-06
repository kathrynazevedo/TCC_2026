const express = require('express');
const router = express.Router();
const upload = require('../middlewares/uploadMiddleware');
const violationController = require('../controllers/violationController');

// Define as rotas (O prefixo /api/violations será definido no server.js)
router.get('/', violationController.getViolations);
router.patch('/:id', violationController.updateStatus);
router.post('/', upload.single('image'), violationController.registrarInfracao);

module.exports = router;