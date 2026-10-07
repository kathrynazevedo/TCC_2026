import requests
import sys

API_URL = "http://192.168.0.101:3000/api/alertas"

print(f"[REDE] Testando conectividade com a API: {API_URL}")


try:
    # Remove a rota final para testar a raiz do servidor ou faz um head/get rápido
    url_base = API_URL.rsplit('/', 2)[0] #Pega o IP e a porta
    response = requests.get(API_URL, timeout=5)

    print(f"[REDE] Conexão bem-sucedida! Status Code: {response.status_code}")
    print("[SISTEMA] O programa principal pode prosseguir")

except requests.exceptions.RequestException as e:
    print(f"[ERRO CRÍTICO] falha ao conectar com o servidor: {e}")
    print("[SISTEMA] Programa encerrado por falha de conectividade.")
    sys.exit(1)
