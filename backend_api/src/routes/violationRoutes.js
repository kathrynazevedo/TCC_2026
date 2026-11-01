const express = require('express');
const violationController = require('../controllers/violationController');

const router = express.Router();

router.get('/', violationController.getViolations);
router.patch('/:id', violationController.updateStatus);
// Exclusão em lote; exige a senha no corpo da requisição (conferida no controller).
router.delete('/', violationController.deleteViolations);

module.exports = router;
