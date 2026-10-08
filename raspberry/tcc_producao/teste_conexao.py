"""Diagnóstico rápido: a Raspberry alcança a API e a chave está correta?"""
import sys

import requests

import cliente_api
import config

print(f"[REDE] Testando a API em {config.API_BASE_URL}")

try:
    saude = requests.get(config.URL_HEALTH, timeout=5)
    print(f"[REDE] /api/health -> {saude.status_code} {saude.text}")
except requests.RequestException as erro:
    print(f"[ERRO] Não foi possível conectar: {erro}")
    sys.exit(1)

if saude.status_code != 200:
    print("[ERRO] A API respondeu, mas o banco de dados está indisponível.")
    sys.exit(1)

if cliente_api.enviar_heartbeat():
    print(f"[OK] Heartbeat aceito para o dispositivo {config.ID_DISPOSITIVO}. Tudo pronto.")
else:
    print("[ERRO] Heartbeat recusado: confira EDGE_API_KEY e ID_DISPOSITIVO (o dispositivo precisa existir no banco).")
    sys.exit(1)
