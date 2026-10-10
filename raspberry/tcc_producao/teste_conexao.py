"""Diagnóstico rápido: a Raspberry alcança a API e a chave está correta?

    python teste_conexao.py              confere a rede, a chave e o heartbeat
    python teste_conexao.py --infracao   além disso, envia uma infração de teste (com foto) e confere no painel

A infração de teste fica gravada no banco (confiança 0.99). Ao final o script mostra o comando para apagá-la.
"""
import sys

import requests

import cliente_api
import config


def checar_api():
    """Health check. No plano gratuito do Render o servidor 'dorme' e a primeira resposta leva cerca de 1 minuto."""
    print(f"[REDE] Testando a API em {config.API_BASE_URL} (se estiver dormindo, pode levar ~1 min)...")
    try:
        saude = requests.get(config.URL_HEALTH, timeout=90)
    except requests.RequestException as erro:
        print(f"[ERRO] Não foi possível conectar: {erro}")
        return False
    print(f"[REDE] /api/health -> {saude.status_code} {saude.text}")
    if saude.status_code != 200:
        print("[ERRO] A API respondeu, mas o banco de dados está indisponível.")
        return False
    return True


def checar_heartbeat():
    if cliente_api.enviar_heartbeat():
        print(f"[OK] Heartbeat aceito para o dispositivo {config.ID_DISPOSITIVO}.")
        return True

    print("[ERRO] Heartbeat recusado: confira EDGE_API_KEY e ID_DISPOSITIVO (o dispositivo precisa existir no banco).")
    # Repete a chamada só para mostrar o motivo devolvido pela API (a chave nunca é exibida).
    try:
        detalhe = requests.post(
            config.URL_HEARTBEAT,
            json={"id_dispositivo": config.ID_DISPOSITIVO},
            headers={"x-api-key": config.EDGE_API_KEY} if config.EDGE_API_KEY else {},
            timeout=15,
        )
    except requests.RequestException as erro:
        print(f"[DIAGNÓSTICO] Falha de rede ao repetir o heartbeat: {erro}")
        return False
    print(f"[DIAGNÓSTICO] HTTP {detalhe.status_code}: {detalhe.text[:200]}")
    if detalhe.status_code == 401:
        print("[DIAGNÓSTICO] A EDGE_API_KEY do .env é diferente da configurada no servidor.")
    elif detalhe.status_code == 404:
        print("[DIAGNÓSTICO] A chave está certa, mas o dispositivo não existe no banco (rode o seed.sql no Neon).")
    return False


def enviar_infracao_de_teste():
    """Envia uma ocorrência sintética (foto + 1 pessoa) pelo mesmo caminho do main.py e confere no painel."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        print("[ERRO] Faltam opencv-python/numpy para gerar a foto de teste: pip install -r requirements.txt")
        return False

    momento = cliente_api.agora_utc()
    frame = np.full((config.ALTURA_FRAME, config.LARGURA_FRAME, 3), 90, dtype=np.uint8)
    cv2.putText(frame, "TESTE DE INFRACAO", (40, 220), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 3)
    cv2.putText(frame, momento[:19].replace("T", " ") + " UTC", (40, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    sucesso, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not sucesso:
        print("[ERRO] Não foi possível gerar a foto de teste.")
        return False

    ocorrencia = {
        "id_dispositivo": config.ID_DISPOSITIVO,
        "timestamp": momento,
        "severity": "high",
        "total_pessoas": 1,
        "pessoas": [
            {
                "numero": 1,
                "caixa": [40, 40, 600, 440],
                "capacete": {"estado": "ausente", "confianca": 0.99, "novo": True},
                "colete": {"estado": "ok", "confianca": 0.95, "novo": False},
            }
        ],
    }
    print("[OCORRÊNCIA] Enviando ocorrência de teste (1 pessoa sem capacete, confiança 0.99) com foto...")
    if cliente_api.enviar_ocorrencia(buffer.tobytes(), ocorrencia) != cliente_api.OK:
        print("[ERRO] A API não aceitou a ocorrência de teste. Veja a mensagem [REDE] acima.")
        print("[DICA] Se o erro for 500, o schema.sql novo (tabela ocorrencia) ainda não foi aplicado no banco.")
        return False

    # Confere no mesmo endpoint que o dashboard usa: a infração mais recente deve ser a de teste.
    try:
        ultima = requests.get(f"{config.URL_INFRACOES}?limit=1", timeout=15).json()["data"][0]
    except (requests.RequestException, ValueError, KeyError, IndexError) as erro:
        print(f"[AVISO] A API aceitou o envio, mas não consegui conferir no painel: {erro}")
        return True
    print(f"[OK] Infração #{ultima['id']} registrada: {ultima['type']}, confiança {ultima['confidence']}, zona '{ultima['zone']}'.")
    print(f"[OK] Ocorrência #{ultima.get('occurrence_id')}: pessoa {ultima.get('person_number')} de {ultima.get('people_total')} em cena.")
    print(f"[OK] Foto no Cloudinary: {ultima['imagem_url']}")
    print("[LIMPEZA] Para apagar o teste (SQL Editor do Neon):")
    print(f"    DELETE FROM infracao WHERE id_ocorrencia = {ultima.get('occurrence_id')};")
    print(f"    DELETE FROM ocorrencia WHERE id_ocorrencia = {ultima.get('occurrence_id')};")
    return True


if __name__ == "__main__":
    if not (checar_api() and checar_heartbeat()):
        sys.exit(1)
    if "--infracao" in sys.argv and not enviar_infracao_de_teste():
        sys.exit(1)
    print("[OK] Tudo pronto.")
