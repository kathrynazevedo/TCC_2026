#!/bin/bash
# Prepara a Raspberry Pi: cria um ambiente virtual e instala as dependências.
set -euo pipefail
cd "$(dirname "$0")"

echo "Atualizando pacotes do sistema..."
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip libgl1 libglib2.0-0

echo "Criando ambiente virtual (.venv)..."
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Arquivo .env criado. EDITE-O com o IP do servidor e a EDGE_API_KEY antes de iniciar."
fi

echo
echo "Ambiente pronto. Para testar a conexão e iniciar:"
echo "  .venv/bin/python teste_conexao.py"
echo "  .venv/bin/python main.py"
