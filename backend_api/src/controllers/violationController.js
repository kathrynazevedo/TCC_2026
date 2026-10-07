const cloudinary = require('../config/cloudinary');
const db = require('../config/db'); // Pool de conexão com o PostgreSQL (Neon)

// Função 1: Registrar a infração vinda da Raspberry Pi (Já estava pronta)
exports.registrarInfracao = async (req, res) => {
    try {
        const { id_dispositivo, tipo_epi_ausente, timestamp, confidence, severity } = req.body;
        const file = req.file;
        
        if (!file) {
            return res.status(400).json({ error: 'Nenhuma imagem de infração foi enviada.' });
        }

        // Upload da evidência para o Cloudinary
        const base64Image = `data:${file.mimetype};base64,${file.buffer.toString('base64')}`;
        const uploadResult = await cloudinary.uploader.upload(base64Image, {
            folder: 'tcc_infracoes_epi',
        });
        const imageUrl = uploadResult.secure_url;

        const sql = `
            INSERT INTO infracao 
            (id_dispositivo, tipo_epi_ausente, score_confianca, timestamp_deteccao, imagem_url, sincronizado_nuvem, status_resolucao, severidade) 
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id_infracao;
        `;
                 
        const dataInfracao = timestamp ? new Date(timestamp) : new Date();
        const score_confianca = confidence || 0.95;
        const severidadeVal = severity || 'high';

        const values = [
            id_dispositivo || 1,
            tipo_epi_ausente, 
            score_confianca, 
            dataInfracao, 
            imageUrl, 
            true, 
            'active',
            severidadeVal
        ];

        const result = await db.query(sql, values);
        const insertId = result.rows[0].id_infracao;

        return res.status(201).json({
            message: 'Infração registrada com sucesso no sistema!',
            data: {
                id_infracao: insertId,
                id_dispositivo: values[0],
                tipo_epi_ausente: values[1],
                image_url: imageUrl,
                timestamp: dataInfracao
            }
        });
    } catch (error) {
        console.error("Erro ao registrar infração:", error);
        return res.status(500).json({ error: 'Erro interno no servidor ao processar o alerta.' });
    }
};

// Função 2: Buscar infrações para o Dashboard e Tela de Violações
exports.getViolations = async (req, res) => {
    try {
        const query = `
            SELECT 
                i.id_infracao AS id,
                i.id_dispositivo,
                COALESCE(a.nome_area, 'Zona Geral') AS zone,
                i.tipo_epi_ausente AS type,
                COALESCE(i.severidade, 'high') AS severity,
                COALESCE(i.status_resolucao, 'active') AS status,
                i.timestamp_deteccao AS detected_at,
                i.imagem_url
            FROM infracao i
            LEFT JOIN dispositivo_borda d ON i.id_dispositivo = d.id_dispositivo
            LEFT JOIN area a ON d.id_area = a.id_area
            ORDER BY i.timestamp_deteccao DESC;
        `;
        
        const result = await db.query(query);
        res.status(200).json({ data: result.rows });
    } catch (error) {
        console.error("Erro ao buscar infrações:", error);
        res.status(500).json({ error: 'Erro ao buscar infrações do banco de dados' });
    }
};

// Função 3: Atualizar status da infração (Ativa -> Reconhecida -> Resolvida)
exports.updateStatus = async (req, res) => {
    try {
        const { id } = req.params;
        const { status } = req.body; // Espera 'active', 'acknowledged' ou 'resolved'

        const query = `
            UPDATE infracao 
            SET status_resolucao = $1 
            WHERE id_infracao = $2 
            RETURNING id_infracao, status_resolucao;
        `;
        
        const result = await db.query(query, [status, id]);

        if (result.rows.length === 0) {
            return res.status(404).json({ error: 'Infração não encontrada.' });
        }

        res.status(200).json({ 
            message: "Status atualizado com sucesso", 
            data: result.rows[0] 
        });
    } catch (error) {
        console.error("Erro ao atualizar status da infração:", error);
        res.status(500).json({ error: 'Erro ao atualizar status no banco de dados' });
    }
};