const pool = require('../config/db');

// Função 1: Chamada pelo Frontend (React) para atualizar o painel
const getEdgeStatus = async (req, res) => {
    try {
        // Consulta o dispositivo de borda mais recente/ativo no banco
        const query = `
            SELECT id_dispositivo, numero_serie, ultima_atividade 
            FROM dispositivo_borda 
            ORDER BY ultima_atividade DESC 
            LIMIT 1;
        `;
        const result = await pool.query(query);

        if (result.rows.length === 0) {
            return res.status(200).json({ online: false, time: 0 });
        }

        const dispositivo = result.rows[0];
        const agora = new Date();
        const ultimaAtividade = new Date(dispositivo.ultima_atividade);
        
        // Considera online se a última atividade ocorreu nos últimos 60 segundos
        const diffSegundos = (agora - ultimaAtividade) / 1000;
        const isOnline = diffSegundos <= 60;

        res.status(200).json({ 
            online: isOnline, 
            time: Math.round(diffSegundos * 1000), // Latência simulada
            detalhes: dispositivo
        });
    } catch (error) {
        console.error('Erro ao verificar status da edge:', error);
        res.status(500).json({ online: false, error: 'Erro interno ao verificar status' });
    }
};

// Função 2: Chamada pelo Raspberry Pi (Python) a cada X segundos
const edgeHeartbeat = async (req, res) => {
    try {
        const { id_dispositivo } = req.body;
        
        if (!id_dispositivo) {
            return res.status(400).json({ error: 'ID do dispositivo não fornecido' });
        }

        // Atualiza a coluna ultima_atividade com o horário atual do servidor (NOW())
        const query = `
            UPDATE dispositivo_borda 
            SET ultima_atividade = NOW() 
            WHERE id_dispositivo = $1
            RETURNING id_dispositivo, ultima_atividade;
        `;
        
        const result = await pool.query(query, [id_dispositivo]);

        if (result.rows.length === 0) {
             return res.status(404).json({ error: 'Dispositivo não encontrado no banco' });
        }

        res.status(200).json({ message: 'Heartbeat registrado com sucesso' });
    } catch (error) {
        console.error('Erro no heartbeat da edge:', error);
        res.status(500).json({ error: 'Erro ao registrar heartbeat' });
    }
};

module.exports = { getEdgeStatus, edgeHeartbeat };