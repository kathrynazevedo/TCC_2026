import os
import glob
import requests
from datetime import datetime

API_URL = "http://192.168.0.101:3000/api/alertas"


fotos_pendentes = glob.glob("*jpg")

if not fotos_pendentes:
    print("Nenhuma oto encontrada na raspberry")
else:
    print("Iniciando envio de {len(foto_pendentes)} evidências para o servidor...")

    for  foto in fotos_pendentes:
         timestamp_formatado = datetime.now().isoformat()

         dados = {
             'zone': 'Zona Norte',
	     'type': 'no-helmet',
	     'severity': 'high',
	     'confidence': '0.85',
	     'detected_at': timestamp_formatado
	 }

         try:
              with open(foto, 'rb') as f:
                files = {'imagem': (foto, f, 'image/jpg')}
                resposta = requests.post(API_URL, data=dados, files=files, timeout=5)

              if resposta.status_code == 201:
                print(f"{foto} sincronizada com sucesso!")

              else:
                print(f" Erro ao sinconizar {foto}: {resposta.text}")
         except Exception as e:
                print(f"SERVIDOR NÃO ENCONTRADO Erro: {e}")
