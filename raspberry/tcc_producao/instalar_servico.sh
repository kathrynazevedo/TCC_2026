#!/bin/bash
# Instala o monitoramento como serviço do sistema: sobe sozinho ao ligar a placa e volta se cair.
#
#   ./instalar_servico.sh              instala e inicia
#   ./instalar_servico.sh --mostrar    só mostra o serviço que seria criado (não altera nada)
#   ./instalar_servico.sh --remover    desliga e remove o serviço
#
# Depois de instalado:  journalctl -u tcc-epi -f   (ver o que o programa escreve)
#                       sudo systemctl stop tcc-epi   (parar para testar na mão: câmera e sirene ficam livres)
set -euo pipefail
cd "$(dirname "$0")"

PASTA="$(pwd)"
NOME="tcc-epi"
DESTINO="/etc/systemd/system/$NOME.service"
USUARIO="${SUDO_USER:-$(id -un)}"
if [ -x "$PASTA/.venv/bin/python" ]; then
  PYTHON="$PASTA/.venv/bin/python"
else
  PYTHON="$(command -v python3 || command -v python || true)"
fi

unidade() {
  sed -e "s|__USUARIO__|$USUARIO|g" -e "s|__PASTA__|$PASTA|g" -e "s|__PYTHON__|$PYTHON|g" "$NOME.service.modelo"
}

case "${1:-}" in
  --mostrar)
    unidade
    exit 0
    ;;
  --remover)
    sudo systemctl disable --now "$NOME" 2>/dev/null || true
    sudo rm -f "$DESTINO"
    sudo systemctl daemon-reload
    echo "Serviço $NOME removido."
    exit 0
    ;;
  "") ;;
  *)
    echo "Uso: $0 [--mostrar | --remover]"
    exit 1
    ;;
esac

[ -n "$PYTHON" ] || { echo "ERRO: Python 3 não encontrado."; exit 1; }
[ -f .env ] || { echo "ERRO: falta o .env. Faça: cp .env.example .env  e preencha (API, chave, câmera)."; exit 1; }

echo "Python do serviço: $PYTHON (usuário: $USUARIO)"
"$PYTHON" -c "import ultralytics, cv2, requests, dotenv" 2>/dev/null || {
  echo "ERRO: faltam pacotes neste Python (ultralytics, opencv, requests, python-dotenv). Veja o README ou rode ./setup.sh"
  exit 1
}

echo "Conferindo o modelo (leva alguns segundos)..."
if ! SAIDA="$("$PYTHON" testar_modelo.py --so-classes 2>&1)"; then
  echo "$SAIDA" | tail -6
  echo "ERRO: o modelo não serve ao sistema; o serviço não foi instalado."
  exit 1
fi
echo "$SAIDA" | grep "RESULTADO"

if systemctl is-active --quiet "$NOME" 2>/dev/null; then
  echo "O serviço já está instalado: vou atualizá-lo e reiniciá-lo."
fi
if pgrep -f "python.* main.py" >/dev/null 2>&1 && ! systemctl is-active --quiet "$NOME" 2>/dev/null; then
  echo "AVISO: há um main.py rodando na mão. Pare-o (Ctrl+C) para o serviço poder usar a câmera e a sirene."
fi

unidade | sudo tee "$DESTINO" >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable "$NOME"
sudo systemctl restart "$NOME"

echo
echo "Serviço $NOME instalado e iniciado. Ele sobe sozinho sempre que a placa ligar."
echo "  ver o que acontece:  journalctl -u $NOME -f"
echo "  estado:              systemctl status $NOME"
echo "  parar para testar:   sudo systemctl stop $NOME"
echo
echo "Sirene: o programa já segura o relé em repouso ao terminar. Para ela também não tocar durante a PARTIDA da placa,"
echo "veja no README a linha 'gpio=17=ip,pn' do config.txt (ou um resistor/diodo)."
