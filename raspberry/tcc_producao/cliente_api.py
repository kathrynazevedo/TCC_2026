"""Comunicação com o backend: infrações, heartbeat e fila offline de pendências."""
import json
import threading
from datetime import datetime, timezone

import requests

import config

OK = "ok"
RETENTAR = "retentar"    # falha temporária (rede fora, servidor com problema): guardar e tentar depois
DESCARTAR = "descartar"  # a API recusou o conteúdo (4xx): reenviar não adianta

_trava_pendentes = threading.Lock()


def _cabecalhos():
    return {"x-api-key": config.EDGE_API_KEY} if config.EDGE_API_KEY else {}


def agora_utc():
    """Timestamp ISO-8601 em UTC (com fuso), para a API não depender do relógio/fuso do servidor."""
    return datetime.now(timezone.utc).isoformat()


def enviar_infracao(jpeg, tipo, confianca, timestamp):
    """Envia uma infração. Devolve OK, RETENTAR ou DESCARTAR."""
    dados = {
        "id_dispositivo": config.ID_DISPOSITIVO,
        "tipo_epi_ausente": tipo,
        "severity": "high",
        "confidence": f"{confianca:.4f}",
        "timestamp": timestamp,
    }
    try:
        resposta = requests.post(
            config.URL_INFRACOES,
            data=dados,
            files={"image": ("infracao.jpg", jpeg, "image/jpeg")},
            headers=_cabecalhos(),
            timeout=20,  # inclui o upload da imagem para o Cloudinary
        )
    except requests.RequestException as erro:
        print(f"[REDE] Sem conexão com a API ({erro.__class__.__name__}).")
        return RETENTAR

    if resposta.status_code == 201:
        return OK
    if resposta.status_code == 401:
        print("[REDE] API recusou a chave (EDGE_API_KEY). Corrija o .env; o alerta ficará pendente.")
        return RETENTAR
    if resposta.status_code in (400, 404, 413, 422):
        print(f"[REDE] API recusou o alerta ({resposta.status_code}): {resposta.text[:200]}")
        return DESCARTAR
    print(f"[REDE] Erro temporário da API ({resposta.status_code}).")
    return RETENTAR


def enviar_heartbeat():
    """True se a API confirmou que a placa está viva."""
    try:
        resposta = requests.post(
            config.URL_HEARTBEAT,
            json={"id_dispositivo": config.ID_DISPOSITIVO},
            headers=_cabecalhos(),
            timeout=5,
        )
        return resposta.status_code == 200
    except requests.RequestException:
        return False


def processar_alerta(jpeg, tipo, confianca):
    """Envia o alerta; se não for possível, guarda em disco para sincronizar depois."""
    timestamp = agora_utc()
    resultado = enviar_infracao(jpeg, tipo, confianca, timestamp)
    if resultado == OK:
        print(f"[REDE] Alerta '{tipo}' enviado com sucesso.")
    elif resultado == RETENTAR:
        salvar_pendente(jpeg, tipo, confianca, timestamp)
    return resultado


# --------------------------------------------------------------------------
# Fila offline
# --------------------------------------------------------------------------
def salvar_pendente(jpeg, tipo, confianca, timestamp):
    with _trava_pendentes:
        config.PASTA_PENDENTES.mkdir(parents=True, exist_ok=True)
        base = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        (config.PASTA_PENDENTES / f"{base}.jpg").write_bytes(jpeg)
        meta = {"tipo": tipo, "confianca": confianca, "timestamp": timestamp}
        (config.PASTA_PENDENTES / f"{base}.json").write_text(json.dumps(meta), encoding="utf-8")
        _limitar_pendentes()
    print(f"[OFFLINE] Alerta '{tipo}' guardado para envio posterior.")


def _limitar_pendentes():
    """Mantém só as MAX_PENDENTES mais recentes (descarta as mais antigas)."""
    fotos = sorted(config.PASTA_PENDENTES.glob("*.jpg"))
    for foto in fotos[: max(0, len(fotos) - config.MAX_PENDENTES)]:
        foto.unlink(missing_ok=True)
        foto.with_suffix(".json").unlink(missing_ok=True)


def sincronizar_pendentes():
    """Reenvia os alertas guardados. Devolve (enviados, restantes)."""
    enviados = 0
    with _trava_pendentes:
        if not config.PASTA_PENDENTES.exists():
            return 0, 0
        fotos = sorted(config.PASTA_PENDENTES.glob("*.jpg"))
        restantes = len(fotos)
        if fotos:
            print(f"[SYNC] {len(fotos)} alerta(s) pendente(s). Reenviando...")

        for foto in fotos:
            meta_arquivo = foto.with_suffix(".json")
            try:
                meta = json.loads(meta_arquivo.read_text(encoding="utf-8"))
                tipo, confianca, timestamp = meta["tipo"], float(meta["confianca"]), meta["timestamp"]
            except (OSError, ValueError, KeyError):
                print(f"[SYNC] Metadados inválidos em {foto.name}; removendo.")
                foto.unlink(missing_ok=True)
                meta_arquivo.unlink(missing_ok=True)
                restantes -= 1
                continue

            resultado = enviar_infracao(foto.read_bytes(), tipo, confianca, timestamp)
            if resultado == RETENTAR:
                break  # servidor fora do ar: não adianta insistir nos demais agora
            foto.unlink(missing_ok=True)
            meta_arquivo.unlink(missing_ok=True)
            restantes -= 1
            if resultado == OK:
                enviados += 1

    return enviados, restantes
