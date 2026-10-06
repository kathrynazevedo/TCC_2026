const cloudinary = require('../config/cloudinary');
const db = require('../config/db'); // Sua conexão com o Neon (Pool do pg)

// Função 1: Registrar a infração vinda da Raspberry Pi
exports.registrarInfracao = async (req, res) => {
    try {
        // 1. Extrair os dados enviados pelo Raspberry Pi
        // (Ajustado para os nomes reais que estão na sua tabela infracao)
        const { id_dispositivo, tipo_epi_ausente, timestamp } = req.body;
        const file = req.file;

        if (!file) {
            return res.status(400).json({ error: 'Nenhuma imagem de infração foi enviada.' });
        }

        // 2. Upload para o Cloudinary
        const base64Image = `data:${file.mimetype};base64,${file.buffer.toString('base64')}`;
        const uploadResult = await cloudinary.uploader.upload(base64Image, {
            folder: 'tcc_infracoes_epi',
        });
        const imageUrl = uploadResult.secure_url;

        // 3. Preparar o INSERT no PostgreSQL (Neon)
        const sql = `
            INSERT INTO infracao 
            (id_dispositivo, tipo_epi_ausente, score_confianca, timestamp_deteccao, imagem_url, sincronizado_nuvem, status_resolucao) 
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id_infracao;
        `;
        
        const dataInfracao = timestamp ? new Date(timestamp) : new Date();
        const score_confianca = req.body.confidence || 0.95; // Valor default caso não venha
        
        const values = [
            id_dispositivo || 1, // Força 1 caso não venha
            tipo_epi_ausente, 
            score_confianca, 
            dataInfracao, 
            imageUrl, 
            true, 
            'active'
        ];

        /* --- MODO BANCO DESLIGADO / LIGADO --- 
           Descomente as 3 linhas abaixo quando for testar com o banco ligado
        */
        // const result = await db.query(sql, values);
        // const insertId = result.rows[0].id_infracao; 

        // 4. Retornar sucesso
        return res.status(201).json({
            message: 'Infração registrada com sucesso no sistema!',
            data: {
                // id_infracao: insertId, // Descomente depois
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

// Função 2: Buscar infrações para o Dashboard (Apenas placeholder por enquanto)
exports.getViolations = async (req, res) => {
    // Quando o banco voltar, faremos o SELECT aqui
    res.status(200).json({ data: [] });
};

// Função 3: Atualizar status (Apenas placeholder por enquanto)
exports.updateStatus = async (req, res) => {
    // Quando o banco voltar, faremos o UPDATE aqui
    res.status(200).json({ message: "Status atualizado" });
};