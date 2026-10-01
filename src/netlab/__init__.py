"""netlab - validador de projeto de rede LAN a partir de arquivo declarativo.

LAN design validator driven by a declarative YAML file.

A ideia e antecipar o erro de projeto. Empresa decide topologia em planilha
antes de subir em campo, e o erro de enderecamento so aparece no teto, com a
equipe parada. Esta ferramenta roda o projeto pelas 12 regras antes de existir
cabo, switch e Taking anything out of the wall.

Twelve rules, none of which needs an emulator, a switch or a cable.
"""

from .cargador import (
    ErroDeCarga,
    carregar_projeto,
    resumo_do_projeto,
)
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
from .relatorio import (
    formatar_json,
    formatar_texto,
    imprimir,
    resumo_curto,
)
from .validador import (
    CATALOGO_REGRAS,
    REGRAS,
    ErroValidacao,
    Resultado,
    resumo_por_regra,
    validar,
)

__all__ = [
    # Modelo
    "Vlan",
    "Interface",
    "PortaTrunk",
    "Switch",
    "AccessPoint",
    "PoolDhcp",
    "Rota",
    "Projeto",
    "ErroDeProjeto",
    # Carga
    "carregar_projeto",
    "resumo_do_projeto",
    "ErroDeCarga",
    # Validacao
    "validar",
    "Resultado",
    "ErroValidacao",
    "REGRAS",
    "CATALOGO_REGRAS",
    "resumo_por_regra",
    # Relatorio
    "formatar_texto",
    "formatar_json",
    "imprimir",
    "resumo_curto",
]

__version__ = "1.0.0"