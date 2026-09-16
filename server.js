import express from 'express';
import cors from 'cors';
import sqlite3 from 'sqlite3';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();
const port = 3000;

// Configurações de segurança e recebimento de dados
app.use(cors());
app.use(express.json());

// Conecta ao banco de dados SQLite local
const dbPath = join(__dirname, 'database.sqlite');
const db = new sqlite3.Database(dbPath, (err) => {
    if (err) console.error('Erro ao conectar no banco:', err);
    else console.log('Conectado ao banco SQLite com sucesso!');
});

// ==========================================
// ROTAS DA API
// ==========================================

// Rota para buscar todas as infrações (Teste H3)
app.get('/api/violations', (req, res) => {
    // Busca do mais recente para o mais antigo
    db.all('SELECT * FROM violations ORDER BY detected_at DESC', [], (err, rows) => {
        if (err) return res.status(500).json({ error: err.message });
        res.json({ data: rows });
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