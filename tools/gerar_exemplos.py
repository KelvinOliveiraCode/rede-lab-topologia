"""Gera os exemplos do repositorio com saida real.

Generate the repository examples from real output.

Roda a CLI de verdade sobre os dois arquivos de projeto e grava a saida. Nada
aqui e escrito a mao: se uma regra mudar de comportamento, o exemplo muda junto
e o CI falha, porque a regeneracao precisa deixar o arquivo igual.

Uso: python tools/gerar_exemplos.py
"""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

#: Permite executar o script direto do checkout, sem instalar o pacote.
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from netlab.cli import main as cli_main  # noqa: E402

EXEMPLOS = RAIZ / "exemplos"

VALIDO = RAIZ / "dados" / "projeto-predio.yaml"
COM_ERROS = RAIZ / "dados" / "projeto-com-erros.yaml"

#: Caminho mostrado na documentacao, no lugar do caminho absoluto da maquina.
CAMINHO_DOCUMENTADO = "dados/projeto-predio.yaml"
CAMINHO_DOCUMENTADO_ERROS = "dados/projeto-com-erros.yaml"


def rodar(argv: list[str]) -> tuple[int, str]:
    """Roda um comando da CLI e captura a saida.

    Run a CLI command and capture its output.

    Args:
        argv: Argumentos do comando.

    Returns:
        Par com o codigo de saida e o texto produzido.
    """
    saida = io.StringIO()
    erro = io.StringIO()
    with redirect_stdout(saida), redirect_stderr(erro):
        codigo = cli_main(argv)
    return codigo, saida.getvalue() + erro.getvalue()


def normalizar(texto: str) -> str:
    """Troca o caminho absoluto da maquena pelo caminho documentado.

    Replace the machine's absolute path with the documented one.

    O exemplo precisa ser identico em qualquer maquina, senao o gate
    `git diff --exit-code` do CI falha sempre.

    Args:
        texto: Saida capturada.

    Returns:
        O texto com o caminho documentado.
    """
    return texto.replace(str(VALIDO), CAMINHO_DOCUMENTADO).replace(
        str(COM_ERROS), CAMINHO_DOCUMENTADO_ERROS
    )


def main() -> int:
    """Regera os dois artefatos de exemplo.

    Regenerate the two example artefacts.
    """
    EXEMPLOS.mkdir(exist_ok=True)

    _codigo, saida_valida = rodar(["validar", str(VALIDO)])
    _codigo, saida_erros = rodar(["validar", str(COM_ERROS)])
    _codigo, saida_regras = rodar(["regras"])
    _codigo, saida_resumo = rodar(["resumir", str(VALIDO)])

    cabecalho = (
        "# Saida real do validador\n\n"
        "Gerado por `python tools/gerar_exemplos.py`. Os tres blocos abaixo sao\n"
        "a saida da CLI sobre os dois arquivos que acompanham o repositorio.\n"
        "Nada foi escrito a mao.\n\n"
    )

    (EXEMPLOS / "saida-valida.txt").write_text(
        cabecalho
        + "## Projeto valido\n\n"
        + "```\n"
        + "PS> python -m netlab validar dados/projeto-predio.yaml\n"
        + saida_valida
        + "```\n\n"
        + f"Codigo de saida: 0. As {len(saida_regras.splitlines()) - 2} regras\n"
        "do catalogo estao listadas com `python -m netlab regras`.\n",
        encoding="utf-8",
    )

    (EXEMPLOS / "saida-com-erros.txt").write_text(
        "# Saida real do validador com o projeto que tem erros\n\n"
        "Gerado por `python tools/gerar_exemplos.py`. O arquivo\n"
        "`dados/projeto-com-erros.yaml` tem um caso de cada regra plantado, e\n"
        "abaixo esta a saida da CLI sobre ele.\n\n"
        "```\n"
        "PS> python -m netlab validar dados/projeto-com-erros.yaml\n"
        + saida_erros
        + "```\n\n"
        "## Resumo do projeto\n\n"
        "```\n"
        "PS> python -m netlab resumir dados/projeto-predio.yaml\n"
        + saida_resumo
        + "```\n",
        encoding="utf-8",
    )

    print(f"exemplos regravados em {EXEMPLOS}")
    for nome in sorted(p.name for p in EXEMPLOS.iterdir() if p.is_file()):
        print(f"  {nome:<26} {(EXEMPLOS / nome).stat().st_size:>7} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())