"""Prova de aceite do netlab.

Acceptance proof for netlab.

O criterio de aceite da especificacao tem duas partes, e este script verifica as
duas:

1. o projeto valido passa com zero erro;
2. o projeto com erros falha com pelo menos 6 erros distintos, um por regra.

A segunda parte e a que importa. Um validador que aprova tudo satisfaz a
primeira e nao serve para nada. Este script exige que as 12 regras aparecam,
cada uma com um codigo proprio, e exige que o relatorio nao se transforme em
centenas de linhas repetidas.

Roda fora do pytest de proposito: a suite cobre as funcoes, este script cobre a
pergunta que a suite nao responde sozinha, que e se os dois arquivos que
acompanham o repositorio se comportam como a documentacao promete.
"""

from __future__ import annotations

import sys
from pathlib import Path

#: Permite executar o script direto do checkout, sem instalar o pacote.
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from netlab.cargador import carregar_projeto  # noqa: E402
from netlab.cli import construir_parser, main as cli_main  # noqa: E402
from netlab.validador import CATALOGO_REGRAS, validar  # noqa: E402

VALIDO = RAIZ / "dados" / "projeto-predio.yaml"
COM_ERROS = RAIZ / "dados" / "projeto-com-erros.yaml"

#: Minimo de erros distintos que a especificacao exige.
MINIMO_ERROS = 6

#: Teto de erros, para o relatorio continuar legivel.
MAXIMO_ERROS = 25

#: Topologia esperada do projeto valido.
VLANS_ESPERADAS = 5
SWITCHES_ESPERADOS = 9


def main() -> int:
    """Verifica os dois criterios.

    Verify both acceptance criteria.
    """
    falhas: list[str] = []

    print(f"projeto valido:   {VALIDO.name}")
    projeto = carregar_projeto(VALIDO)
    resultado = validar(projeto)
    print(
        f"  {len(projeto.vlans)} VLANs, {len(projeto.switches)} switches, "
        f"{len(projeto.aps)} APs, {resultado.total} erro(s)"
    )
    if resultado.aprovado is False:
        falhas.append(
            "o projeto valido tem "
            f"{resultado.total} erro(s): {', '.join(resultado.codigos)}"
        )

    if len(projeto.vlans) != VLANS_ESPERADAS:
        falhas.append(
            f"o projeto valido tem {len(projeto.vlans)} VLANs, "
            f"esperava {VLANS_ESPERADAS}"
        )
    if len(projeto.switches) != SWITCHES_ESPERADOS:
        falhas.append(
            f"o projeto valido tem {len(projeto.switches)} switches, "
            f"esperava {SWITCHES_ESPERADOS}"
        )

    print(f"\nprojeto com erros: {COM_ERROS.name}")
    projeto_ruim = carregar_projeto(COM_ERROS)
    resultado_ruim = validar(projeto_ruim)
    print(f"  {resultado_ruim.total} erro(s), {len(resultado_ruim.codigos)} regra(s)")

    for codigo in sorted(CATALOGO_REGRAS):
        quantos = len(resultado_ruim.por_codigo(codigo))
        marca = "ok" if quantos else "AUSENTE"
        print(f"  {codigo}  {marca:<8} {CATALOGO_REGRAS[codigo]}")
        if not quantos:
            falhas.append(f"{codigo} nao detectou o caso plantado")

    if resultado_ruim.total < MINIMO_ERROS:
        falhas.append(
            f"o projeto com erros tem {resultado_ruim.total} erro(s), "
            f"a especificacao exige ao menos {MINIMO_ERROS}"
        )
    if resultado_ruim.total > MAXIMO_ERROS:
        falhas.append(
            f"o projeto com erros tem {resultado_ruim.total} erro(s); acima de "
            f"{MAXIMO_ERROS} o relatorio deixa de ser legivel"
        )

    print("\ncodigos de saida da CLI:")
    codigo_valido = cli_main(["validar", str(VALIDO)])
    print(f"  projeto valido   -> {codigo_valido} (esperado 0)")
    if codigo_valido != 0:
        falhas.append(f"a CLI devolveu {codigo_valido} para o projeto valido")

    codigo_ruim = cli_main(["validar", str(COM_ERROS), "--formato", "json"])
    print(f"  projeto com erros -> {codigo_ruim} (esperado 1)")
    if codigo_ruim != 1:
        falhas.append(f"a CLI devolveu {codigo_ruim} para o projeto com erros")

    codigo_ausente = cli_main(["validar", "nao-existe.yaml"])
    print(f"  arquivo ausente   -> {codigo_ausente} (esperado 2)")
    if codigo_ausente != 2:
        falhas.append(
            f"a CLI devolveu {codigo_ausente} para arquivo inexistente, "
            "esperava 2 para nao confundir arquivo ruim com projeto ruim"
        )

    print(f"\n{len(CATALOGO_REGRAS)} regras no catalogo")

    if falhas:
        print("\nFALHOU:")
        for falha in falhas:
            print(f"  - {falha}")
        return 1

    print(
        "\nok: projeto valido passa com 0 erro, projeto com erros dispara as "
        f"{len(CATALOGO_REGRAS)} regras e os tres codigos de saida estao "
        "corretos"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())