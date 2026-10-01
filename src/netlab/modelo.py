"""Modelo de dominio do projeto de rede LAN.

Domain model for a LAN design project.

Um projeto de rede aqui e o que a empresa decide **antes** de subir em campo:
quais VLANs existem, qual faixa cada uma ocupa, quem faz trunk com quem, onde o
DHCP entrega endereco, e que rotas sao permitidas. Errado isso, o erro so
aparece no teto, com a equipe parada e o Patch de Cabo na mao.

O modelo e a traducao do YAML em objetos. A validacao de regra esta em
:mod:`netlab.validador`; aqui so ha estrutura e as propriedades derivadas que
nao dependem de regra nenhuma.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field

#: Tipo de porta de switch.
TIPO_ACCESS = "access"
TIPO_TRUNK = "trunk"

#: Tipos de porta aceitos.
TIPOS_PORTA = frozenset({TIPO_ACCESS, TIPO_TRUNK})


class ErroDeProjeto(ValueError):
    """O arquivo de projeto declara algo que nao faz sentido.

    O arquivo esta bem formado como YAML, mas o conteudo e invalido: um tipo
    de porta desconhecido, uma faixa que nao e CIDR. Falhar na carga e melhor
    que deixar o validador descobrir depois.
    """


@dataclass(frozen=True)
class Vlan:
    """Uma VLAN declarada no projeto.

    Args:
        id: Numero da VLAN.
        nome: Nome logico, como ``10-CORPORATIVO``.
        faixa_ip: Sub-rede em notacao CIDR, como ``192.168.10.0/24``.
        descricao: Texto livre sobre o uso da VLAN.
    """

    id: int
    nome: str
    faixa_ip: str
    descricao: str = ""

    def __post_init__(self) -> None:
        """Valida a faixa ao construir.

        Validate the subnet at construction.
        """
        if not (1 <= self.id <= 4094):
            raise ErroDeProjeto(
                f"VLAN {self.id}: id fora de 1..4094"
            )
        try:
            ipaddress.ip_network(self.faixa_ip, strict=True)
        except ValueError as exc:
            raise ErroDeProjeto(
                f"VLAN {self.nome}: faixa {self.faixa_ip!r} invalida ({exc})"
            ) from exc

    @property
    def rede(self) -> ipaddress.IPv4Network:
        """Faixa como objeto de rede, para comparacao com ``overlaps``.

        The subnet as a network object, for ``overlaps`` comparison.
        """
        return ipaddress.ip_network(self.faixa_ip)

    @property
    def prefixo(self) -> int:
        """Tamanho do prefixo da faixa.

        Prefix length of the subnet.
        """
        return self.rede.prefixlen

    @property
    def rede_base(self) -> str:
        """Endereco de rede, sem a notacao de prefixo.

        Network address, without the prefix notation.
        """
        return str(self.rede.network_address)

    @property
    def gateway_esperado(self) -> str:
        """Gateway convencional da faixa: o primeiro endereco utilizavel.

        Conventional gateway: the first usable address.
        """
        return str(self.rede.network_address + 1)

    @property
    def eh_rede_privada(self) -> bool:
        """Se a faixa e RFC 1918.

        Whether the subnet is RFC 1918 private space.
        """
        return self.rede.is_private

    def contem(self, endereco: str | ipaddress.IPv4Address) -> bool:
        """Se o endereco cai dentro da faixa da VLAN.

        Whether the address falls inside the VLAN subnet.

        Args:
            endereco: Endereco a testar, em texto ou como objeto.

        Returns:
            ``True`` se o endereco pertence a faixa.
        """
        try:
            addr = (
                endereco if isinstance(endereco, ipaddress.IPv4Address)
                else ipaddress.IPv4Address(endereco)
            )
        except ipaddress.AddressValueError:
            return False
        return addr in self.rede


@dataclass
class Interface:
    """Uma porta de switch.

    Args:
        switch: Nome do switch dono da porta.
        porta: Nome da porta, como ``Gi0/1``.
        tipo: ``access`` ou ``trunk``.
        vlan: VLAN atribuida, ou a VLAN de gerencia de um trunk.
        descricao: Texto livre.
    """

    switch: str
    porta: str
    tipo: str
    vlan: int | None = None
    descricao: str = ""

    def __post_init__(self) -> None:
        """Recusa tipo de porta desconhecido.

        Refuse an unknown port type.
        """
        if self.tipo not in TIPOS_PORTA:
            raise ErroDeProjeto(
                f"{self.switch} {self.porta}: tipo {self.tipo!r} invalido, "
                f"use {sorted(TIPOS_PORTA)}"
            )

    @property
    def chave(self) -> str:
        """Identificador unico da porta no projeto.

        Unique port identifier in the project.
        """
        return f"{self.switch}/{self.porta}"


@dataclass
class PortaTrunk:
    """Uma VLAN permitida em um trunk.

    Args:
        switch: Nome do switch.
        porta: Nome da porta trunk.
        vlan_id: VLAN permitida.
        modo: ``native`` quando e a VLAN nativa do trunk.
    """

    switch: str
    porta: str
    vlan_id: int
    nativo: bool = False

    @property
    def chave(self) -> str:
        """Identificador unico da porta trunk.

        Unique trunk port identifier.
        """
        return f"{self.switch}/{self.porta}"

    @property
    def sem_tag(self) -> bool:
        """Se o trafego desta VLAN passa sem etiqueta 802.1Q.

        Whether this VLAN's traffic crosses untagged.
        """
        return self.nativo


@dataclass
class Switch:
    """Um switch da topologia.

    Args:
        nome: Nome unico.
        modelo: Modelo do equipamento.
        camada: ``core``, ``distribuicao`` ou ``acesso``.
        vlan_gerencia: VLAN de gerenciamento, usada no endereco do SVI.
        ip_gerencia: Endereço do SVI.
        snmp_community: Community SNMP configurada.
        snmp_modo: ``read`` ou ``read-write``.
    """

    nome: str
    modelo: str = ""
    camada: str = "acesso"
    vlan_gerencia: int | None = None
    ip_gerencia: str | None = None
    snmp_community: str | None = None
    snmp_modo: str = "read"

    @property
    def eh_roteador(self) -> bool:
        """Se o switch faz roteamento, isto e, e de camada 3.

        Whether the switch routes, that is, is layer 3.
        """
        return self.camada in ("core", "distribuicao")

    @property
    def snmp_e_gravacao(self) -> bool:
        """Se o SNMP esta em modo de escrita.

        Whether SNMP is in write mode.
        """
        return self.snmp_modo == "read-write"


@dataclass
class AccessPoint:
    """Um ponto de acesso sem fio.

    Args:
        nome: Nome unico.
        switch: Switch onde o AP esta ligado.
        porta: Porta do switch.
        ssids: SSIDs anunciados, com a VLAN de cada um.
    """

    nome: str
    switch: str = ""
    porta: str = ""
    ssids: dict[str, int] = field(default_factory=dict)

    @property
    def vlan_do_ssid(self) -> tuple[str, int] | None:
        """Primeiro SSID com VLAN mapeada, se houver.

        First SSID with a mapped VLAN, if any.
        """
        for ssid, vlan in self.ssids.items():
            if vlan:
                return (ssid, vlan)
        return None

    @property
    def ssids_sem_vlan(self) -> list[str]:
        """SSIDs anunciados sem VLAN mapeada.

        Broadcast SSIDs with no mapped VLAN.
        """
        return [s for s, v in self.ssids.items() if not v]


@dataclass
class PoolDhcp:
    """Faixa que o DHCP entrega endereco.

    Args:
        vlan_id: VLAN servida pelo pool.
        inicio: Primeiro endereco entregue.
        fim: Ultimo endereco entregue.
        gateway: Gateway anunciado no contrato.
    """

    vlan_id: int
    inicio: str
    fim: str
    gateway: str = ""

    @property
    def faixa(self) -> list[str]:
        """Todos os enderecos do pool, na ordem.

        Every address in the pool, in order.
        """
        try:
            inicio = ipaddress.IPv4Address(self.inicio)
            fim = ipaddress.IPv4Address(self.fim)
        except ipaddress.AddressValueError:
            return []
        if int(fim) < int(inicio):
            return []
        return [str(ipaddress.IPv4Address(i)) for i in range(int(inicio), int(fim) + 1)]


@dataclass
class Rota:
    """Uma rota declarada no projeto.

    Args:
        vlan_id: VLAN de origem.
        destino: Rede de destino em CIDR.
        proximo_salto: Interface de saida.
        descricao: Texto livre.
        padrao_para_internet: Se e rota default para a internet.
    """

    vlan_id: int
    destino: str = ""
    proximo_salto: str = ""
    descricao: str = ""
    padrao_para_internet: bool = False

    @property
    def origem(self) -> str:
        """Rota de origem, para rotulo na saida.

        Source of the route, for labelling in the output.
        """
        return "internet" if self.padrao_para_internet else (self.destino or "?")


@dataclass
class Projeto:
    """O projeto de rede inteiro.

    Args:
        nome: Nome do projeto.
        predio: Nome do predio, quando o projeto for predial.
        vlans: VLANs declaradas.
        switches: Switches por nome.
        interfaces: Portas de switch.
        trunks: Portas trunk com as VLANs permitidas.
        pools: Pools DHCP por id da VLAN.
        rotas: Rotas declaradas.
        aps: Pontos de acesso.
        outros: Demais equipamentos declarados, como firewall e sensores.
    """

    nome: str = "projeto"
    predio: str = ""
    vlans: dict[int, Vlan] = field(default_factory=dict)
    switches: dict[str, Switch] = field(default_factory=dict)
    interfaces: dict[str, Interface] = field(default_factory=dict)
    trunks: list[PortaTrunk] = field(default_factory=list)
    pools: dict[int, PoolDhcp] = field(default_factory=dict)
    rotas: list[Rota] = field(default_factory=list)
    aps: dict[str, AccessPoint] = field(default_factory=dict)
    outros: dict[str, dict] = field(default_factory=dict)

    def vlan(self, vlan_id: int) -> Vlan | None:
        """Acha uma VLAN pelo id.

        Find a VLAN by id.
        """
        return self.vlans.get(vlan_id)

    @property
    def vlan_gerencia(self) -> int | None:
        """VLAN de gerenciamento do projeto, pela nomenclatura da faixa.

        Management VLAN, by the naming convention of the subnet.
        """
        for vlan in self.vlans.values():
            if vlan.nome.upper().startswith("10-") or "CORPORATIVO" in vlan.nome.upper():
                return vlan.id
        return None

    def vlans_de_categoria(self, categoria: str) -> list[Vlan]:
        """VLANs cujo nome comeca pelo numero da categoria.

        VLANs whose name starts with the category number.
        """
        prefixo = f"{categoria}-"
        return [v for v in self.vlans.values() if v.nome.upper().startswith(prefixo)]

    @property
    def total_dispositivos(self) -> int:
        """Quantos equipamentos o projeto declara.

        How many devices the project declares.
        """
        return (
            len(self.switches)
            + len(self.aps)
            + sum(
                len(v) for v in self.outros.values()
                if isinstance(v, list)
            )
        )

    def trunks_de(self, switch: str) -> list[PortaTrunk]:
        """Trunks de um switch.

        Trunk ports of a switch.
        """
        return [t for t in self.trunks if t.switch == switch]

    def ports_do_switch(self, switch: str) -> list[Interface]:
        """Portas de um switch.

        Ports of a switch.
        """
        return [i for i in self.interfaces.values() if i.switch == switch]