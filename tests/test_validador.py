"""Testes das 12 regras de validacao.

Validation rule tests.

Cada regra tem um caso que dispara e um caso que **nao** dispara. O segundo e
o que importa: uma regra que nunca erra acerta tudo, e um validador approve
sempre nao serve para nada.

O arquivo `dados/projeto-com-erros.yaml` tem de produzir os 12 codigos. Esse e o
teste que prova que o validador detecta erro em vez de apenas aprovar.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from netlab.cargador import carregar_projeto
from netlab.modelo import Projeto, Vlan
from netlab.validador import (
    CATALOGO_REGRAS,
    REGRAS,
    validar,
)

RAIZ = Path(__file__).resolve().parent.parent
PROJETO_VALIDO = RAIZ / "dados" / "projeto-predio.yaml"
PROJETO_COM_ERROS = RAIZ / "dados" / "projeto-com-erros.yaml"


@pytest.fixture(scope="module")
def valido() -> Projeto:
    """O projeto que deve passar nas 12 regras.

    The project that must pass all 12 rules.
    """
    return carregar_projeto(PROJETO_VALIDO)


@pytest.fixture(scope="module")
def com_erros() -> Projeto:
    """O projeto com um caso de cada regra plantado.

    The project with one planted case per rule.
    """
    return carregar_projeto(PROJETO_COM_ERROS)


def clonar(projeto: Projeto) -> Projeto:
    """Copia rasa do projeto, para mutar em um teste.

    Shallow copy of the project, to mutate in a test.
    """
    novo = Projeto(
        nome=projeto.nome,
        predio=projeto.predio,
        vlans=copy.deepcopy(projeto.vlans),
        switches=copy.deepcopy(projeto.switches),
        interfaces=copy.deepcopy(projeto.interfaces),
        trunks=copy.deepcopy(projeto.trunks),
        pools=copy.deepcopy(projeto.pools),
        rotas=copy.deepcopy(projeto.rotas),
        aps=copy.deepcopy(projeto.aps),
        outros=copy.deepcopy(projeto.outros),
    )
    return novo


def codigos(projeto: Projeto) -> list[str]:
    """Codigos disparados por um projeto.

    Codes triggered by a project.
    """
    return validar(projeto).codigos


class TestCatalogoDeRegras:
    """O conjunto de regras."""

    def test_tem_doze_regras(self) -> None:
        assert len(REGRAS) == 12

    def test_codigos_de_E001_a_E012(self) -> None:
        assert [c for c, _ in REGRAS] == [f"E{n:03d}" for n in range(1, 13)]

    def test_catalogo_completo(self) -> None:
        assert len(CATALOGO_REGRAS) == 12
        assert all(descricao for descricao in CATALOGO_REGRAS.values())

    def test_todas_as_regras_rodam(self, valido: Projeto) -> None:
        resultado = validar(valido)
        assert len(resultado.regras_aplicadas) == 12

    def test_codigos_acionados_sao_do_catalogo(self, com_erros: Projeto) -> None:
        for codigo in codigos(com_erros):
            assert codigo in CATALOGO_REGRAS


class TestProjetoValido:
    """O arquivo de projeto sem erro."""

    def test_passa_sem_erro(self, valido: Projeto) -> None:
        resultado = validar(valido)
        assert resultado.aprovado, [str(e) for e in resultado.erros]

    def test_zero_erros(self, valido: Projeto) -> None:
        assert validar(valido).total == 0

    def test_cinco_vlans(self, valido: Projeto) -> None:
        assert len(valido.vlans) == 5

    def test_nove_switches(self, valido: Projeto) -> None:
        assert len(valido.switches) == 9

    def test_dois_aps(self, valido: Projeto) -> None:
        assert len(valido.aps) == 2

    def test_vlans_rfc1918(self, valido: Projeto) -> None:
        for vlan in valido.vlans.values():
            assert vlan.eh_rede_privada
            assert vlan.prefixo == 24

    def test_todas_as_faixas_disjuntas(self, valido: Projeto) -> None:
        for codigo in codigos(valido):
            assert codigo != "E001"

    def test_cftv_sem_internet(self, valido: Projeto) -> None:
        cftv = valido.vlan(30)
        rotas = [r for r in valido.rotas if r.vlan_id == cftv.id]
        assert all(not r.padrao_para_internet for r in rotas)

    def test_energia_sem_internet(self, valido: Projeto) -> None:
        rotas = [r for r in valido.rotas if r.vlan_id == 50]
        assert all(not r.padrao_para_internet for r in rotas)

    def test_todo_trunk_tem_vlan_de_gerencia(self, valido: Projeto) -> None:
        gerencia = valido.vlan_gerencia
        for chave in {t.chave for t in valido.trunks}:
            vlans = {t.vlan_id for t in valido.trunks if t.chave == chave}
            assert gerencia in vlans, chave

    def test_pools_dentro_das_faixas(self, valido: Projeto) -> None:
        for vlan_id, pool in valido.pools.items():
            vlan = valido.vlan(vlan_id)
            assert all(vlan.contem(e) for e in pool.faixa), vlan_id

    def test_todo_ssid_mapeado(self, valido: Projeto) -> None:
        for ap in valido.aps.values():
            assert ap.ssids_sem_vlan == []

    def test_snmp_so_leitura(self, valido: Projeto) -> None:
        assert all(not s.snmp_e_gravacao for s in valido.switches.values())

    def test_um_endereco_por_switch(self, valido: Projeto) -> None:
        enderecos = [
            s.ip_gerencia for s in valido.switches.values() if s.ip_gerencia
        ]
        assert len(enderecos) == len(set(enderecos))


class TestProjetoComErros:
    """O arquivo com um caso de cada regra."""

    def test_detecta_as_doze_regras(self, com_erros: Projeto) -> None:
        assert codigos(com_erros) == [f"E{n:03d}" for n in range(1, 13)]

    def test_falha(self, com_erros:Projeto) -> None:
        assert validar(com_erros).aprovado is False

    def test_pelo_menos_seis_erros(self, com_erros: Projeto) -> None:
        assert validar(com_erros).total >= 6

    def test_tem_erro_de_criticidade_alta(self, com_erros: Projeto) -> None:
        assert validar(com_erros).por_criticidade("alta")

    def test_todo_erro_tem_sugestao(self, com_erros: Projeto) -> None:
        for erro in validar(com_erros).erros:
            assert erro.sugestao, erro.codigo

    def test_todo_erro_tem_onde(self, com_erros: Projeto) -> None:
        for erro in validar(com_erros).erros:
            assert erro.onde, erro.codigo

    def test_um_erro_por_regra_no_maximo(self, com_erros: Projeto) -> None:
        # Relatorio com 150 linhas do mesmo problema nao e lido por ninguem.
        total = validar(com_erros).total
        assert total <= 20

    def test_erro_mais_grave_primeiro(self, com_erros: Projeto) -> None:
        erros = validar(com_erros).erros
        assert erros[0].criticidade == "alta"


class TestE001SobreposicaoDeSubRede:
    """E001: duas VLANs com faixa que se sobrepoem."""

    def test_detecta_sobreposicao(self, com_erros: Projeto) -> None:
        assert len(validar(com_erros).por_codigo("E001")) == 1

    def test_nao_compara_texto(self, valido: Projeto) -> None:
        # 192.168.20.0/24 contra 192.168.20.0/25: as notacoes sao DIFERENTES,
        # entao comparar string nao acha nada. So aritmetica de sub-rede acha.
        p = clonar(valido)
        p.vlans[40] = type(p.vlans[10])(
            id=40, nome="40-GUEST", faixa_ip="192.168.20.0/25"
        )
        assert "E001" in validar(p).codigos

    def test_faixas_adjacentes_nao_sobrepoem(self, valido: Projeto) -> None:
        p = clonar(valido)
        p.vlans[40] = type(p.vlans[10])(
            id=40, nome="40-GUEST", faixa_ip="192.168.11.0/24"
        )
        assert "E001" not in validar(p).codigos

    def test_faixa_contida_sobrepoem(self, valido: Projeto) -> None:
        p = clonar(valido)
        p.vlans[40] = type(p.vlans[10])(
            id=40, nome="40-GUEST", faixa_ip="192.168.10.0/26"
        )
        assert "E001" in validar(p).codigos

    def test_uma_so_vlan_nao_acusa(self) -> None:
        p = Projeto(nome="minimo")
        p.vlans[10] = Vlan(id=10, nome="10-CORPORATIVO", faixa_ip="192.168.10.0/24")
        assert "E001" not in validar(p).codigos


class TestE002GatewayForaDaFaixa:
    """E002: endereco de gerenciamento fora da faixa."""

    def test_detecta(self, com_erros: Projeto) -> None:
        assert len(validar(com_erros).por_codigo("E002")) == 1

    def test_gateway_dentro_da_faixa_passa(self, valido: Projeto) -> None:
        assert "E002" not in validar(valido).codigos

    def test_gateway_fora_da_faixa_acusa(self, valido: Projeto) -> None:
        p = clonar(valido)
        p.switches["core-1"].ip_gerencia = "10.0.0.5"
        erros = validar(p).por_codigo("E002")
        assert len(erros) == 1
        assert "core-1" in erros[0].onde

    def test_switch_sem_ip_nao_acusa(self, valido: Projeto) -> None:
        p = clonar(valido)
        p.switches["core-1"].ip_gerencia = None
        assert "E002" not in validar(p).codigos

    def test_terceira_faixa_diferente_acusa(self, valido: Projeto) -> None:
        # 192.168.99.4 tem o mesmo primeiro octeto que 192.168.10.0/24 e mesmo
        # assim esta fora. Comparar so os dois primeiros octetos deixaria
        # passar.
        p = clonar(valido)
        p.switches["core-1"].ip_gerencia = "192.168.99.4"
        assert "E002" in validar(p).codigos


class TestE003PoolDhcp:
    """E003: pool DHCP fora da faixa da VLAN."""

    def test_detecta(self, com_erros: Projeto) -> None:
        assert len(validar(com_erros).por_codigo("E003")) == 1

    def test_um_erro_por_pool(self, com_erros: Projeto) -> None:
        # O pool inteiro fora da faixa e um erro, nao um por endereco.
        erros = validar(com_erros).por_codigo("E003")
        assert len(erros) == 1
        assert "endereco(s)" in erros[0].mensagem

    def test_resume_o_intervalo(self, com_erros: Projeto) -> None:
        erro = validar(com_erros).por_codigo("E003")[0]
        assert "ate" in erro.mensagem

    def test_pool_dentro_da_faixa_passa(self, valido: Projeto) -> None:
        assert "E003" not in validar(valido).codigos

    def test_pool_que_atravessa_a_fim_da_faixa(self, valido: Projeto) -> None:
        p = clonar(valido)
        p.pools[10].fim = "192.168.11.50"
        erros = validar(p).por_codigo("E003")
        assert len(erros) == 1
        assert "ate 192.168.11.50" in erros[0].mensagem


class TestE004VlanNaoDeclarada:
    """E004: porta access em VLAN inexistente."""

    def test_detecta(self, com_erros: Projeto) -> None:
        assert len(validar(com_erros).por_codigo("E004")) == 1

    def test_vlan_declarada_passa(self, valido: Projeto) -> None:
        assert "E004" not in validar(valido).codigos

    def test_porta_trunk_nao_e_chequeada_por_esta(self, valido: Projeto) -> None:
        # Um trunk com VLAN errada e E005, nao E004. As duas would report.
        p = clonar(valido)
        p.trunks[0].vlan_id = 77
        codigos_achados = validar(p).codigos
        assert "E005" in codigos_achados
        assert "E004" not in codigos_achados


class TestE005TrunkVlanInexistente:
    """E005: trunk permitindo VLAN inexistente."""

    def test_detecta(self, com_erros: Projeto) -> None:
        assert len(validar(com_erros).por_codigo("E005")) == 1

    def test_trunk_valido_passa(self, valido: Projeto) -> None:
        assert "E005" not in validar(valido).codigos

    def test_vlan_que_so_existe_no_trunk(self, valido: Projeto) -> None:
        p = clonar(valido)
        p.trunks[0].vlan_id = 88
        assert "E005" in validar(p).codigos


class TestE006eE007Segmentacao:
    """E006 e E007: categoria sem rota para a internet."""

    def test_e006_detecta_cftv(self, com_erros: Projeto) -> None:
        assert len(validar(com_erros).por_codigo("E006")) == 1

    def test_e007_detecta_energia(self, com_erros: Projeto) -> None:
        assert len(validar(com_erros).por_codigo("E007")) == 1

    def test_cftv_sem_internet_passa(self, valido: Projeto) -> None:
        assert "E006" not in validar(valido).codigos

    def test_energia_sem_internet_passa(self, valido: Projeto) -> None:
        assert "E007" not in validar(valido).codigos

    def test_rota_nao_default_nao_acusa(self, valido: Projeto) -> None:
        p = clonar(valido)
        for rota in p.rotas:
            if rota.vlan_id == 30:
                rota.padrao_para_internet = True
        # Agora so CFTV esta com rota default.
        codigos_achados = validar(p).codigos
        assert "E006" in codigos_achados
        assert "E007" not in codigos_achados

    def test_depende_da_categoria_do_nome(self, valido: Projeto) -> None:
        # A regra olha o prefixo numerico do nome, nao o id. Uma VLAN que deixa
        # de se chamar 30-alguma-coisa deixa de contar como CFTV.
        p = clonar(valido)
        p.vlans[30] = type(p.vlans[30])(
            id=30, nome="VISITANTES", faixa_ip="192.168.30.0/24"
        )
        for rota in p.rotas:
            if rota.vlan_id == 30:
                rota.padrao_para_internet = True
        assert "E006" not in validar(p).codigos

    def test_outra_categoria_30_ainda_acusa(self, valido: Projeto) -> None:
        # O prefixo e o que define a categoria, entao 30-VISITANTES continua
        # sendoLAN 30 e continua entrando na regra.
        p = clonar(valido)
        p.vlans[30] = type(p.vlans[30])(
            id=30, nome="30-VISITANTES", faixa_ip="192.168.30.0/24"
        )
        for rota in p.rotas:
            if rota.vlan_id == 30:
                rota.padrao_para_internet = True
        assert "E006" in validar(p).codigos

    def test_ambos_disparam_no_mesmo_projeto(self, com_erros: Projeto) -> None:
        assert {"E006", "E007"} <= set(validar(com_erros).codigos)

    def test_mensagem_explica_o_risco(self, com_erros: Projeto) -> None:
        erro = validar(com_erros).por_codigo("E006")[0]
        assert "internet" in erro.mensagem
        assert erro.sugestao


class TestE008TrunkSemGerencia:
    """E008: trunk sem a VLAN de gerenciamento."""

    def test_detecta(self, com_erros: Projeto) -> None:
        assert len(validar(com_erros).por_codigo("E008")) == 1

    def test_trunk_com_gerencia_passa(self, valido: Projeto) -> None:
        assert "E008" not in validar(valido).codigos

    def test_remove_a_gerencia_do_trunk(self, valido: Projeto) -> None:
        p = clonar(valido)
        gerencia = p.vlan_gerencia
        p.trunks = [t for t in p.trunks if t.vlan_id != gerencia]
        erros = validar(p).por_codigo("E008")
        assert len(erros) >= 1

    def test_um_erro_por_trunk(self, valido: Projeto) -> None:
        p = clonar(valido)
        gerencia = p.vlan_gerencia
        # Um erro por porta trunk, e nao por declaracao de VLAN.
        chaves = {t.chave for t in p.trunks if t.vlan_id != gerencia}
        p.trunks = [t for t in p.trunks if t.vlan_id != gerencia]
        erros = validar(p).por_codigo("E008")
        assert len(erros) == len(chaves)


class TestE009EnderecoDuplicado:
    """E009: mesmo endereco em dois switches."""

    def test_detecta(self, com_erros: Projeto) -> None:
        assert len(validar(com_erros).por_codigo("E009")) == 1

    def test_endereco_unico_passa(self, valido: Projeto) -> None:
        assert "E009" not in validar(valido).codigos

    def test_cita_os_dois_switches(self, com_erros: Projeto) -> None:
        erro = validar(com_erros).por_codigo("E009")[0]
        assert "acc-1b" in erro.mensagem
        assert "dist-1a" in erro.mensagem

    def test_tres_switches_com_o_mesmo_ip(self, valido: Projeto) -> None:
        p = clonar(valido)
        ip = p.switches["core-1"].ip_gerencia
        p.switches["acc-1a"].ip_gerencia = ip
        p.switches["acc-1b"].ip_gerencia = ip
        erros = validar(p).por_codigo("E009")
        assert len(erros) == 1
        assert "3 switches" in erros[0].mensagem

    def test_switch_sem_ip_nao_entra_na_conta(self, valido: Projeto) -> None:
        p = clonar(valido)
        p.switches["acc-1a"].ip_gerencia = None
        p.switches["acc-1b"].ip_gerencia = None
        assert "E009" not in validar(p).codigos


class TestE010SnmpEmEscrita:
    """E010: community SNMP em modo escrita."""

    def test_detecta(self, com_erros: Projeto) -> None:
        assert len(validar(com_erros).por_codigo("E010")) == 1

    def test_read_only_passa(self, valido: Projeto) -> None:
        assert "E010" not in validar(valido).codigos

    def test_muda_para_escrita(self, valido: Projeto) -> None:
        p = clonar(valido)
        p.switches["core-1"].snmp_modo = "read-write"
        erros = validar(p).por_codigo("E010")
        assert len(erros) == 1
        assert "core-1" in erros[0].onde

    def test_switch_sem_community_nao_acusa(self, valido: Projeto) -> None:
        p = clonar(valido)
        p.switches["core-1"].snmp_community = None
        p.switches["core-1"].snmp_modo = "read-write"
        assert "E010" not in validar(p).codigos

    def test_sugere_snmpv3(self, valido: Projeto) -> None:
        p = clonar(valido)
        p.switches["core-1"].snmp_modo = "read-write"
        assert "SNMPv3" in validar(p).por_codigo("E010")[0].sugestao


class TestE011ApSemSsid:
    """E011: SSID sem VLAN mapeada."""

    def test_detecta(self, com_erros: Projeto) -> None:
        assert len(validar(com_erros).por_codigo("E011")) == 1

    def test_todo_mapeado_passa(self, valido: Projeto) -> None:
        assert "E011" not in validar(valido).codigos

    def test_ssid_com_vlan_zero_acusa(self, valido: Projeto) -> None:
        p = clonar(valido)
        p.aps["ap-visitantes-1a"].ssids["Livre"] = 0
        erros = validar(p).por_codigo("E011")
        assert len(erros) == 1
        assert "Livre" in erros[0].mensagem

    def test_ap_com_todos_mapeados_passa(self, valido: Projeto) -> None:
        p = clonar(valido)
        p.aps["ap-visitantes-1a"].ssids = {"Rede": 10}
        assert "E011" not in validar(p).codigos

    def test_sugere_vlan_de_visitantes(self, com_erros: Projeto) -> None:
        assert "40-GUEST" in validar(com_erros).por_codigo("E011")[0].sugestao


class TestE012MascaraDivergente:
    """E012: mascara fora do plano de enderecamento."""

    def test_detecta(self, com_erros: Projeto) -> None:
        assert len(validar(com_erros).por_codigo("E012")) == 1

    def test_mascara_uniforme_passa(self, valido: Projeto) -> None:
        assert "E012" not in validar(valido).codigos

    def test_uma_mascara_diferente_acusa(self, valido: Projeto) -> None:
        p = clonar(valido)
        p.vlans[40] = type(p.vlans[40])(
            id=40, nome="40-GUEST", faixa_ip="192.168.40.0/25"
        )
        erros = validar(p).por_codigo("E012")
        assert len(erros) == 1
        assert "/25" in erros[0].mensagem

    def test_mascara_menor_que_as_outras_acusa(self, valido: Projeto) -> None:
        p = clonar(valido)
        for vlan in p.vlans.values():
            if vlan.id == 40:
                p.vlans[40] = type(vlan)(
                    id=40, nome="40-GUEST", faixa_ip="192.168.40.0/25"
                )
        assert "E012" in validar(p).codigos

    def test_sugere_padronizar(self, valido: Projeto) -> None:
        p = clonar(valido)
        p.vlans[40] = type(p.vlans[40])(
            id=40, nome="40-GUEST", faixa_ip="192.168.40.0/25"
        )
        assert "/24" in validar(p).por_codigo("E012")[0].sugestao


class TestResultado:
    """Estrutura de resultado."""

    def test_aprovado_sem_erros(self, valido: Projeto) -> None:
        r = validar(valido)
        assert r.aprovado is True
        assert r.total == 0

    def test_codigos_distintos(self, com_erros: Projeto) -> None:
        codigos_achados = validar(com_erros).codigos
        assert len(codigos_achados) == len(set(codigos_achados))

    def test_por_codigo_filtra(self, com_erros: Projeto) -> None:
        r = validar(com_erros)
        total = sum(len(r.por_codigo(c)) for c in r.codigos)
        assert total == r.total

    def test_por_criticidade_soma(self, com_erros: Projeto) -> None:
        r = validar(com_erros)
        soma = sum(len(r.por_criticidade(c)) for c in ("alta", "media", "baixa"))
        assert soma == r.total

    def test_texto_do_erro(self, com_erros: Projeto) -> None:
        erro = validar(com_erros).erros[0]
        assert erro.codigo in str(erro)
        assert erro.mensagem in str(erro)


def _vlan_exemplo() -> dict:
    """Dicionario de uma VLAN minima, para o teste de uma VLAN so."""
    return {"id": 10, "nome": "10-CORPORATIVO", "faixa_ip": "192.168.10.0/24"}