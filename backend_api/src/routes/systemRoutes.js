const express = require('express');
const edgeAuth = require('../middlewares/edgeAuth');
const systemController = require('../controllers/systemController');

const router = express.Router();

// Consumida pelo React: GET /api/status/edge
router.get('/edge', systemController.getEdgeStatus);

// Consumida pela Raspberry Pi: POST /api/status/heartbeat
router.post('/heartbeat', edgeAuth, systemController.edgeHeartbeat);

module.exports = router;
