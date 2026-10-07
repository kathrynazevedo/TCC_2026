const express = require('express');
const router = express.Router();
const systemController = require('../controllers/systemController');

// Rota consumida pelo React (GET http://localhost:3000/api/status/edge)
router.get('/edge', systemController.getEdgeStatus);

// Rota consumida pela Raspberry Pi (POST http://localhost:3000/api/status/heartbeat)
router.post('/heartbeat', systemController.edgeHeartbeat);

module.exports = router;