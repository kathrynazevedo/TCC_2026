#!/bin/bash
echo "Atualizando pacotes do sistema da Raspberry Pi..."
sudo apt-get update

echo "Instalando dependências do projeto..."
pip3 install -r requirements.txt

echo "Ambiente pronto para rodar!"