"""Saida do validador: texto no terminal, JSON e os arquivos de exemplo.

Validator output: terminal text, JSON and the example files.

A saida em terminal usa cor, mas respeita ``NO_COLOR`` e o fato de a saida nao
ser um terminal. Cor em arquivo de log e sequencia de escape nao e informacao.
"""

from __future__ import annotations

import json
import os
import sys
from typing import TextIO

from .modelo import Projeto
from .validador import CATALOGO_REGRAS, Resultado, resultado_para_dict

#: Codigos de cor ANSI por criticidade.
CORES = {
    "alta": "\033[31m",
    "media": "\033[33m",
    "baixa": "\033[36m",
    "ok": "\033[32m",
}

#: Codigo que zera a cor.
SEM_COR = "\033[0m"

#: Negrito.
NEGRITO = "\033[1m"

#: Numero do nivel de cada criticidade.
NIVEIS = {"alta": 0, "media": 1, "baixa": 2}


def cor_ativa(fluxo: TextIO | None = None) -> bool:
    """Se a saida deve ter cor.

    Whether the output should carry colour.

    Args:
        fluxo: Fluxo de saida. Padrao: ``sys.stdout``.

    Returns:
        ``True`` quando o destino e um terminal e ``NO_COLOR`` nao esta setado.
    """
    destino = fluxo if fluxo is not None else sys.stdout
    if os.environ.get("NO_COLOR"):
        return False
    return bool(getattr(destino, "isatty", lambda: False)())


def _pintar(texto: str, cor: str, usar_cor: bool) -> str:
    """Aplica cor, se houver.

    Apply colour, if enabled.
    """
    if not usar_cor:
        return texto
    return f"{CORES.get(cor, '')}{texto}{SEM_COR}"


def ordenar(erros) -> list:
    """Ordena erros por criticidade e depois por codigo.

    Sort errors by severity, then by rule code.

    Args:
        erros: Lista de :class:`~netlab.validador.ErroValidacao`.

    Returns:
        A lista ordenada.
    """
    return sorted(erros, key=lambda e: (NIVEIS.get(e.criticidade, 3), e.codigo))


def formatar_texto(
    projeto: Projeto,
    resultado: Resultado,
    usar_cor: bool = False,
) -> str:
    """Monta a saida de texto do validador.

    Build the validator's text output.

    Args:
        projeto: Projeto validado.
        resultado: Resultado da validacao.
        usar_cor: Se deve aplicar cor.

    Returns:
        Texto com o resumo e a lista de erros.
    """
    linhas: list[str] = []

    cabecalho = f"Projeto: {projeto.nome}"
    if projeto.predio:
        cabecalho += f" - {projeto.predio}"
    linhas.append(_pintar(cabecalho, "ok", usar_cor))
    linhas.append(
        f"{len(projeto.vlans)} VLANs | {len(projeto.switches)} switches | "
        f"{len(projeto.interfaces)} portas | {len(projeto.aps)} APs | "
        f"{len(resultado.regras_aplicadas)} regras aplicadas"
    )
    linhas.append("")

    if resultado.aprovado:
        linhas.append(_pintar(
            f"0 erros em {len(projeto.switches)} dispositivos, "
            f"{len(projeto.vlans)} VLANs",
            "ok",
            usar_cor,
        ))
        return "\n".join(linhas)

    altas = len(resultado.por_criticidade("alta"))
    medias = len(resultado.por_criticidade("media"))
    linhas.append(_pintar(
        f"{resultado.total} erro(s) encontrado(s): {altas} alta, "
        f"{medias} media",
        "alta",
        usar_cor,
    ))
    linhas.append("")

    atual = ""
    for erro in ordenar(resultado.erros):
        if erro.codigo != atual:
            atual = erro.codigo
            nome = CATALOGO_REGRAS.get(erro.codigo, "")
            linhas.append(_pintar(f"{erro.codigo} - {nome}", "alta", usar_cor))
        cabecalho_erro = f"  {erro.mensagem}"
        linhas.append(_pintar(cabecalho_erro, erro.criticidade, usar_cor))
        if erro.onde:
            linhas.append(f"    onde: {erro.onde}")
        if erro.sugestao:
            linhas.append(f"    sugestao: {erro.sugestao}")

    return "\n".join(linhas)


def formatar_json(projeto: Projeto, resultado: Resultado) -> str:
    """Monta a saida JSON do validador.

    Build the validator's JSON output.

    Args:
        projeto: Projeto validado.
        resultado: Resultado da validacao.

    Returns:
        Texto JSON indentado.
    """
    dados = resultado_para_dict(resultado)
    dados["projeto"] = {
        "nome": projeto.nome,
        "predio": projeto.predio,
        "vlans": len(projeto.vlans),
        "switches": len(projeto.switches),
        "interfaces": len(projeto.interfaces),
        "aps": len(projeto.aps),
    }
    dados["catalogo_regras"] = CATALOGO_REGRAS
    return json.dumps(dados, ensure_ascii=False, indent=2)


def imprimir(
    projeto: Projeto,
    resultado: Resultado,
    formato: str = "texto",
    saida: TextIO | None = None,
) -> int:
    """Escreve a saida e devolve o codigo de saida do processo.

    Write the output and return the process exit code.

    Args:
        projeto: Projeto validado.
        resultado: Resultado da validacao.
        formato: ``texto`` ou ``json``.
        saida: Fluxo de destino.

    Returns:
        ``0`` quando o projeto passou, ``1`` quando tem erro.
    """
    fluxo = saida if saida is not None else sys.stdout
    if formato == "json":
        fluxo.write(formatar_json(projeto, resultado) + "\n")
    else:
        fluxo.write(
            formatar_texto(projeto, resultado, cor_ativa(fluxo)) + "\n"
        )
    return 0 if resultado.aprovado else 1


def gravar_json(projeto: Projeto, resultado: Resultado, caminho) -> None:
    """Grava o relatorio JSON em arquivo.

    Write the JSON report to a file.

    Args:
        projeto: Projeto validado.
        resultado: Resultado da validacao.
        caminho: Caminho de destino.
    """
    from pathlib import Path

    destino = Path(caminho)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(formatar_json(projeto, resultado) + "\n", encoding="utf-8")


def resumo_curto(resultado: Resultado) -> str:
    """Resumo de uma linha.

    One-line summary.
    """
    if resultado.aprovado:
        return "aprovado: nenhum erro"
    return (
        f"{resultado.total} erro(s) em {len(resultado.codigos)} "
        f"regra(s): {', '.join(resultado.codigos)}"
    )