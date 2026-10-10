"""Configurações da Raspberry Pi. Tudo pode ser sobrescrito por variáveis de ambiente ou pelo arquivo .env."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:  # python-dotenv é opcional; sem ele valem apenas as variáveis do sistema
    pass


def _float(nome, padrao):
    try:
        return float(os.getenv(nome, padrao))
    except ValueError:
        return float(padrao)


def _int(nome, padrao):
    try:
        return int(os.getenv(nome, padrao))
    except ValueError:
        return int(padrao)


def _fonte_camera():
    """CAMERA_SOURCE pode ser o índice de uma webcam ("0") ou uma URL RTSP."""
    valor = os.getenv("CAMERA_SOURCE", "0").strip()
    return int(valor) if valor.isdigit() else valor


# --- API (backend Node.js) ---
API_BASE_URL = os.getenv("API_BASE_URL", "https://tcc-2026-mfxn.onrender.com").rstrip("/")
EDGE_API_KEY = os.getenv("EDGE_API_KEY", "")  # sem valor padrão: a chave vem do .env, nunca do código
ID_DISPOSITIVO = _int("ID_DISPOSITIVO", 1)  # id em dispositivo_borda, no banco
URL_INFRACOES = f"{API_BASE_URL}/api/violations"  # uma infração isolada (formato antigo)
URL_OCORRENCIAS = f"{API_BASE_URL}/api/occurrences"  # a cena inteira: foto + todas as pessoas e seus EPIs
URL_HEARTBEAT = f"{API_BASE_URL}/api/status/heartbeat"
URL_HEALTH = f"{API_BASE_URL}/api/health"

# --- Câmera e modelo ---
CAMERA_SOURCE = _fonte_camera()
MODELO_PATH = os.getenv("MODELO_PATH", str(BASE_DIR / "best.tflite"))
CONFIANCA_MINIMA = _float("CONFIANCA_MINIMA", 0.70)
LARGURA_FRAME, ALTURA_FRAME = 640, 480
MOSTRAR_JANELA = os.getenv("MOSTRAR_JANELA", "false").lower() == "true"  # só para depuração com monitor

# --- Regras de alerta ---
TEMPO_REALERTA = _float("TEMPO_REALERTA", 0.0)  # s para repetir o alerta de quem segue sem EPI (0 = um só por permanência)
RASTREADOR_TEMPO_AUSENTE = _float("RASTREADOR_TEMPO_AUSENTE", 10.0)  # s sem ver a pessoa antes de "esquecê-la"
RASTREADOR_TEMPO_PRESENTE = _float("RASTREADOR_TEMPO_PRESENTE", 3.0)  # s sem aparecer até sair da contagem de "em cena"
RASTREADOR_DIST_MAXIMA = _int("RASTREADOR_DIST_MAXIMA", 150)  # px (frame 640x480) para ser a mesma pessoa
PINO_SIRENE = _int("PINO_SIRENE", 18)
DURACAO_SIRENE = _float("DURACAO_SIRENE", 2.0)
INTERVALO_HEARTBEAT = _float("INTERVALO_HEARTBEAT", 30.0)

# --- Modo offline: alertas que não chegaram à API ficam aqui até a sincronização ---
PASTA_PENDENTES = Path(os.getenv("PASTA_PENDENTES", str(BASE_DIR / "pendentes")))
MAX_PENDENTES = _int("MAX_PENDENTES", 200)  # protege o cartão SD
INTERVALO_SINCRONIZACAO = _float("INTERVALO_SINCRONIZACAO", 60.0)
