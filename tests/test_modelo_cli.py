"""Testes do modelo, do carregador, do relatorio e da CLI.

Model, loader, report and CLI tests.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from netlab.cargador import (
    ErroDeCarga,
    carregar_projeto,
    resumo_do_projeto,
)
from netlab.cli import construir_parser, main
from netlab.modelo import (
    AccessPoint,
    ErroDeProjeto,
    Interface,
    PoolDhcp,
    PortaTrunk,
    Projeto,
    Switch,
    Vlan,
)
from netlab.relatorio import (
    formatar_json,
    ordenar,
    formatar_texto,
    imprimir,
    resumo_curto,
)
from netlab.validador import validar

RAIZ = Path(__file__).resolve().parent.parent
VALIDO = RAIZ / "dados" / "projeto-predio.yaml"
COM_ERROS = RAIZ / "dados" / "projeto-com-erros.yaml"


class TestVlan:
    """Uma VLAN do projeto."""

    def test_faixa_valida(self) -> None:
        vlan = Vlan(10, "10-CORPORATIVO", "192.168.10.0/24")
        assert vlan.prefixo == 24
        assert vlan.rede_base == "192.168.10.0"

    def test_gateway_esperado(self) -> None:
        assert Vlan(10, "x", "192.168.10.0/24").gateway_esperado == "192.168.10.1"

    def test_rede_privada(self) -> None:
        assert Vlan(10, "x", "192.168.10.0/24").eh_rede_privada

    def test_contem_dentro(self) -> None:
        vlan = Vlan(10, "x", "192.168.10.0/24")
        assert vlan.contem("192.168.10.1")
        assert vlan.contem("192.168.10.254")

    def test_contem_fora(self) -> None:
        vlan = Vlan(10, "x", "192.168.10.0/24")
        assert not vlan.contem("192.168.11.1")
        assert not vlan.contem("10.0.0.1")

    def test_contem_endereco_de_rede(self) -> None:
        vlan = Vlan(10, "x", "192.168.10.0/24")
        assert vlan.contem("192.168.10.0")

    def test_contem_texto_invalido(self) -> None:
        assert not Vlan(10, "x", "192.168.10.0/24").contem("nao-e-ip")

    def test_faixa_invalida(self) -> None:
        with pytest.raises(ErroDeProjeto, match="invalida"):
            Vlan(10, "x", "192.168.10.0/33")

    def test_faixa_sem_ipe_endereco(self) -> None:
        with pytest.raises(ErroDeProjeto):
            Vlan(10, "x", "192.168.10.1/24")

    def test_id_zero(self) -> None:
        with pytest.raises(ErroDeProjeto, match="fora de"):
            Vlan(0, "x", "192.168.10.0/24")

    def test_id_4095(self) -> None:
        with pytest.raises(ErroDeProjeto):
            Vlan(4095, "x", "192.168.10.0/24")

    def test_id_4094_valido(self) -> None:
        assert Vlan(4094, "x", "192.168.10.0/24").id == 4094


class TestInterface:
    """Uma porta de switch."""

    def test_tipos_validos(self) -> None:
        assert Interface("s1", "Gi0/1", "access", 10).tipo == "access"
        assert Interface("s1", "Gi0/1", "trunk").tipo == "trunk"

    def test_tipo_invalido(self) -> None:
        with pytest.raises(ErroDeProjeto, match="invalido"):
            Interface("s1", "Gi0/1", "trunkk", 10)

    def test_chave(self) -> None:
        assert Interface("acc-1a", "Gi0/1", "access", 10).chave == "acc-1a/Gi0/1"

    def test_sem_vlan(self) -> None:
        assert Interface("s1", "Gi0/1", "trunk").vlan is None


class TestPortaTrunk:
    """Uma VLAN permitida em trunk."""

    def test_padroes(self) -> None:
        t = PortaTrunk("core-1", "Te1/0/1", 10)
        assert t.chave == "core-1/Te1/0/1"
        assert t.nativo is False
        assert t.sem_tag is False

    def test_nativo(self) -> None:
        assert PortaTrunk("s", "p", 10, nativo=True).sem_tag is True


class TestSwitch:
    """Um switch."""

    def test_padroes(self) -> None:
        s = Switch("core-1", "C9300", "core")
        assert s.eh_roteador is True
        assert s.snmp_e_gravacao is False

    def test_acesso_nao_roteia(self) -> None:
        assert Switch("acc-1a", "C1200", "acesso").eh_roteador is False

    def test_distribuicao_roteia(self) -> None:
        assert Switch("dist-1a", "C9300", "distribuicao").eh_roteador is True

    def test_snmp_em_escrita(self) -> None:
        s = Switch("s", "m", "acesso", snmp_modo="read-write")
        assert s.snmp_e_gravacao is True


class TestPoolDhcp:
    """Um pool DHCP."""

    def test_faixa(self) -> None:
        pool = PoolDhcp(10, "192.168.10.100", "192.168.10.105")
        assert pool.faixa == [f"192.168.10.{n}" for n in range(100, 106)]

    def test_endereco_unico(self) -> None:
        assert PoolDhcp(10, "192.168.10.1", "192.168.10.1").faixa == ["192.168.10.1"]

    def test_fim_antes_do_inicio(self) -> None:
        assert PoolDhcp(10, "192.168.10.200", "192.168.10.100").faixa == []

    def test_endereco_invalido(self) -> None:
        assert PoolDhcp(10, "abc", "def").faixa == []

    def test_pool_vazio(self) -> None:
        assert PoolDhcp(10, "192.168.10.1", "192.168.10.0").faixa == []


class TestAccessPoint:
    """Um ponto de acesso."""

    def test_ssid_com_vlan(self) -> None:
        ap = AccessPoint("ap-1", ssids={"Rede": 10})
        assert ap.vlan_do_ssid == ("Rede", 10)
        assert ap.ssids_sem_vlan == []

    def test_ssid_sem_vlan(self) -> None:
        ap = AccessPoint("ap-1", ssids={"Rede": 10, "Livre": 0})
        assert ap.ssids_sem_vlan == ["Livre"]
        assert ap.vlan_do_ssid == ("Rede", 10)

    def test_todos_sem_vlan(self) -> None:
        ap = AccessPoint("ap-1", ssids={"A": 0, "B": 0})
        assert ap.vlan_do_ssid is None
        assert ap.ssids_sem_vlan == ["A", "B"]

    def test_sem_ssids(self) -> None:
        assert AccessPoint("ap-1").ssids_sem_vlan == []


class TestProjeto:
    """O projeto inteiro."""

    @pytest.fixture
    def projeto(self) -> Projeto:
        return Projeto(
            nome="p",
            vlans={
                10: Vlan(10, "10-CORPORATIVO", "192.168.10.0/24"),
                40: Vlan(40, "40-GUEST", "192.168.40.0/24"),
                30: Vlan(30, "30-CFTV", "192.168.30.0/24"),
            },
            switches={
                "s1": Switch("s1", "m", "acesso", ip_gerencia="192.168.10.2"),
            },
            interfaces={
                "s1/Gi0/1": Interface("s1", "Gi0/1", "access", 10),
            },
            trunks=[PortaTrunk("s1", "Gi0/24", 10)],
            aps={"ap-1": AccessPoint("ap-1")},
            outros={"servidores": [{"nome": "s"}]},
        )

    def test_vlan_gerencia_por_nome(self, projeto: Projeto) -> None:
        assert projeto.vlan_gerencia == 10

    def test_vlan_gerencia_inexistente(self) -> None:
        assert Projeto().vlan_gerencia is None

    def test_vlans_de_categoria(self, projeto: Projeto) -> None:
        assert [v.id for v in projeto.vlans_de_categoria("40")] == [40]

    def test_categoria_vazia(self, projeto: Projeto) -> None:
        assert projeto.vlans_de_categoria("99") == []

    def test_total_dispositivos(self, projeto: Projeto) -> None:
        # 1 switch + 1 AP + 1 servidor
        assert projeto.total_dispositivos == 3

    def test_trunks_de(self, projeto: Projeto) -> None:
        assert len(projeto.trunks_de("s1")) == 1
        assert projeto.trunks_de("outro") == []

    def test_ports_do_switch(self, projeto: Projeto) -> None:
        assert len(projeto.ports_do_switch("s1")) == 1

    def test_vlan_por_id(self, projeto: Projeto) -> None:
        assert projeto.vlan(40).nome == "40-GUEST"
        assert projeto.vlan(99) is None


class TestCarregador:
    """Leitura do arquivo de projeto."""

    def test_carrega_o_valido(self) -> None:
        p = carregar_projeto(VALIDO)
        assert len(p.vlans) == 5
        assert len(p.switches) == 9

    def test_nome_e_predio(self) -> None:
        assert carregar_projeto(VALIDO).predio

    def test_carrega_trunks(self) -> None:
        assert len(carregar_projeto(VALIDO).trunks) >= 8

    def test_carrega_pools(self) -> None:
        assert len(carregar_projeto(VALIDO).pools) == 5

    def test_carrega_aps_com_ssids(self) -> None:
        aps = carregar_projeto(VALIDO).aps
        assert all(ap.ssids for ap in aps.values())

    def test_carrega_outros_equipamentos(self) -> None:
        outros = carregar_projeto(VALIDO).outros
        assert "firewalls" in outros
        assert "nvrs" in outros

    def test_arquivo_inexistente(self) -> None:
        with pytest.raises(ErroDeCarga, match="nao encontrado"):
            carregar_projeto(RAIZ / "nao-existe.yaml")

    def test_yaml_invalido(self, tmp_path: Path) -> None:
        f = tmp_path / "x.yaml"
        f.write_text("a: [1,\n  b: {", encoding="utf-8")
        with pytest.raises(ErroDeCarga, match="YAML invalido"):
            carregar_projeto(f)

    def test_topo_nao_mapeado(self, tmp_path: Path) -> None:
        f = tmp_path / "x.yaml"
        f.write_text("- a\n- b\n", encoding="utf-8")
        with pytest.raises(ErroDeCarga, match="mapeamento"):
            carregar_projeto(f)

    def test_campo_obrigatorio_ausente(self, tmp_path: Path) -> None:
        f = tmp_path / "x.yaml"
        f.write_text("vlans:\n  - nome: sem-id\n    faixa: 192.168.1.0/24\n",
                     encoding="utf-8")
        with pytest.raises(ErroDeCarga, match="obrigatorio"):
            carregar_projeto(f)

    def test_vlan_duplicada(self, tmp_path: Path) -> None:
        f = tmp_path / "x.yaml"
        f.write_text(
            "vlans:\n"
            "  - {id: 10, nome: a, faixa: 192.168.1.0/24}\n"
            "  - {id: 10, nome: b, faixa: 192.168.2.0/24}\n",
            encoding="utf-8",
        )
        with pytest.raises(ErroDeCarga, match="mais de uma vez"):
            carregar_projeto(f)

    def test_switch_duplicado(self, tmp_path: Path) -> None:
        f = tmp_path / "x.yaml"
        f.write_text(
            "switches:\n"
            "  - {nome: a}\n  - {nome: a}\n",
            encoding="utf-8",
        )
        with pytest.raises(ErroDeCarga, match="mais de uma vez"):
            carregar_projeto(f)

    def test_interface_de_switch_inexistente(self, tmp_path: Path) -> None:
        # Referencia quebrada e erro de digitacao, nao erro de projeto.
        f = tmp_path / "x.yaml"
        f.write_text(
            "interfaces:\n  - {switch: nao-existe, porta: Gi0/1, tipo: access, vlan: 10}\n",
            encoding="utf-8",
        )
        with pytest.raises(ErroDeCarga, match="nao declarado"):
            carregar_projeto(f)

    def test_trunk_de_switch_inexistente(self, tmp_path: Path) -> None:
        f = tmp_path / "x.yaml"
        f.write_text("trunks:\n  - {switch: nao-existe, porta: Te1/1, vlan: 10}\n",
                     encoding="utf-8")
        with pytest.raises(ErroDeCarga, match="nao declarado"):
            carregar_projeto(f)

    def test_ap_de_switch_inexistente(self, tmp_path: Path) -> None:
        f = tmp_path / "x.yaml"
        f.write_text("aps:\n  - {nome: ap-1, switch: nao-existe}\n", encoding="utf-8")
        with pytest.raises(ErroDeCarga, match="nao declarado"):
            carregar_projeto(f)

    def test_trunk_com_vlan_repetida(self, tmp_path: Path) -> None:
        f = tmp_path / "x.yaml"
        f.write_text(
            "switches:\n  - {nome: s1}\n"
            "trunks:\n"
            "  - {switch: s1, porta: Te1/1, vlan: 10}\n"
            "  - {switch: s1, porta: Te1/1, vlan: 10}\n",
            encoding="utf-8",
        )
        with pytest.raises(ErroDeCarga, match="duas vezes"):
            carregar_projeto(f)

    def test_faixa_invalida_vira_erro_de_carga(self, tmp_path: Path) -> None:
        f = tmp_path / "x.yaml"
        f.write_text("vlans:\n  - {id: 10, nome: a, faixa: nao-e-cidr}\n",
                     encoding="utf-8")
        with pytest.raises(ErroDeCarga, match="invalida"):
            carregar_projeto(f)

    def test_projeto_minimo(self, tmp_path: Path) -> None:
        f = tmp_path / "x.yaml"
        f.write_text("nome: minimo\n", encoding="utf-8")
        p = carregar_projeto(f)
        assert p.nome == "minimo"
        assert p.vlans == {}
        assert validar(p).aprovado is True

    def test_resumo_do_projeto(self) -> None:
        texto = resumo_do_projeto(carregar_projeto(VALIDO))
        assert "5 VLANs" in texto
        assert "9 switches" in texto

    def test_padrao_padrao_para_internet(self, tmp_path: Path) -> None:
        # As duas grafias aceitas: padrao_para_internet e default.
        f = tmp_path / "x.yaml"
        f.write_text(
            "rotas:\n"
            "  - {vlan: 10, destino: '0.0.0.0/0', padrao_para_internet: true}\n"
            "  - {vlan: 20, destino: '0.0.0.0/0', default: true}\n",
            encoding="utf-8",
        )
        rotas = carregar_projeto(f).rotas
        assert all(r.padrao_para_internet for r in rotas)


class TestRelatorio:
    """Saida do validador."""

    def test_texto_do_projeto_aprovado(self) -> None:
        p = carregar_projeto(VALIDO)
        texto = formatar_texto(p, validar(p))
        assert "0 erros em 9 dispositivos, 5 VLANs" in texto

    def test_texto_sem_cor_nao_tem_escape(self) -> None:
        p = carregar_projeto(VALIDO)
        assert "\033[" not in formatar_texto(p, validar(p), usar_cor=False)

    def test_texto_com_cor(self) -> None:
        p = carregar_projeto(VALIDO)
        assert "\033[" in formatar_texto(p, validar(p), usar_cor=True)

    def test_texto_lista_os_codigos(self) -> None:
        p = carregar_projeto(COM_ERROS)
        texto = formatar_texto(p, validar(p))
        for codigo in validar(p).codigos:
            assert codigo in texto

    def test_texto_mostra_a_sugestao(self) -> None:
        p = carregar_projeto(COM_ERROS)
        texto = formatar_texto(p, validar(p))
        assert "sugestao:" in texto

    def test_json_valido(self) -> None:
        p = carregar_projeto(VALIDO)
        dados = json.loads(formatar_json(p, validar(p)))
        assert dados["aprovado"] is True
        assert dados["total_erros"] == 0

    def test_json_tem_o_projeto(self) -> None:
        p = carregar_projeto(VALIDO)
        dados = json.loads(formatar_json(p, validar(p)))
        assert dados["projeto"]["switches"] == 9
        assert dados["projeto"]["vlans"] == 5

    def test_json_tem_o_catalogo(self) -> None:
        p = carregar_projeto(VALIDO)
        dados = json.loads(formatar_json(p, validar(p)))
        assert len(dados["catalogo_regras"]) == 12

    def test_json_lista_criticidade(self) -> None:
        p = carregar_projeto(COM_ERROS)
        dados = json.loads(formatar_json(p, validar(p)))
        assert dados["criticidade"]["alta"] > 0
        assert dados["aprovado"] is False

    def test_json_com_erro_tem_regra_nomeada(self) -> None:
        p = carregar_projeto(COM_ERROS)
        dados = json.loads(formatar_json(p, validar(p)))
        assert dados["erros"][0]["regra"]

    def test_imprimir_codigo_de_saida(self) -> None:
        p = carregar_projeto(VALIDO)
        assert imprimir(p, validar(p), saida=io.StringIO()) == 0

    def test_imprimir_codigo_com_erro(self) -> None:
        p = carregar_projeto(COM_ERROS)
        assert imprimir(p, validar(p), saida=io.StringIO()) == 1

    def test_resumo_curto(self) -> None:
        assert resumo_curto(validar(carregar_projeto(VALIDO))) == "aprovado: nenhum erro"
        assert "12 erro(s)" in resumo_curto(validar(carregar_projeto(COM_ERROS)))

    def test_ordena_por_criticidade(self) -> None:
        p = carregar_projeto(COM_ERROS)
        erros = ordenar(validar(p).erros)
        ordem = {"alta": 0, "media": 1, "baixa": 2}
        for a, b in zip(erros, erros[1:]):
            assert ordem[a.criticidade] <= ordem[b.criticidade]

    def test_ordenado_agrupa_por_codigo(self) -> None:
        p = carregar_projeto(COM_ERROS)
        erros = ordenar(validar(p).erros)
        # Dentro de uma mesma criticidade, os codigos sobem. Atravessar
        # criticidade reinicia a sequencia, porque a ordem e
        # (criticidade, codigo) e nao so codigo.
        for criticidade in ("alta", "media", "baixa"):
            codigos = [e.codigo for e in erros if e.criticidade == criticidade]
            assert codigos == sorted(codigos), criticidade

    def test_relatorio_lista_alta_antes_de_media(self) -> None:
        p = carregar_projeto(COM_ERROS)
        texto = formatar_texto(p, validar(p))
        assert texto.index("E002") < texto.index("E008")


class TestCli:
    """A linha de comando."""

    def test_validar_aprovado(self, capsys) -> None:
        assert main(["validar", str(VALIDO)]) == 0
        assert "0 erros" in capsys.readouterr().out

    def test_validar_com_erros(self, capsys) -> None:
        assert main(["validar", str(COM_ERROS)]) == 1

    def test_validar_json(self, capsys) -> None:
        assert main(["validar", str(VALIDO), "--formato", "json"]) == 0
        dados = json.loads(capsys.readouterr().out)
        assert dados["aprovado"] is True

    def test_arquivo_inexistente(self, capsys) -> None:
        # Codigo 2 e separado de 1: arquivo corrompido nao e projeto ruim.
        assert main(["validar", "nao-existe.yaml"]) == 2
        assert "nao encontrado" in capsys.readouterr().err

    def test_grava_saida(self, tmp_path: Path, capsys) -> None:
        destino = tmp_path / "r.txt"
        assert main(["validar", str(VALIDO), "--saida", str(destino)]) == 0
        assert "0 erros" in destino.read_text(encoding="utf-8")

    def test_grava_json(self, tmp_path: Path) -> None:
        destino = tmp_path / "r.json"
        main(["validar", str(VALIDO), "--json-saida", str(destino)])
        assert json.loads(destino.read_text(encoding="utf-8"))["aprovado"] is True

    def test_saida_json_em_arquivo(self, tmp_path: Path) -> None:
        destino = tmp_path / "r.json"
        main(["validar", str(COM_ERROS), "--formato", "json",
              "--saida", str(destino)])
        assert json.loads(destino.read_text(encoding="utf-8"))["aprovado"] is False

    def test_saida_cria_diretorio(self, tmp_path: Path) -> None:
        destino = tmp_path / "a" / "b" / "r.txt"
        main(["validar", str(VALIDO), "--saida", str(destino)])
        assert destino.exists()

    def test_regras(self, capsys) -> None:
        assert main(["regras"]) == 0
        saida = capsys.readouterr().out
        assert "E001" in saida
        assert "12 regras" in saida

    def test_resumir(self, capsys) -> None:
        assert main(["resumir", str(VALIDO)]) == 0
        saida = capsys.readouterr().out
        assert "VLANs: 5" in saida
        assert "Switches: 9" in saida

    def test_resumir_arquivo_invalido(self, capsys) -> None:
        assert main(["resumir", "nao-existe.yaml"]) == 2

    def test_ajuda(self) -> None:
        with pytest.raises(SystemExit) as exc:
            main(["--help"])
        assert exc.value.code == 0

    @pytest.mark.parametrize("comando", ["validar", "regras", "resumir"])
    def test_ajuda_de_cada_comando(self, comando: str) -> None:
        with pytest.raises(SystemExit) as exc:
            main([comando, "--help"])
        assert exc.value.code == 0

    def test_sem_subcomando(self) -> None:
        with pytest.raises(SystemExit) as exc:
            main([])
        assert exc.value.code != 0

    def test_subcomando_desconhecido(self) -> None:
        with pytest.raises(SystemExit):
            main(["nao-existe"])

    def test_formato_invalido(self) -> None:
        with pytest.raises(SystemExit):
            main(["validar", str(VALIDO), "--formato", "xml"])

    def test_parser_padroes(self) -> None:
        args = construir_parser().parse_args(["validar", "x.yaml"])
        assert args.formato == "texto"
        assert args.saida is None

    def test_saida_utf8_valida(self, tmp_path: Path) -> None:
        destino = tmp_path / "r.txt"
        main(["validar", str(COM_ERROS), "--saida", str(destino)])
        destino.read_bytes().decode("utf-8")