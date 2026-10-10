"""Comunicação com o backend: infrações, heartbeat e fila offline de pendências."""
import itertools
import json
import threading
from datetime import datetime, timezone

import requests

import config

OK = "ok"
RETENTAR = "retentar"    # falha temporária (rede fora, servidor com problema): guardar e tentar depois
DESCARTAR = "descartar"  # a API recusou o conteúdo (4xx): reenviar não adianta

_trava_pendentes = threading.Lock()
_sequencia = itertools.count()  # desempata alertas salvos no mesmo instante (o relógio do Windows tem baixa resolução)


def _cabecalhos():
    return {"x-api-key": config.EDGE_API_KEY} if config.EDGE_API_KEY else {}


def agora_utc():
    """Timestamp ISO-8601 em UTC (com fuso), para a API não depender do relógio/fuso do servidor."""
    return datetime.now(timezone.utc).isoformat()


def _resultado(resposta):
    """Traduz a resposta da API em OK, RETENTAR ou DESCARTAR (e explica o motivo no terminal)."""
    if resposta.status_code == 201:
        return OK
    if resposta.status_code == 401:
        print("[REDE] API recusou a chave (EDGE_API_KEY). Corrija o .env; o alerta ficará pendente.")
        return RETENTAR
    if resposta.status_code == 404 and "Rota não encontrada" in resposta.text:
        # Servidor ainda sem a rota (placa atualizada antes da API): guardar, não perder o alerta.
        print("[REDE] A API ainda não tem esta rota (servidor desatualizado?); o alerta ficará pendente.")
        return RETENTAR
    if resposta.status_code in (400, 404, 413, 422):
        print(f"[REDE] API recusou o alerta ({resposta.status_code}): {resposta.text[:200]}")
        return DESCARTAR
    print(f"[REDE] Erro temporário da API ({resposta.status_code}): {resposta.text[:200]}")
    return RETENTAR


def _post(url, nome_arquivo, jpeg, **dados):
    """POST multipart com a foto. Devolve OK, RETENTAR ou DESCARTAR."""
    try:
        resposta = requests.post(
            url,
            files={"image": (nome_arquivo, jpeg, "image/jpeg")},
            headers=_cabecalhos(),
            timeout=20,  # inclui o upload da imagem para o Cloudinary
            **dados,
        )
    except requests.RequestException as erro:
        print(f"[REDE] Sem conexão com a API ({erro.__class__.__name__}).")
        return RETENTAR
    return _resultado(resposta)


def enviar_infracao(jpeg, tipo, confianca, timestamp):
    """Envia uma infração isolada (formato antigo; ainda usado para reenviar pendências gravadas por ele)."""
    dados = {
        "id_dispositivo": config.ID_DISPOSITIVO,
        "tipo_epi_ausente": tipo,
        "severity": "high",
        "confidence": f"{confianca:.4f}",
        "timestamp": timestamp,
    }
    return _post(config.URL_INFRACOES, "infracao.jpg", jpeg, data=dados)


def enviar_ocorrencia(jpeg, ocorrencia):
    """Envia a cena inteira (foto + pessoas + EPIs) numa única requisição. Devolve OK, RETENTAR ou DESCARTAR."""
    return _post(config.URL_OCORRENCIAS, "ocorrencia.jpg", jpeg, data={"occurrence": json.dumps(ocorrencia)})


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


def processar_ocorrencia(jpeg, ocorrencia):
    """Envia a cena inteira; se não for possível, guarda em disco (foto + JSON) para sincronizar depois."""
    resultado = enviar_ocorrencia(jpeg, ocorrencia)
    novos = sum(1 for p in ocorrencia["pessoas"] for epi in ("capacete", "colete") if p[epi]["novo"])
    if resultado == OK:
        print(f"[REDE] Ocorrência enviada com sucesso ({len(ocorrencia['pessoas'])} pessoa(s), {novos} infração(ões) nova(s)).")
    elif resultado == RETENTAR:
        salvar_pendente_ocorrencia(jpeg, ocorrencia)
    return resultado


# --------------------------------------------------------------------------
# Fila offline
# --------------------------------------------------------------------------
def _gravar_pendente(jpeg, meta):
    with _trava_pendentes:
        config.PASTA_PENDENTES.mkdir(parents=True, exist_ok=True)
        base = f"{datetime.now(timezone.utc):%Y%m%d_%H%M%S_%f}_{next(_sequencia):04d}"
        (config.PASTA_PENDENTES / f"{base}.jpg").write_bytes(jpeg)
        (config.PASTA_PENDENTES / f"{base}.json").write_text(json.dumps(meta), encoding="utf-8")
        _limitar_pendentes()


def salvar_pendente_ocorrencia(jpeg, ocorrencia):
    """Guarda a cena inteira; o JSON da ocorrência vai junto, com o horário original da detecção."""
    _gravar_pendente(jpeg, {"ocorrencia": ocorrencia})
    print("[OFFLINE] Ocorrência guardada para envio posterior.")


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
                if "ocorrencia" in meta:  # cena inteira
                    if not isinstance(meta["ocorrencia"], dict):
                        raise ValueError("ocorrencia não é um objeto")
                    envio = (enviar_ocorrencia, (meta["ocorrencia"],))
                else:  # infração isolada, gravada por versões anteriores
                    envio = (enviar_infracao, (meta["tipo"], float(meta["confianca"]), meta["timestamp"]))
            except (OSError, ValueError, KeyError, TypeError):
                print(f"[SYNC] Metadados inválidos em {foto.name}; removendo.")
                foto.unlink(missing_ok=True)
                meta_arquivo.unlink(missing_ok=True)
                restantes -= 1
                continue

            funcao, argumentos = envio
            resultado = funcao(foto.read_bytes(), *argumentos)
            if resultado == RETENTAR:
                break  # servidor fora do ar: não adianta insistir nos demais agora
            foto.unlink(missing_ok=True)
            meta_arquivo.unlink(missing_ok=True)
            restantes -= 1
            if resultado == OK:
                enviados += 1

    return enviados, restantes
