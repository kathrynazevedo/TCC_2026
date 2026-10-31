"""Teste de bancada da sirene, com o pino e o nível do .env (os mesmos que o sistema usa em operação).

    python3 testar_sirene.py            # repouso 3 s -> sirene 3 s -> repouso 3 s
    python3 testar_sirene.py --segundos 5

Confira de ouvido: a sirene deve ficar CALADA nas fases de repouso e TOCAR só na fase "ACIONADA".
Se acontecer o contrário, o nível está invertido: coloque SIRENE_ATIVA_EM=alto (ou baixo) no .env e repita.
"""
import argparse
import sys
import time

import config
from sirene import Sirene


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--segundos", type=float, default=3.0, help="duração de cada fase (padrão 3)")
    args = p.parse_args()

    sirene = Sirene(config.PINO_SIRENE, args.segundos, ativa_em_baixo=config.SIRENE_ATIVA_EM_BAIXO)
    if not sirene.preparar():
        print("[ERRO] RPi.GPIO indisponível (este teste só faz sentido na Raspberry Pi).")
        return 1

    nivel = "BAIXO" if config.SIRENE_ATIVA_EM_BAIXO else "ALTO"
    print(f"Pino físico {config.PINO_SIRENE} | o relé liga em nível {nivel} (SIRENE_ATIVA_EM do .env)\n")
    try:
        print(f"1) REPOUSO por {args.segundos:g}s: a sirene deve estar CALADA...")
        time.sleep(args.segundos)
        print(f"2) ACIONADA por {args.segundos:g}s: a sirene deve TOCAR...")
        sirene.tocar()
        print(f"3) REPOUSO por {args.segundos:g}s: a sirene deve voltar a ficar CALADA...")
        time.sleep(args.segundos)
        print("4) O programa vai terminar AGORA. Observe por uns 10 s: a sirene deve CONTINUAR calada.")
    except KeyboardInterrupt:
        print("\n(interrompido)")
    finally:
        sirene.encerrar()
    print("\nTeste finalizado. Anote em que passo a sirene tocou (deve ser só o 2) e se ela ligou DEPOIS do fim do programa.")
    print("  - tocou nos passos 1 e 3 e calou no 2: nível invertido -> SIRENE_ATIVA_EM=alto no .env")
    print("  - ligou só depois que o programa terminou: o pino ficou solto -> resistor de pull-up (ver README)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
