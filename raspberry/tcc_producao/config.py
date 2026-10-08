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
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:3000").rstrip("/")
EDGE_API_KEY = os.getenv("EDGE_API_KEY", "")
ID_DISPOSITIVO = _int("ID_DISPOSITIVO", 1)  # id em dispositivo_borda, no banco
URL_INFRACOES = f"{API_BASE_URL}/api/violations"
URL_HEARTBEAT = f"{API_BASE_URL}/api/status/heartbeat"
URL_HEALTH = f"{API_BASE_URL}/api/health"

# --- Câmera e modelo ---
CAMERA_SOURCE = _fonte_camera()
MODELO_PATH = os.getenv("MODELO_PATH", str(BASE_DIR / "best.tflite"))
CONFIANCA_MINIMA = _float("CONFIANCA_MINIMA", 0.70)
LARGURA_FRAME, ALTURA_FRAME = 640, 480
MOSTRAR_JANELA = os.getenv("MOSTRAR_JANELA", "false").lower() == "true"  # só para depuração com monitor

# --- Regras de alerta ---
TEMPO_DEBOUNCE = _float("TEMPO_DEBOUNCE", 10.0)  # segundos entre alertas do mesmo tipo
PINO_SIRENE = _int("PINO_SIRENE", 18)
DURACAO_SIRENE = _float("DURACAO_SIRENE", 2.0)
INTERVALO_HEARTBEAT = _float("INTERVALO_HEARTBEAT", 30.0)

# --- Modo offline: alertas que não chegaram à API ficam aqui até a sincronização ---
PASTA_PENDENTES = Path(os.getenv("PASTA_PENDENTES", str(BASE_DIR / "pendentes")))
MAX_PENDENTES = _int("MAX_PENDENTES", 200)  # protege o cartão SD
INTERVALO_SINCRONIZACAO = _float("INTERVALO_SINCRONIZACAO", 60.0)
