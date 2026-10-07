const multer = require('multer');

// Usa a memória RAM temporariamente para segurar o arquivo
const storage = multer.memoryStorage();

// Configura o multer para aceitar apenas um arquivo por vez
const upload = multer({ storage: storage });

module.exports = upload;