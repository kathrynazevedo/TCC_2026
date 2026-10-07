const express = require('express');
const router = express.Router();
const workersController = require('../controllers/workersController');

router.get('/', workersController.getWorkers);

module.exports = router;