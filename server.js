import express from 'express';
import cors from 'cors';
import sqlite3 from 'sqlite3';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import multer from 'multer';
import fs from 'fs';

// 1. INICIALIZAÇÃO CORRETA DAS VARIÁVEIS DE CAMINHO (ESM)
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();
const port = 3000;

// Configurações de segurança e recebimento de dados
app.use(cors());
app.use(express.json());

// 2. CRIAÇÃO DA PASTA DE UPLOADS DE FORMA SEGURA
const uploadDir = join(__dirname, 'uploads');
if (!fs.existsSync(uploadDir)) {
    fs.mkdirSync(uploadDir);
}

// Configuração do Multer para salvar as imagens vindas da Raspberry Pi
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    cb(null, file.originalname);
  }
});
const upload = multer({ storage });

// 3. LIBERA A PASTA DE UPLOADS PARA O FRONT-END ACESSAR VIA HTTP
app.use('/uploads', express.static(uploadDir));

// Conecta ao banco de dados SQLite local
const dbPath = join(__dirname, 'database.sqlite');
const db = new sqlite3.Database(dbPath, (err) => {
    if (err) console.error('Erro ao conectar no banco:', err);
    else console.log('Conectado ao banco SQLite com sucesso!');
});

// ==========================================
// ROTAS DA API
// ==========================================

// Rota para buscar todas as infrações
app.get('/api/violations', (req, res) => {
    db.all('SELECT * FROM violations ORDER BY detected_at DESC', [], (err, rows) => {
        if (err) return res.status(500).json({ error: err.message });
        res.json({ data: rows });
    });
});

// Rota para a Raspberry Pi enviar o alerta e a foto
app.post('/api/alertas', upload.single('imagem'), (req, res) => {
    const { zone, type, severity, confidence, detected_at } = req.body;
    const caminho_imagem = req.file ? `http://localhost:3000/uploads/${req.file.filename}` : null;

    const sql = `INSERT INTO violations (zone, type, severity, confidence, detected_at, caminho_imagem, status) 
                 VALUES (?, ?, ?, ?, ?, ?, 'active')`;
    
    db.run(sql, [zone, type, severity, confidence, detected_at, caminho_imagem], function(err) {
        if (err) return res.status(500).json({ error: err.message });
        res.status(201).json({ message: "Alerta salvo com sucesso!", id: this.lastID });
    });
});

// Rota para atualizar o status da infração (Reconhecer/Resolver)
app.patch('/api/violations/:id', (req, res) => {
    const { status } = req.body;
    const { id } = req.params;
    
    db.run('UPDATE violations SET status = ? WHERE id = ?', [status, id], function(err) {
        if (err) return res.status(500).json({ error: err.message });
        res.json({ message: "Status atualizado com sucesso", id });
    });
});

// Inicia o servidor
app.listen(port, () => {
    console.log(`🚀 Servidor SafeWork rodando na porta http://localhost:${port}`);
});