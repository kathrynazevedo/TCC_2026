const pool = require('../config/db');
const cloudinary = require('../config/cloudinary');

const criarAlerta = async (req, res) => {
  try {
    // A placa manda os nomes em inglês, nós pegamos aqui:
    const { type, confidence, detected_at } = req.body;
    let imagem_url = null;

    // 1. Verifica se a IA enviou uma foto e sobe pro Cloudinary
    if (req.file) {
      const b64 = Buffer.from(req.file.buffer).toString('base64');
      const dataURI = "data:" + req.file.mimetype + ";base64," + b64;
      
      const uploadResponse = await cloudinary.uploader.upload(dataURI, {
        folder: 'safework_tcc'
      });
      imagem_url = uploadResponse.secure_url;
    }

    // 2. Salva no banco de dados Neon na tabela correta ("infracao")
    const sql = `
      INSERT INTO infracao 
      (id_dispositivo, tipo_epi_ausente, score_confianca, timestamp_deteccao, imagem_url, sincronizado_nuvem, status_resolucao) 
      VALUES ($1, $2, $3, $4, $5, $6, $7)
      RETURNING *
    `;
    
    // Forçamos o id_dispositivo = 1 (RPI4-001) para este protótipo
    const idDispositivo = 1;
    const dataDetectada = detected_at || new Date();
    
    const valores = [
      idDispositivo, 
      type, 
      confidence, 
      dataDetectada, 
      imagem_url, 
      true, // sincronizado_nuvem
      'active' // status_resolucao
    ];
    
    const result = await pool.query(sql, valores);

    // 3. Responde para a placa
    res.status(201).json({ 
      message: "Alerta salvo com sucesso na Nuvem!", 
      data: result.rows[0] 
    });

  } catch (error) {
    console.error("Erro ao processar o alerta da IA:", error);
    res.status(500).json({ error: 'Falha ao salvar alerta no sistema' });
  }
};

module.exports = { criarAlerta };