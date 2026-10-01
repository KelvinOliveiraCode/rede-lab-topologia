"""CLI do netlab: valida um projeto de rede e mostra as violacoes.

netlab CLI: validate a network design and show the violations.

Codigo de saida: ``0`` quando o projeto passa, ``1`` quando ha erro de projeto,
``2`` quando o arquivo nem chegou a ser lido. Os tres sao distintos de proposito:
em automacao, um arquivo corrompido e um projeto ruim nao podem sair igual.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .cargador import ErroDeCarga, carregar_projeto
from .relatorio import (
    formatar_json,
    formatar_texto,
    gravar_json,
    imprimir,
    resumo_curto,
)
from .validador import CATALOGO_REGRAS, validar

#: Codigo de saida quando o projeto tem violacao.
SAIDA_COM_ERROS = 1

#: Codigo de saida quando o arquivo nao pode ser lido.
SAIDA_COM_ARQUIVO_INVALIDO = 2


def _cmd_validar(args: argparse.Namespace) -> int:
    """Subcomando validar.

    The validate subcommand.
    """
    try:
        projeto = carregar_projeto(args.projeto)
    except ErroDeCarga as exc:
        print(f"Erro / error: {exc}", file=sys.stderr)
        return SAIDA_COM_ARQUIVO_INVALIDO

    resultado = validar(projeto)

    if args.saida:
        destino = Path(args.saida)
        destino.parent.mkdir(parents=True, exist_ok=True)
        conteudo = (
            formatar_json(projeto, resultado)
            if args.formato == "json"
            else formatar_texto(projeto, resultado, usar_cor=False)
        )
        destino.write_text(conteudo + "\n", encoding="utf-8")
        print(f"Saida gravada em: {destino}")

    if args.json_saida:
        gravar_json(projeto, resultado, args.json_saida)
        print(f"JSON gravado em: {args.json_saida}")

    if args.saida and args.formato == "texto":
        print(resumo_curto(resultado))
        return 0 if resultado.aprovado else SAIDA_COM_ERROS

    return imprimir(projeto, resultado, args.formato)


def _cmd_regras(args: argparse.Namespace) -> int:
    """Subcomando regras: lista as 12 regras.

    The rules subcommand: list the 12 rules.
    """
    for codigo, nome in sorted(CATALOGO_REGRAS.items()):
        print(f"{codigo}  {nome}")
    print(f"\n{len(CATALOGO_REGRAS)} regras")
    return 0


def _cmd_resumir(args: argparse.Namespace) -> int:
    """Subcomando resumir: mostra a estrutura sem validar.

    The summary subcommand: show the structure without validating.
    """
    try:
        projeto = carregar_projeto(args.projeto)
    except ErroDeCarga as exc:
        print(f"Erro / error: {exc}", file=sys.stderr)
        return SAIDA_COM_ARQUIVO_INVALIDO

    print(f"Projeto: {projeto.nome}")
    if projeto.predio:
        print(f"Predio: {projeto.predio}")
    print(f"Dispositivos: {projeto.total_dispositivos}")
    print(f"VLANs: {len(projeto.vlans)}")
    for vlan in sorted(projeto.vlans.values(), key=lambda v: v.id):
        print(f"  {vlan.id:>4} {vlan.nome:<22} {vlan.faixa_ip}")
    print(f"Switches: {len(projeto.switches)}")
    for switch in sorted(projeto.switches.values(), key=lambda s: s.nome):
        ip = switch.ip_gerencia or "sem ip"
        print(f"  {switch.nome:<22} {switch.camada:<14} {ip}")
    print(f"Access points: {len(projeto.aps)}")
    for ap in sorted(projeto.aps.values(), key=lambda a: a.nome):
        print(f"  {ap.nome:<22} {len(ap.ssids)} SSIDs")
    return 0


def construir_parser() -> argparse.ArgumentParser:
    """Monta o parser de argumentos.

    Build the argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="netlab",
        description=(
            "Validador de projeto de rede LAN a partir de arquivo declarativo. "
            "Sem emulador, sem equipamento. "
            "LAN design validator from a declarative file. No emulator, no gear."
        ),
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    p_val = sub.add_parser("validar", help="Valida um projeto de rede")
    p_val.add_argument("projeto", help="Caminho do YAML do projeto")
    p_val.add_argument(
        "--formato", choices=["texto", "json"], default="texto",
        help="Formato da saida",
    )
    p_val.add_argument("--saida", help="Grava a saida neste caminho")
    p_val.add_argument(
        "--json-saida", help="Grava o relatorio JSON neste caminho"
    )
    p_val.set_defaults(func=_cmd_validar)

    p_reg = sub.add_parser("regras", help="Lista as 12 regras")
    p_reg.set_defaults(func=_cmd_regras)

    p_res = sub.add_parser("resumir", help="Mostra a estrutura do projeto")
    p_res.add_argument("projeto", help="Caminho do YAML do projeto")
    p_res.set_defaults(func=_cmd_resumir)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada da CLI.

    CLI entry point.

    Args:
        argv: Argumentos. Padrao: ``sys.argv[1:]``.

    Returns:
        ``0`` aprovado, ``1`` com erro de projeto, ``2`` arquivo invalido.
    """
    parser = construir_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())