const cloudinary = require('cloudinary').v2;
require('dotenv').config(); // Adicione isso para garantir que o .env seja lido aqui também

// Configuração explícita usando as variáveis separadas
cloudinary.config({
  cloud_name: process.env.CLOUDINARY_CLOUD_NAME,
  api_key: process.env.CLOUDINARY_API_KEY,
  api_secret: process.env.CLOUDINARY_API_SECRET,
  secure: true 
});
module.exports = cloudinary;