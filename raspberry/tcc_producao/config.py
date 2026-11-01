"""Configurações da Raspberry Pi. Tudo pode ser sobrescrito por variáveis de ambiente ou pelo arquivo .env."""
import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def carregar_env(caminho):
    """Lê o .env sem sobrescrever variáveis que já existam no ambiente.

    Aceita o BOM que o Bloco de Notas do Windows grava no início do arquivo: sem isso a primeira linha vira lixo e o
    python-dotenv avisa que não consegue lê-la.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:  # python-dotenv é opcional; sem ele valem apenas as variáveis do sistema
        return False
    return load_dotenv(caminho, encoding="utf-8-sig")


carregar_env(BASE_DIR / ".env")


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


def ocultar_credenciais(fonte):
    """Troca usuário:senha de uma URL RTSP por *** para a fonte poder aparecer em mensagens e prints."""
    return re.sub(r"://[^@/]*@", "://***@", str(fonte))


def _fonte_camera(nome, padrao=None):
    """Uma câmera do .env: o índice de uma webcam ("0") ou uma URL RTSP. Vazia ou ausente = `padrao` (None = sem câmera)."""
    valor = os.getenv(nome, "").strip() or padrao
    if valor is None:
        return None
    return int(valor) if valor.isdigit() else valor


# --- API (backend Node.js) ---
API_BASE_URL = os.getenv("API_BASE_URL", "https://tcc-2026-mfxn.onrender.com").strip().rstrip("/")
EDGE_API_KEY = os.getenv("EDGE_API_KEY", "").strip()  # sem valor padrão: a chave vem do .env, nunca do código
ID_DISPOSITIVO = _int("ID_DISPOSITIVO", 1)  # id em dispositivo_borda, no banco
URL_INFRACOES = f"{API_BASE_URL}/api/violations"  # lista de infrações (a mesma do painel; o teste de conexão confere por ela)
URL_OCORRENCIAS = f"{API_BASE_URL}/api/occurrences"  # a cena inteira: foto + todas as pessoas e seus EPIs
URL_HEARTBEAT = f"{API_BASE_URL}/api/status/heartbeat"
URL_HEALTH = f"{API_BASE_URL}/api/health"
INTERVALO_HEARTBEAT = _float("INTERVALO_HEARTBEAT", 30.0)  # s entre sinais de vida (a API dá a placa como offline após 90 s)

# --- Câmera e modelo ---
CAMERA_SOURCE = _fonte_camera("CAMERA_SOURCE", "0")  # a câmera principal
# Câmera de reserva (opcional): fica em espera e só assume quando a principal passa CAMERA_TROCA_APOS s sem imagem. Só uma
# câmera é analisada por vez. Com a reserva em uso, a principal é testada a cada CAMERA_VOLTAR_A_CADA s (0 = não volta
# sozinha) e a captura volta para ela quando responde.
CAMERA_SOURCE_SECUNDARIA = _fonte_camera("CAMERA_SOURCE_SECUNDARIA")
CAMERA_TIMEOUT_S = _float("CAMERA_TIMEOUT_S", 5.0)  # prazo para abrir a câmera de rede e para ler um quadro dela
CAMERA_TROCA_APOS = _float("CAMERA_TROCA_APOS", 5.0)
CAMERA_VOLTAR_A_CADA = _float("CAMERA_VOLTAR_A_CADA", 30.0)
# Modelo de 3 classes (pessoa, capacete, colete); sem elas o programa nem inicia.
MODELO_PATH = os.getenv("MODELO_PATH", str(BASE_DIR / "modelo_pessoa_epi.tflite"))
LARGURA_FRAME, ALTURA_FRAME = 640, 480
MOSTRAR_JANELA = os.getenv("MOSTRAR_JANELA", "false").lower() == "true"  # só para depuração com monitor

# --- O que conta como detecção ---
# Abaixo disso a "pessoa" é ignorada. 0,65 separa as pessoas reais (alertas em 0,74 a 0,83 nos testes) das duvidosas que
# aparecem e somem (0,53 a 0,56). Subir reduz alarme falso, mas uma pessoa vista com pouca certeza deixa de ser julgada.
# NUNCA abaixo de 0,50: o banco da API recusa infração com confiança menor que isso.
CONFIANCA_PESSOA = _float("CONFIANCA_PESSOA", 0.65)
# Confiança mínima para aceitar um EPI como PRESENTE. Há dois erros possíveis e eles puxam em sentidos opostos:
#   - limiar BAIXO: aceita um colete/capacete duvidoso (ex.: 53% sobre uma camiseta) e deixa passar uma falta de EPI;
#   - limiar ALTO: recusa um EPI real que o modelo viu com pouca certeza e acusa quem está equipado (alarme falso).
# O colete é mais exigente porque é maior e confunde-se com roupas claras; ajuste olhando a confiança média por classe
# na tela Sistema e a curva F1 da validação. CONFIANCA_EPI, se definida, vale para os dois.
CONFIANCA_EPI = _float("CONFIANCA_EPI", 0.50)
CONFIANCA_CAPACETE = _float("CONFIANCA_CAPACETE", CONFIANCA_EPI)
CONFIANCA_COLETE = _float("CONFIANCA_COLETE", CONFIANCA_EPI if "CONFIANCA_EPI" in os.environ else 0.65)
LIMIARES_EPI = {"capacete": CONFIANCA_CAPACETE, "colete": CONFIANCA_COLETE}  # mesmas chaves de deteccao.CAPACETE/COLETE
# O modelo devolve tudo a partir do menor limiar; cada papel (pessoa, capacete, colete) é filtrado depois.
CONFIANCA_MODELO = min(CONFIANCA_PESSOA, CONFIANCA_CAPACETE, CONFIANCA_COLETE)
ALTURA_MINIMA_PESSOA = _int("ALTURA_MINIMA_PESSOA", 120)  # px (frame 640x480): pessoa menor que isso não é julgada

# --- Regras de alerta ---
TEMPO_CONFIRMACAO = _float("TEMPO_CONFIRMACAO", 1.0)  # s de falta CONTÍNUA de EPI antes de acusar (0 = 1º quadro)
TEMPO_REALERTA = _float("TEMPO_REALERTA", 0.0)  # s para repetir o alerta de quem segue sem EPI (0 = um só por permanência)
RASTREADOR_TEMPO_AUSENTE = _float("RASTREADOR_TEMPO_AUSENTE", 10.0)  # s sem ver a pessoa antes de "esquecê-la"
RASTREADOR_TEMPO_PRESENTE = _float("RASTREADOR_TEMPO_PRESENTE", 3.0)  # s sem aparecer até sair da contagem de "em cena"
RASTREADOR_DIST_MAXIMA = _int("RASTREADOR_DIST_MAXIMA", 150)  # px (frame 640x480) para ser a mesma pessoa

# --- Sirene (relé no GPIO) ---
# Pino do relé pela numeração FÍSICA da placa (modo BOARD; o pino 11 é o do teste de bancada).
PINO_SIRENE = _int("PINO_SIRENE", 11)
# Nível que LIGA o relé: "baixo" (módulos de relé comuns, acionam em LOW) ou "alto". O contrário é o repouso.
SIRENE_ATIVA_EM_BAIXO = os.getenv("SIRENE_ATIVA_EM", "baixo").strip().lower() != "alto"
# Como DESLIGAR: soltando o pino (entrada, sem pull; padrão) ou conduzindo o nível de repouso. Módulos de relé de 5 V
# comandados por um pino de 3,3 V costumam NÃO desligar com o nível alto (foi o caso da bancada): precisam do pino solto.
SIRENE_DESLIGA_SOLTANDO = os.getenv("SIRENE_DESLIGA_SOLTANDO", "true").strip().lower() != "false"
# A sirene fica LIGADA enquanto houver alguém sem EPI na cena e só cala depois de tantos segundos sem nenhuma infração (é
# também o tempo mínimo que ela toca). Tolera um quadro em que o modelo "pisca"; quem se equipa ou sai de cena deixa de contar.
SIRENE_DESLIGA_APOS = _float("SIRENE_DESLIGA_APOS", 2.0)

# --- Modo offline: alertas que não chegaram à API ficam aqui até a sincronização ---
PASTA_PENDENTES = BASE_DIR / "pendentes"
MAX_PENDENTES = _int("MAX_PENDENTES", 200)  # protege o cartão SD
INTERVALO_SINCRONIZACAO = _float("INTERVALO_SINCRONIZACAO", 60.0)

# --- Métricas: terminal, painel (tela Sistema) e registro local em CSV ---
# Os resumos fecham a cada INTERVALO_METRICAS segundos (nunca desligam: o painel depende deles; valor inválido volta a 10 s).
INTERVALO_METRICAS = _float("INTERVALO_METRICAS", 10.0)
if INTERVALO_METRICAS <= 0:
    INTERVALO_METRICAS = 10.0
ARQUIVO_METRICAS = BASE_DIR / "metricas.csv"  # rodado ao passar de 5 MB
ARQUIVO_ESTADO = BASE_DIR / "estado_execucao.json"  # conta os reinícios
# Resultado da validação do modelo (mAP por classe), gerado no Colab e mostrado na tela Sistema.
ARQUIVO_VALIDACAO = Path(os.getenv("ARQUIVO_VALIDACAO", str(BASE_DIR / "validacao_modelo.json")))

# --- Reinício programado do turno (ver reinicio.py) ---
REINICIAR_APOS_HORAS = _float("REINICIAR_APOS_HORAS", 8.0)  # h de operação até reiniciar sozinho (0 = desligado)
REINICIO_MODO = os.getenv("REINICIO_MODO", "programa").strip().lower()  # "programa" (só o main.py) ou "placa" (sudo reboot)
if REINICIO_MODO not in ("programa", "placa"):
    REINICIO_MODO = "programa"
REINICIO_TOLERANCIA_S = _float("REINICIO_TOLERANCIA_S", 600.0)  # espera por um momento sem ninguém em cena antes de forçar
