"""Leitura e validacao do arquivo de projeto em YAML.

Load and validate the project YAML file.

O arquivo de projeto e a fonte da verdade de um desenho de rede. Esta camada
fala duas coisas: traduz YAML em :class:`~netlab.modelo.Projeto`, e recusa
arquivo cujo conteudo nao faz sentido antes de qualquer regra rodar.

A separacao importa. Um YAML com ``tipo: trunkk`` nao e um projeto com erro de
projeto: e um arquivo com erro de digitacao. Deixar isso chegar ao validador
produziria um erro de regra sobre um equipamento inexistente.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .modelo import (
    AccessPoint,
    ErroDeProjeto,
    Interface,
    PoolDhcp,
    PortaTrunk,
    Projeto,
    Rota,
    Switch,
    Vlan,
)

#: Categorias que o modelo reconhece em ``outros``.
CATEGORIAS_OUTROS = ("firewalls", "servidores", "sensores", "nvrs", "medidores")


class ErroDeCarga(ValueError):
    """O arquivo de projeto nao pode ser lido.

    The project file cannot be read.
    """


def _exigir(dado: dict, chave: str, contexto: str) -> Any:
    """Le uma chave obrigatoria.

    Read a required key.

    Args:
        dado: Dicionario de origem.
        chave: Chave a ler.
        contexto: Texto que identifica o item, para a mensagem de erro.

    Returns:
        O valor da chave.

    Raises:
        ErroDeCarga: Se a chave nao existir.
    """
    if chave not in dado:
        raise ErroDeCarga(f"{contexto}: campo obrigatorio '{chave}' ausente")
    return dado[chave]


def _texto(valor: Any) -> str:
    """Converte valor em texto,aceitando numero.

    Convert a value to text, accepting numbers.
    """
    return str(valor)


def carregar_vlans(lista: list[dict]) -> dict[int, Vlan]:
    """Traduz a lista de VLANs.

    Translate the VLAN list.

    Args:
        lista: Lista de dicionarios de VLAN.

    Returns:
        Dicionario de id para :class:`~netlab.modelo.Vlan`.
    """
    vlans: dict[int, Vlan] = {}
    for item in lista:
        contexto = f"VLAN {item.get('nome', item.get('id', '?'))}"
        vlan = Vlan(
            id=int(_exigir(item, "id", contexto)),
            nome=_texto(_exigir(item, "nome", contexto)),
            faixa_ip=_texto(_exigir(item, "faixa", contexto)),
            descricao=_texto(item.get("descricao", "")),
        )
        if vlan.id in vlans:
            raise ErroDeCarga(
                f"VLAN {vlan.id} declarada mais de uma vez"
            )
        vlans[vlan.id] = vlan
    return vlans


def carregar_switches(lista: list[dict]) -> dict[str, Switch]:
    """Traduz a lista de switches.

    Translate the switch list.
    """
    switches: dict[str, Switch] = {}
    for item in lista:
        nome = _texto(_exigir(item, "nome", "switch"))
        switch = Switch(
            nome=nome,
            modelo=_texto(item.get("modelo", "")),
            camada=_texto(item.get("camada", "acesso")),
            vlan_gerencia=(
                int(item["vlan_gerencia"]) if item.get("vlan_gerencia") else None
            ),
            ip_gerencia=(
                _texto(item["ip_gerencia"]) if item.get("ip_gerencia") else None
            ),
            snmp_community=(
                _texto(item["snmp_community"]) if item.get("snmp_community") else None
            ),
            snmp_modo=_texto(item.get("snmp_modo", "read")),
        )
        if nome in switches:
            raise ErroDeCarga(f"switch {nome} declarado mais de uma vez")
        switches[nome] = switch
    return switches


def carregar_interfaces(lista: list[dict]) -> dict[str, Interface]:
    """Traduz a lista de portas de switch.

    Translate the switch port list.
    """
    interfaces: dict[str, Interface] = {}
    for item in lista:
        switch = _texto(_exigir(item, "switch", "interface"))
        porta = _texto(_exigir(item, "porta", f"interface de {switch}"))
        chave = f"{switch}/{porta}"
        interface = Interface(
            switch=switch,
            porta=porta,
            tipo=_texto(_exigir(item, "tipo", f"interface {chave}")),
            vlan=(int(item["vlan"]) if item.get("vlan") else None),
            descricao=_texto(item.get("descricao", "")),
        )
        if chave in interfaces:
            raise ErroDeCarga(f"interface {chave} declarada mais de uma vez")
        interfaces[chave] = interface
    return interfaces


def carregar_trunks(lista: list[dict]) -> list[PortaTrunk]:
    """Traduz a lista de VLANs permitidas em trunk.

    Translate the trunk VLAN list.
    """
    trunks: list[PortaTrunk] = []
    vistas: set[tuple[str, str, int]] = set()
    for item in lista:
        switch = _texto(_exigir(item, "switch", "trunk"))
        porta = _texto(_exigir(item, "porta", f"trunk de {switch}"))
        vlan_id = int(_exigir(item, "vlan", f"trunk {switch}/{porta}"))
        chave = (switch, porta, vlan_id)
        if chave in vistas:
            raise ErroDeCarga(
                f"trunk {switch}/{porta} declara a VLAN {vlan_id} duas vezes"
            )
        vistas.add(chave)
        trunks.append(PortaTrunk(
            switch=switch,
            porta=porta,
            vlan_id=vlan_id,
            nativo=bool(item.get("nativo", False)),
        ))
    return trunks


def carregar_pools(lista: list[dict]) -> dict[int, PoolDhcp]:
    """Traduz a lista de pools DHCP.

    Translate the DHCP pool list.
    """
    pools: dict[int, PoolDhcp] = {}
    for item in lista:
        vlan_id = int(_exigir(item, "vlan", "pool DHCP"))
        contexto = f"pool DHCP da VLAN {vlan_id}"
        pools[vlan_id] = PoolDhcp(
            vlan_id=vlan_id,
            inicio=_texto(_exigir(item, "inicio", contexto)),
            fim=_texto(_exigir(item, "fim", contexto)),
            gateway=_texto(item.get("gateway", "")),
        )
    return pools


def carregar_rotas(lista: list[dict]) -> list[Rota]:
    """Traduz a lista de rotas.

    Translate the route list.
    """
    rotas: list[Rota] = []
    for item in lista:
        rotas.append(Rota(
            vlan_id=int(_exigir(item, "vlan", "rota")),
            destino=_texto(item.get("destino", "")),
            proximo_salto=_texto(item.get("proximo_salto", "")),
            descricao=_texto(item.get("descricao", "")),
            padrao_para_internet=bool(
                item.get("padrao_para_internet", False)
                or item.get("default", False)
            ),
        ))
    return rotas


def carregar_aps(lista: list[dict]) -> dict[str, AccessPoint]:
    """Traduz a lista de pontos de acesso.

    Translate the access point list.
    """
    aps: dict[str, AccessPoint] = {}
    for item in lista:
        nome = _texto(_exigir(item, "nome", "ponto de acesso"))
        ssids = {
            _texto(s): (int(v) if v else 0)
            for s, v in (item.get("ssids") or {}).items()
        }
        aps[nome] = AccessPoint(
            nome=nome,
            switch=_texto(item.get("switch", "")),
            porta=_texto(item.get("porta", "")),
            ssids=ssids,
        )
    return aps


def carregar_projeto(caminho: str | Path) -> Projeto:
    """Le um arquivo de projeto e monta o modelo.

    Load a project file and build the model.

    Args:
        caminho: Caminho do arquivo YAML.

    Returns:
        O projeto carregado.

    Raises:
        ErroDeCarga: Se o arquivo nao existir, nao for YAML valido, ou tiver
            campo obrigatorio ausente.
        ErroDeProjeto: Se um valor for invalido, como faixa que nao e CIDR.
    """
    arquivo = Path(caminho)
    if not arquivo.exists():
        raise ErroDeCarga(f"{arquivo}: arquivo nao encontrado")

    try:
        with open(arquivo, "r", encoding="utf-8") as fh:
            dados = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise ErroDeCarga(f"{arquivo}: YAML invalido ({exc})") from exc

    if not isinstance(dados, dict):
        raise ErroDeCarga(f"{arquivo}: esperado um mapeamento no topo do arquivo")

    try:
        projeto = Projeto(
            nome=_texto(dados.get("nome", arquivo.stem)),
            predio=_texto(dados.get("predio", "")),
            vlans=carregar_vlans(dados.get("vlans") or []),
            switches=carregar_switches(dados.get("switches") or []),
            interfaces=carregar_interfaces(dados.get("interfaces") or []),
            trunks=carregar_trunks(dados.get("trunks") or []),
            pools=carregar_pools(dados.get("dhcp") or []),
            rotas=carregar_rotas(dados.get("rotas") or []),
            aps=carregar_aps(dados.get("aps") or []),
            outros={
                chave: dados[chave]
                for chave in CATEGORIAS_OUTROS
                if chave in dados
            },
        )
    except ErroDeProjeto as exc:
        raise ErroDeCarga(f"{arquivo}: {exc}") from exc

    _checar_referencias(projeto)
    return projeto


def _checar_referencias(projeto: Projeto) -> None:
    """Confere que porta, trunk e AP apontam para equipamento declarado.

    Check that ports, trunks and APs point at declared equipment.

    Uma porta que declara um switch inexistente nao e um problema de projeto:
    e um erro de digitacao no arquivo. Deixar passar faria a porta nao contar
    em nenhuma regra, e o validador aprovaria um arquivo que nao descreve a
    rede que ele diz descrever.

    Args:
        projeto: Projeto ja montado.

    Raises:
        ErroDeCarga: Se alguma referencia nao resolver.
    """
    for interface in projeto.interfaces.values():
        if interface.switch not in projeto.switches:
            raise ErroDeCarga(
                f"interface {interface.chave}: switch '{interface.switch}' "
                "nao declarado no projeto"
            )
    for trunk in projeto.trunks:
        if trunk.switch not in projeto.switches:
            raise ErroDeCarga(
                f"trunk {trunk.chave}: switch '{trunk.switch}' "
                "nao declarado no projeto"
            )
    for ap in projeto.aps.values():
        if ap.switch and ap.switch not in projeto.switches:
            raise ErroDeCarga(
                f"ponto de acesso {ap.nome}: switch '{ap.switch}' "
                "nao declarado no projeto"
            )


def resumo_do_projeto(projeto: Projeto) -> str:
    """Linha de identificacao do projeto.

    One-line project identity.
    """
    partes = [
        f"{projeto.nome}",
        f"{len(projeto.vlans)} VLANs",
        f"{len(projeto.switches)} switches",
        f"{len(projeto.interfaces)} portas",
        f"{len(projeto.trunks)} VLANs de trunk",
        f"{len(projeto.pools)} pools DHCP",
        f"{len(projeto.aps)} APs",
    ]
    return ", ".join(partes)