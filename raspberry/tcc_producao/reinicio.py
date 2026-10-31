"""Reinício programado do turno: depois de N horas de operação o programa (ou a placa) reinicia sozinho.

Serve para começar cada turno "limpo" (memória, câmera, conexões) e aparece na tela Sistema como o próximo reinício
programado. Fica DESLIGADO com REINICIAR_APOS_HORAS=0.

Dois modos (REINICIO_MODO no .env):
  programa  reabre só o main.py no mesmo processo (os.execv); funciona em qualquer instalação e é o padrão.
  placa     `sudo reboot`: reinicia a Raspberry inteira. Só faz sentido se o programa sobe sozinho no boot (serviço
            systemd); do contrário a placa volta e o monitoramento não. Se o reboot falhar, cai no modo programa.
"""
import os
import subprocess
import sys


def reinicio_devido(ligado_s, apos_horas, ninguem_em_cena, tolerancia_s=600):
    """True quando já passou o tempo programado E é um bom momento.

    Bom momento = ninguém em cena (não interrompe a vigilância de quem está sendo julgado) ou a tolerância se esgotou
    (um canteiro sempre movimentado não pode adiar o reinício para sempre).
    """
    if not apos_horas or apos_horas <= 0:
        return False
    atraso = ligado_s - apos_horas * 3600
    if atraso < 0:
        return False
    return bool(ninguem_em_cena) or atraso >= tolerancia_s


def segundos_para_reinicio(ligado_s, apos_horas):
    """Quanto falta (s) para o reinício programado, ou None se estiver desligado."""
    if not apos_horas or apos_horas <= 0:
        return None
    return max(0.0, apos_horas * 3600 - ligado_s)


def executar_reinicio(modo, executar=os.execv, rodar=subprocess.run):
    """Reinicia conforme o modo. Só volta (retorna False) se não conseguiu reiniciar; `executar`/`rodar` são injetáveis."""
    if modo == "placa":
        print("[REINÍCIO] Reiniciando a placa (sudo reboot)...", flush=True)
        try:
            rodar(["sudo", "-n", "reboot"], check=True, timeout=30)
            return True
        except (OSError, subprocess.SubprocessError) as erro:
            print(f"[REINÍCIO] Não foi possível reiniciar a placa ({erro}); reiniciando só o programa.", flush=True)
    print("[REINÍCIO] Reiniciando o programa...", flush=True)
    try:
        executar(sys.executable, [sys.executable] + sys.argv)
    except OSError as erro:
        print(f"[ERRO] Não foi possível reiniciar o programa: {erro}", flush=True)
        return False
    return True
