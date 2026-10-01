"""As 12 regras de validacao do projeto de rede.

The 12 network design validation rules.

Cada regra tem codigo, nome e o que ela protege. A aritmetica de sub-rede vem
de :mod:`ipaddress`, da biblioteca padrao, e nao de comparacao de texto: duas
faixas podem ter a mesma notacao e se sobrepor, ou notacoes diferentes e nao se
sobrepor, e so ``overlaps`` responde isso direito.

Duas regras merecem justificativa por serem as mais importantes do conjunto:

**E006 e E007, segmentacao de rede.** Video e gesto de energia nao convivem com
a internet. Um NVR que alcanca a web pode ser Alcançado de fora; um medidor de
energia alcancado pela internet vira ponto de entrada para a rede eletrica. Sao
os dois casos em que a falha de segmentacao deixa de ser teoria e vira incidente
reais, e por isso a regra nao e so 'existe rota default', e 'existe rota default
**para essa categoria**'.

**E009, endereco duplicado.** Dois equipamentos com o mesmo endereco em switches
diferentes geram ARP duplicado. O sintoma em campo e intermitente: o acesso
responde e deixa de responder conforme o switch que ganha o ARP. E o tipo de
problema que se passa uma semana se sendo debugado como "problema de rede".
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from .modelo import TIPO_ACCESS, Projeto

#: Regra que este projeto considera obrigatoria. Numero mais alto significa
#:_segmentacao_: e o que nao pode quebrar.
REGRA_PADRAO = 1


@dataclass(frozen=True)
class ErroValidacao:
    """Uma violacao encontrada.

    Args:
        codigo: Codigo da regra, como ``E006``.
        mensagem: Texto que explica a violacao.
        onde: Onde a violacao esta, como ``core-1 Gi0/24``.
        sugestao: O que fazer para resolver.
        criticidade: ``alta``, ``media`` ou ``baixa``.
    """

    codigo: str
    mensagem: str
    onde: str = ""
    sugestao: str = ""
    criticidade: str = "media"

    def __str__(self) -> str:
        """Linha de texto do erro.

        One-line text of the error.
        """
        partes = [f"[{self.codigo}] {self.mensagem}"]
        if self.onde:
            partes.append(f"em {self.onde}")
        return " ".join(partes)


@dataclass
class Resultado:
    """Resultado da validacao de um projeto.

    Args:
        erros: Violacoes encontradas.
        regras_aplicadas: Codigos das regras executadas.
    """

    erros: list[ErroValidacao] = field(default_factory=list)
    regras_aplicadas: list[str] = field(default_factory=list)

    def adicionar(self, *args, **kwargs) -> None:
        """Registra uma violacao.

        Record a violation.
        """
        self.erros.append(ErroValidacao(*args, **kwargs))

    @property
    def total(self) -> int:
        """Quantas violacoes foram encontradas.

        How many violations were found.
        """
        return len(self.erros)

    @property
    def aprovado(self) -> bool:
        """Se o projeto passou sem nenhuma violacao.

        Whether the project passed with no violations.
        """
        return not self.erros

    @property
    def codigos(self) -> list[str]:
        """Codigos distintos das violacoes encontradas.

        Distinct violation codes.
        """
        return sorted({e.codigo for e in self.erros})

    def por_criticidade(self, criticidade: str) -> list[ErroValidacao]:
        """Violacoes de uma criticidade.

        Violations of one severity.

        Args:
            criticidade: ``alta``, ``media`` ou ``baixa``.

        Returns:
            As violacoes dessa criticidade.
        """
        return [e for e in self.erros if e.criticidade == criticidade]

    def por_codigo(self, codigo: str) -> list[ErroValidacao]:
        """Violacoes de um codigo de regra.

        Violations of one rule code.

        Args:
            codigo: Codigo da regra.

        Returns:
            As violacoes daquela regra.
        """
        return [e for e in self.erros if e.codigo == codigo]


# ---------------------------------------------------------------------------
# E001 - Sobreposicao de sub-rede
# ---------------------------------------------------------------------------

def regra_e001(projeto: Projeto, r: Resultado) -> None:
    """E001: duas VLANs com sub-rede que se sobrepoem.

    Duas redes que se sobrepoem nao podem ter gateway proprio sem roteamento
    entre elas, e o resultado e traffic caindo na VLAN errada.
    """
    vlans = sorted(projeto.vlans.values(), key=lambda v: v.id)
    for i, a in enumerate(vlans):
        for b in vlans[i + 1:]:
            if a.rede.overlaps(b.rede):
                r.adicionar(
                    "E001",
                    f"VLANs {a.nome} ({a.faixa_ip}) e {b.nome} ({b.faixa_ip}) "
                    "tem sub-rede que se sobrepoem",
                    onde=f"{a.id} e {b.id}",
                    sugestao="Dê faixas disjuntas as duas VLANs.",
                    criticidade="alta",
                )


# ---------------------------------------------------------------------------
# E002 - Gateway fora da propria faixa
# ---------------------------------------------------------------------------

def regra_e002(projeto: Projeto, r: Resultado) -> None:
    """E002: endereco de gerenciamento fora da faixa da sua VLAN.

    O SVI de um switch tem que estar dentro da faixa da VLAN que ele gerencia.
    Fora dela, o SVI fica inalcancavel de dentro e o switch perde gerenciamento.
    """
    for switch in projeto.switches.values():
        if not switch.ip_gerencia or switch.vlan_gerencia is None:
            continue
        vlan = projeto.vlan(switch.vlan_gerencia)
        if vlan is None:
            continue
        if not vlan.contem(switch.ip_gerencia):
            r.adicionar(
                "E002",
                f"endereco de gerenciamento {switch.ip_gerencia} esta fora da "
                f"faixa da VLAN {vlan.nome} ({vlan.faixa_ip})",
                onde=f"{switch.nome} vlan {vlan.id}",
                sugestao=(
                    f"Use um endereco dentro de {vlan.faixa_ip}, por exemplo "
                    f"{vlan.gateway_esperado}."
                ),
                criticidade="alta",
            )


# ---------------------------------------------------------------------------
# E003 - Pool DHCP fora da faixa da VLAN
# ---------------------------------------------------------------------------

def regra_e003(projeto: Projeto, r: Resultado) -> None:
    """E003: pool DHCP entregando endereco fora da faixa da VLAN servida.

    Um pool que vaza para outra faixa entrega endereco duplicado, que e o
    E009 se manifestando por outro caminho.

    Reporta **um erro por pool**, nao um por endereco. Um pool de 150 enderecos
    todo fora da faixa geraria 150 achados do mesmo problema, com a mesma
    correcao, e um relatorio com 150 linhas iguais nao e lido por ninguem. A
    evidencia resume quais enderecos fogem e quantos.
    """
    for vlan_id, pool in sorted(projeto.pools.items()):
        vlan = projeto.vlan(vlan_id)
        if vlan is None:
            continue
        fora = [e for e in pool.faixa if not vlan.contem(e)]
        if not fora:
            continue
        primeiro, ultimo = fora[0], fora[-1]
        resumo = (
            f"{primeiro} ate {ultimo}"
            if len(fora) > 1
            else primeiro
        )
        r.adicionar(
            "E003",
            f"pool DHCP da VLAN {vlan.nome} entrega {len(fora)} endereco(s) "
            f"fora de {vlan.faixa_ip}: {resumo}",
            onde=f"pool {pool.inicio}-{pool.fim}",
            sugestao=f"Mantenha o pool inteiro dentro de {vlan.faixa_ip}.",
            criticidade="alta",
        )


# ---------------------------------------------------------------------------
# E004 - VLAN usada mas nao declarada
# ---------------------------------------------------------------------------

def regra_e004(projeto: Projeto, r: Resultado) -> None:
    """E004: interface referencia VLAN que o projeto nao declara.

    Uma porta access apontando para VLAN inexistente fica sem servico, e um
    trunk permitindo VLAN inexistente derruba a sessao do enlace quando o
    primeiro switch Learn dela.
    """
    for interface in projeto.interfaces.values():
        if interface.tipo != TIPO_ACCESS:
            continue
        if interface.vlan is None:
            continue
        if interface.vlan not in projeto.vlans:
            r.adicionar(
                "E004",
                f"porta access usa a VLAN {interface.vlan}, que nao esta "
                "declarada no projeto",
                onde=interface.chave,
                sugestao=f"Declare a VLAN {interface.vlan} ou corrija a porta.",
                criticidade="alta",
            )


# ---------------------------------------------------------------------------
# E005 - Trunk referencia VLAN inexistente
# ---------------------------------------------------------------------------

def regra_e005(projeto: Projeto, r: Resultado) -> None:
    """E005: trunk permite VLAN que o projeto nao declara."""
    for trunk in projeto.trunks:
        if trunk.vlan_id not in projeto.vlans:
            r.adicionar(
                "E005",
                f"trunk permite a VLAN {trunk.vlan_id}, que nao esta declarada "
                "no projeto",
                onde=trunk.chave,
                sugestao=f"Declare a VLAN {trunk.vlan_id} ou remova do trunk.",
                criticidade="alta",
            )


# ---------------------------------------------------------------------------
# E006 e E007 - Segmentacao de rede
# ---------------------------------------------------------------------------

def _regra_segmentacao(categoria: str, codigo: str, projeto: Projeto,
                      r: Resultado, nome_amigavel: str) -> None:
    """Regra de segmentacao: categoria sem rota default para a internet.

    Segmentation rule: category with no default route to the internet.

    Args:
        categoria: Numero da categoria, como ``"30"``.
        codigo: Codigo da regra, ``E006`` ou ``E007``.
        projeto: Projeto a validar.
        r: Resultado em construcao.
        nome_amigavel: Nome para a mensagem, como ``CFTV``.
    """
    vlans_categoria = projeto.vlans_de_categoria(categoria)
    if not vlans_categoria:
        return
    ids = {v.id for v in vlans_categoria}
    nomes = ", ".join(v.nome for v in vlans_categoria)

    for rota in projeto.rotas:
        if rota.vlan_id not in ids or not rota.padrao_para_internet:
            continue
        r.adicionar(
            codigo,
            f"VLAN {nomes} tem rota default para a internet. Equipamento de "
            f"{nome_amigavel} nao deve sair da rede local: alcancavel de fora, "
            "ele vira caminho de entrada para o que esta atras dele",
            onde=f"rota da VLAN {rota.vlan_id}",
            sugestao=(
                f"Remova a rota default da VLAN {rota.vlan_id}. Se precisar de "
                "acesso remoto, use VPN com autenticacao."
            ),
            criticidade="alta",
        )


def regra_e006(projeto: Projeto, r: Resultado) -> None:
    """E006: CFTV sem rota default para a internet."""
    _regra_segmentacao("30", "E006", projeto, r, "CFTV e seguranca eletronica")


def regra_e007(projeto: Projeto, r: Resultado) -> None:
    """E007: ENERGIA-IP sem rota default para a internet."""
    _regra_segmentacao("50", "E007", projeto, r, "Energia IP e automacao predial")


# ---------------------------------------------------------------------------
# E008 - Trunk sem VLAN de gerenciamento
# ---------------------------------------------------------------------------

def regra_e008(projeto: Projeto, r: Resultado) -> None:
    """E008: trunk sem a VLAN de gerenciamento permitida.

    Sem a VLAN de gerenciamento no trunk, nao ha como acessar nenhum equipamento
    atras do enlace. A reparacao custa subir no teto com o Patch de Cabo.
    """
    vlan_gerencia = projeto.vlan_gerencia
    if vlan_gerencia is None:
        return

    por_trunk: dict[str, set[int]] = {}
    for trunk in projeto.trunks:
        por_trunk.setdefault(trunk.chave, set()).add(trunk.vlan_id)

    for chave, vlans in sorted(por_trunk.items()):
        if vlan_gerencia not in vlans:
            r.adicionar(
                "E008",
                f"trunk nao permite a VLAN {vlan_gerencia} de gerenciamento; "
                "os equipamentos atras desse enlace ficam sem gerenciamento",
                onde=chave,
                sugestao=f"Adicione a VLAN {vlan_gerencia} ao trunk.",
                criticidade="media",
            )


# ---------------------------------------------------------------------------
# E009 - Endereco duplicado
# ---------------------------------------------------------------------------

def regra_e009(projeto: Projeto, r: Resultado) -> None:
    """E009: mesmo endereco de gerenciamento em dois switches.

    Endereco duplicado em rede com varios dominios de broadcast gera ARP
    duplicado, e o sintoma e intermitente: o acesso responde ate o outro switch
    ganhar o ARP.
    """
    por_endereco: dict[str, list[str]] = {}
    for switch in projeto.switches.values():
        if not switch.ip_gerencia:
            continue
        por_endereco.setdefault(switch.ip_gerencia, []).append(switch.nome)

    for endereco, switches in sorted(por_endereco.items()):
        if len(switches) > 1:
            r.adicionar(
                "E009",
                f"endereco {endereco} esta em {len(switches)} switches: "
                f"{', '.join(sorted(switches))}",
                onde=endereco,
                sugestao="Atribua um endereco por switch.",
                criticidade="alta",
            )


# ---------------------------------------------------------------------------
# E010 - Community SNMP com escrita
# ---------------------------------------------------------------------------

def regra_e010(projeto: Projeto, r: Resultado) -> None:
    """E010: community SNMP em modo de escrita onde bastava leitura.

    Community em modo escrita e senha de Administrador em texto que travels no
    fio. Quem sniffa o trafaco de gerencia reescreve o equipamento.
    """
    for switch in projeto.switches.values():
        if not switch.snmp_community:
            continue
        if switch.snmp_modo == "read-write":
            r.adicionar(
                "E010",
                f"community SNMP em modo escrita neste equipamento; "
                "community em leitura ja cobre monitoramento",
                onde=f"{switch.nome} ({switch.modelo or 'sem modelo'})",
                sugestao=(
                    "Mude para read-only. Se precisar de escrita, use SNMPv3 "
                    "com autenticacao e cifra."
                ),
                criticidade="alta",
            )


# ---------------------------------------------------------------------------
# E011 - AP sem SSID mapeado
# ---------------------------------------------------------------------------

def regra_e011(projeto: Projeto, r: Resultado) -> None:
    """E011: ponto de acesso anunciando SSID sem VLAN mapeada.

    SSID sem VLAN vai para a rede de gerencia por padrao em quase todo
    equipamento. Na pratica, o hotspot corporativo de visitas aparece na rede
    corporativa.
    """
    for ap in projeto.aps.values():
        orfaos = ap.ssids_sem_vlan
        if not orfaos:
            continue
        r.adicionar(
            "E011",
            f"ponto de acesso anuncia {len(orfaos)} SSID sem VLAN mapeada: "
            f"{', '.join(sorted(orfaos))}. SSID sem VLAN cai na rede de "
            "gerencia por padrao",
            onde=ap.nome,
            sugestao=(
                "Mapeie cada SSID para uma VLAN, de preferencia "
                f"{40}-GUEST para rede de visitantes."
            ),
            criticidade="media",
        )


# ---------------------------------------------------------------------------
# E012 - Mascara fora do plano de enderecamento
# ---------------------------------------------------------------------------

def regra_e012(projeto: Projeto, r: Resultado) -> None:
    """E012: mascara divergente do que o resto das VLANs usa.

    Os enderecos sao planejados por faixa /24. Uma mascara /25 no meio disso
    cria duas redes onde o plano previa uma, e o roteamento passa a depender de
    detalhe que ninguem documentou.
    """
    prefixos: dict[int, list[str]] = {}
    for vlan in projeto.vlans.values():
        prefixos.setdefault(vlan.prefixo, []).append(vlan.nome)

    if len(prefixos) <= 1:
        return

    mais_comum, _conta = max(prefixos.items(), key=lambda par: len(par[1]))
    for prefixo, nomes in sorted(prefixos.items()):
        if prefixo == mais_comum:
            continue
        r.adicionar(
            "E012",
            f"VLANs {', '.join(sorted(nomes))} usam /{prefixo}, e as demais "
            f"usam /{mais_comum}",
            onde=f"prefixo /{prefixo}",
            sugestao=(
                f"Padronize em /{mais_comum}, que e o plano de enderecamento "
                "declarado no projeto."
            ),
            criticidade="media",
        )


#: As 12 regras, na ordem de execucao.
REGRAS: list[tuple[str, Callable[[Projeto, Resultado], None]]] = [
    ("E001", regra_e001),
    ("E002", regra_e002),
    ("E003", regra_e003),
    ("E004", regra_e004),
    ("E005", regra_e005),
    ("E006", regra_e006),
    ("E007", regra_e007),
    ("E008", regra_e008),
    ("E009", regra_e009),
    ("E010", regra_e010),
    ("E011", regra_e011),
    ("E012", regra_e012),
]

#: Catalogo legivel das 12 regras, para documentacao e para o relatorio.
CATALOGO_REGRAS: dict[str, str] = {
    "E001": "Sobreposicao de sub-rede entre VLANs",
    "E002": "Endereco de gateway fora da propria faixa",
    "E003": "Pool DHCP fora da faixa da VLAN",
    "E004": "VLAN usada em interface mas nao declarada",
    "E005": "Trunk referencia VLAN inexistente",
    "E006": "CFTV com rota default para a internet",
    "E007": "ENERGIA-IP com rota default para a internet",
    "E008": "Trunk sem VLAN de gerenciamento permitida",
    "E009": "Endereco duplicado em switch diferente",
    "E010": "Community SNMP em modo escrita",
    "E011": "AP sem SSID mapeado para VLAN",
    "E012": "Mascara de sub-rede inconsistente",
}


def validar(projeto: Projeto) -> Resultado:
    """Executa as 12 regras e devolve o resultado.

    Run the 12 rules and return the outcome.

    Args:
        projeto: Projeto carregado.

    Returns:
        O resultado com as violacoes encontradas.
    """
    resultado = Resultado()
    for codigo, regra in REGRAS:
        resultado.regras_aplicadas.append(codigo)
        regra(projeto, resultado)
    return resultado


def resumo_por_regra(resultado: Resultado) -> dict[str, int]:
    """Conta violacoes por codigo de regra.

    Count violations per rule code.

    Args:
        resultado: Resultado da validacao.

    Returns:
        Dicionario de codigo para quantidade.
    """
    contagem = {codigo: 0 for codigo in CATALOGO_REGRAS}
    for erro in resultado.erros:
        contagem[erro.codigo] = contagem.get(erro.codigo, 0) + 1
    return contagem


def resultado_para_dict(resultado: Resultado) -> dict:
    """Serializa o resultado para JSON.

    Serialise the outcome for JSON.

    Args:
        resultado: Resultado da validacao.

    Returns:
        Dicionario pronto para ``json.dumps``.
    """
    return {
        "aprovado": resultado.aprovado,
        "total_erros": resultado.total,
        "codigos_acionados": resultado.codigos,
        "criticidade": {
            "alta": len(resultado.por_criticidade("alta")),
            "media": len(resultado.por_criticidade("media")),
            "baixa": len(resultado.por_criticidade("baixa")),
        },
        "regras_aplicadas": resultado.regras_aplicadas,
        "erros": [asdict_campos(e) for e in resultado.erros],
    }


def asdict_campos(erro: ErroValidacao) -> dict:
    """Converte um erro em dict.

    Convert an error to a dict.
    """
    return {
        "codigo": erro.codigo,
        "regra": CATALOGO_REGRAS.get(erro.codigo, ""),
        "mensagem": erro.mensagem,
        "onde": erro.onde,
        "sugestao": erro.sugestao,
        "criticidade": erro.criticidade,
    }
