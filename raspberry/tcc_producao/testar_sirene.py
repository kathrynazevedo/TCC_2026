"""Teste de bancada da sirene, com o pino e o nível do .env (os mesmos que o sistema usa em operação).

    python3 testar_sirene.py            # desligada 3 s -> ligada 3 s -> desligada 3 s
    python3 testar_sirene.py --segundos 5

Confira de ouvido: a sirene deve ficar CALADA nas fases de repouso e TOCAR SEM PARAR só na fase "LIGADA", e continuar
CALADA depois que o programa termina (também se você apertar Ctrl+C no meio do toque).
Se tocar nas fases de repouso e calar na "LIGADA", o nível está invertido: SIRENE_ATIVA_EM=alto (ou baixo) no .env.
Se ela NÃO calar nas fases de repouso, o módulo talvez precise do pino solto: confira SIRENE_DESLIGA_SOLTANDO=true.
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

    sirene = Sirene(config.PINO_SIRENE, config.SIRENE_DESLIGA_APOS, ativa_em_baixo=config.SIRENE_ATIVA_EM_BAIXO,
                    desliga_soltando=config.SIRENE_DESLIGA_SOLTANDO)
    if not sirene.preparar():
        print("[ERRO] RPi.GPIO indisponível (este teste só faz sentido na Raspberry Pi).")
        return 1

    nivel = "BAIXO" if config.SIRENE_ATIVA_EM_BAIXO else "ALTO"
    desliga = "soltando o pino" if config.SIRENE_DESLIGA_SOLTANDO else "conduzindo o nível de repouso"
    print(f"Pino físico {config.PINO_SIRENE} (GPIO{sirene.pino_bcm}) | liga em nível {nivel} e desliga {desliga}\n")
    try:
        print(f"1) DESLIGADA por {args.segundos:g}s: a sirene deve estar CALADA...")
        time.sleep(args.segundos)
        print(f"2) LIGADA por {args.segundos:g}s: a sirene deve TOCAR sem parar...")
        sirene.ligar()
        time.sleep(args.segundos)
        print(f"3) DESLIGADA por {args.segundos:g}s: a sirene deve voltar a ficar CALADA...")
        sirene.desligar()
        time.sleep(args.segundos)
        print("4) O programa vai terminar AGORA. Observe por uns 10 s: a sirene deve CONTINUAR calada.")
    except KeyboardInterrupt:
        print("\n(interrompido)")
    finally:
        sirene.encerrar()

    esperado = "ip" if config.SIRENE_DESLIGA_SOLTANDO else ("op dh" if config.SIRENE_ATIVA_EM_BAIXO else "op dl")
    print("\nTeste finalizado. Anote em que passo a sirene tocou (deve ser só o 2) e se ela ligou DEPOIS do fim do programa.")
    print("  - tocou nos passos 1 e 3 e calou no 2: nível invertido -> SIRENE_ATIVA_EM=alto (ou baixo) no .env")
    print(f"  - o estado desligado fica segurado pelo `pinctrl`. Para conferir, rode: pinctrl get {sirene.pino_bcm}")
    print(f"    deve mostrar \"{esperado}\" logo depois do número do pino. Se a sirene tocar mesmo assim, veja a seção da "
          "sirene no README.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
