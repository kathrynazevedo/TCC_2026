"""Reenvia manualmente os alertas guardados em pendentes/ (o main.py já faz isso sozinho a cada minuto)."""
import sys

import cliente_api

if __name__ == "__main__":
    enviados, restantes = cliente_api.sincronizar_pendentes()
    print(f"Sincronização concluída: {enviados} enviado(s), {restantes} ainda pendente(s).")
    sys.exit(0 if restantes == 0 else 1)
