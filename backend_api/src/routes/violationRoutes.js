const express = require('express');
const router = express.Router();
const violationController = require('../controllers/violationController');

// Define as rotas (O prefixo /api/violations será definido no server.js)
router.get('/', violationController.getViolations);
router.patch('/:id', violationController.updateStatus);

module.exports = router;