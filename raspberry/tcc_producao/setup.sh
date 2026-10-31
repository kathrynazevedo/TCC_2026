#!/bin/bash
# Prepara a Raspberry Pi do zero: cria um ambiente virtual e instala as dependências.
# (Se o Python do sistema já tem ultralytics, opencv, requests e python-dotenv, este script pode ser pulado.)
set -euo pipefail
cd "$(dirname "$0")"

echo "Atualizando pacotes do sistema..."
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip libgl1 libglib2.0-0

echo "Criando ambiente virtual (.venv)..."
# --system-site-packages: o ambiente enxerga o RPi.GPIO instalado pelo sistema (sem ele a sirene ficaria só simulada)
python3 -m venv --system-site-packages .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Arquivo .env criado. EDITE-O com o endereço da API, a EDGE_API_KEY e a câmera antes de iniciar."
fi

echo
echo "Conferindo o GPIO da sirene..."
if .venv/bin/python -c "import RPi.GPIO" 2>/dev/null; then
  echo "  RPi.GPIO encontrado."
else
  echo "  AVISO: RPi.GPIO não encontrado; a sirene ficaria só simulada. Instale com:"
  echo "    sudo apt-get install -y python3-rpi-lgpio"
fi

echo
echo "Ambiente pronto. Próximos passos:"
echo "  nano .env                          (API, chave e câmera)"
echo "  .venv/bin/python teste_conexao.py  (confere rede, API e chave)"
echo "  .venv/bin/python testar_sirene.py  (confere o relé de ouvido)"
echo "  bash instalar_servico.sh           (o programa sobe sozinho ao ligar a placa)"
