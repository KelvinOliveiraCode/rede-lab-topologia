# rede-lab-topologia

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white)
![Dependencia](https://img.shields.io/badge/deps-PyYAML%20apenas-blue?style=flat-square)
![Licenca](https://img.shields.io/badge/licenca-MIT-yellow?style=flat-square)
![Plataforma](https://img.shields.io/badge/plataforma-Windows%20Linux%20macOS-blue?style=flat-square)
![Testes](https://img.shields.io/badge/testes-181%20passando-brightgreen?style=flat-square)
![Cobertura](https://img.shields.io/badge/cobertura-96%25-brightgreen?style=flat-square)

Validador de projeto de rede LAN a partir de um arquivo declarativo em YAML. Lê VLANs, faixas de endereço, trunks, pools DHCP e rotas, e devolve as violações antes de existir cabo, switch ou teto aberto. Sem emulador, sem equipamento e sem rede: doze regras, nenhuma precisa de nada ligado.

## Problema / Por que existe

Uma empresa decide a topologia em planilha antes de subir em campo. O erro de endereçamento só aparece depois, com a equipe parada e o patch de cabo na mão. Nada no validador exige hardware: é um arquivo de texto e doze regras.

A primeira versão desta ferramenta não funcionava por três motivos de leitura de código:

- Sobreposição de sub-rede comparada como texto. `192.168.20.0/24` e `192.168.20.0/25` são notações diferentes, então uma comparação de string não encontra sobreposição. Mas as redes se sobrepoem: o `/25` está dentro do `/24`. A correção usa `ipaddress.IPv4Network.overlaps()`, da biblioteca padrão.
- Gateway validado por convenção, não por regra. A versão exigia que o endereço terminasse em `.1`, o que é convenção: um gateway em `.254` numa `/24` é válido. E comparava só os dois primeiros octetos, o que deixava passar `192.168.99.4` numa VLAN `192.168.10.0/24`.
- Pool DHCP relatado um erro por endereço. Um pool de 150 endereços fora da faixa gerava 150 achados iguais. Ninguém lê um relatório assim. A regra agora relata um erro por pool, com o intervalo afetado.

O arquivo de dados também não existia. O código de seis módulos estava pronto, mas `dados/projeto-predio.yaml` não, então nada podia ser executado.

## O que faz

Lê um projeto de rede em YAML e executa doze regras de validação:

| Código | Regra |
| --- | --- |
| E001 | Sobreposição de sub-rede entre VLANs, por aritmética de sub-rede, não por texto |
| E002 | Endereço de gerenciamento fora da faixa da própria VLAN |
| E003 | Pool DHCP fora da faixa da VLAN, um erro por pool |
| E004 | VLAN usada em interface mas não declarada |
| E005 | Trunk referencia VLAN inexistente |
| E006 | CFTV com rota default para a internet |
| E007 | ENERGIA-IP com rota default para a internet |
| E008 | Trunk sem VLAN de gerenciamento permitida |
| E009 | Endereço duplicado em switches diferentes |
| E010 | Community SNMP em modo de escrita |
| E011 | Ponto de acesso com SSID sem VLAN mapeada |
| E012 | Máscara de sub-rede inconsistente com o plano de endereçamento |

Saída em texto no terminal, colorido quando há terminal, ou JSON. Códigos de saída: 0 aprovado, 1 violação de projeto, 2 arquivo não pôde ser lido. Em automação, arquivo corrompido e projeto ruim não saem iguais.

O repositório inclui dois arquivos de projeto:

- `dados/projeto-predio.yaml`: prédio comercial de três andares, cinco VLANs RFC 1918, nove switches em três camadas, dois pontos de acesso, firewall, dois servidores, NVR, coletor SNMP e medidor de energia. Passa nas doze regras com zero erros.
- `dados/projeto-com-erros.yaml`: o mesmo desenho com um caso plantado de cada regra. Dispara as doze regras e devolve código de saída 1. É o arquivo que prova que o validador detecta erro, não apenas aprova.

Exemplo de uso

```
python -m netlab validar dados/projeto-predio.yaml
```

Saída esperada:

```
Projeto: projeto-predio - Edificio Predial Norte - 3 andares
5 VLANs | 9 switches | 13 portas | 2 APs | 12 regras aplicadas

0 erros em 9 dispositivos, 5 VLANs
```

Código de saída 0.

```
python -m netlab validar dados/projeto-com-erros.yaml
```

Saída esperada: `12 erro(s) encontrado(s): 9 alta, 3 media`, uma linha por código de regra, com local e sugestão de cada um, e código de saída 1.

## Stack

- Python 3.10 ou superior
- PyYAML 6.0 ou superior: única dependência de runtime
- `ipaddress` da biblioteca padrão: aritmética de sub-rede, sobreposição de CIDR e teste de pertencimento de endereço
- pytest e pytest-cov: dependências de desenvolvimento
- setuptools: build e empacotamento em layout `src`

Não há emulador, simulador de rede nem biblioteca de fabricante. Tudo roda sobre o que o arquivo declara.

## Como funciona

1. O cargador (`src/netlab/cargador.py`) lê o YAML e constrói o modelo de domínio: `Vlan`, `Switch`, `Interface`, `PortaTrunk`, `PoolDhcp`, `Rota`, `AccessPoint` e `Projeto`. Recusa tipo de porta desconhecido, faixa que não é CIDR e referência a equipamento não declarado, antes de qualquer regra rodar.
2. O validador (`src/netlab/validador.py`) executa as doze regras em ordem sobre o modelo, usando `ipaddress.IPv4Network.overlaps()` para sobreposição de sub-rede.
3. O relatório (`src/netlab/relatorio.py`) emite texto no terminal ou JSON, com uma entrada por código de regra, local da violação e sugestão de correção. Um erro por problema, não um por ocorrência: um pool com 30 endereços fora da faixa gera um achado, não 30.

Subcomandos da CLI:

| Comando | O que faz |
| --- | --- |
| `validar ARQUIVO` | Valida o projeto e lista as violações |
| `resumir ARQUIVO` | Mostra a estrutura sem validar |
| `regras` | Lista as doze regras |

Argumentos de `validar`: `--formato texto|json`, `--saida ARQUIVO` e `--json-saida ARQUIVO`.

## Como rodar

Requer Python 3.10 ou superior. Funciona em Windows, Linux e macOS.

```
git clone https://github.com/kelvinoliveira/netlab.git
cd netlab
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Valide o projeto de referência:

```
python -m netlab validar dados/projeto-predio.yaml
```

Saída: `0 erros em 9 dispositivos, 5 VLANs`, código de saída 0.

Veja o projeto com erros plantados:

```
python -m netlab validar dados/projeto-com-erros.yaml
```

Saída: as doze violações, código de saída 1.

Outros comandos

```
python -m netlab resumir projeto.yaml     # estrutura, sem validar
python -m netlab regras                   # as 12 regras
python -m netlab validar projeto.yaml --formato json   # saída em JSON
python -m netlab validar projeto.yaml --saida rel.txt  # grava em arquivo
python -m netlab validar projeto.yaml --json-saida r.json
```

Testes e verificação

```
python -m pytest --cov=netlab --cov-report=term-missing
python tools/verificar_encoding.py
python tools/verificar_aceite.py
```

- 181 testes, 96% de cobertura, piso configurado em 70%.
- `verificar_encoding.py` falha se algum arquivo tiver caractere de substituição (U+FFFD) ou ideograma CJK.
- `verificar_aceite.py` implementa o critério de aceite: o projeto válido passa com zero erro, o projeto com erros dispara as 12 regras, e os três códigos de saída da CLI estão corretos.

## Estrutura do projeto

```
rede-lab-topologia/
├── src/netlab/
│   ├── __main__.py   ponto de entrada: python -m netlab
│   ├── __init__.py   API pública e versão 1.0.0
│   ├── cargador.py   le o YAML e recusa referencia quebrada
│   ├── modelo.py     Vlan, Switch, Interface, PortaTrunk, PoolDhcp, Rota, AccessPoint, Projeto
│   ├── relatorio.py  texto no terminal e JSON
│   └── validador.py  as 12 regras sobre ipaddress da stdlib
├── tests/            181 testes, 96% de cobertura
├── tools/
│   ├── verificar_encoding.py   gate de U+FFFD e ideograma CJK
│   ├── verificar_aceite.py     prova do critério de aceite
│   └── gerar_exemplos.py       regenera os arquivos de exemplo com saída real
├── dados/
│   ├── projeto-predio.yaml      5 VLANs, 9 switches, aprovado com 0 erro
│   └── projeto-com-erros.yaml   um caso plantado por regra
├── docs/
│   ├── topologia.md             o prédio de referência e o desenho
│   └── regras-de-projeto.md     as 12 regras e o que cada uma protege
├── exemplos/
│   ├── saida-valida.txt         saída real do projeto aprovado
│   └── saida-com-erros.txt      saída real do projeto com 12 violações
├── pyproject.toml               build, scripts, pytest e cobertura
├── requirements.txt             pytest, pytest-cov, PyYAML
├── LICENSE                      MIT
└── README.md
```

## Trade-offs e decisões

- Aritmética de sub-rede com `ipaddress` da biblioteca padrão, não comparação de texto: `192.168.20.0/24` e `192.168.20.0/25` são notações diferentes do mesmo problema; só `overlaps` responde corretamente se sobrepoem.
- Um erro por pool (E003) em vez de um por endereço: um pool de 150 endereços fora da faixa geraria 150 linhas iguais. O relatório do projeto com erros vai de 162 achados para 12, um por regra, e continua cobrindo tudo.
- Gateway validado por regra, não por convenção: não exige que termine em `.1`; um gateway em `.254` numa `/24` é válido.
- Código de saída é parte do contrato: arquivo que não pode ser lido devolve 2, projeto com violação devolve 1. Um `except` genérico que devolve 0 quando o arquivo não abre faria o pipeline anunciar aprovação quando nada rodou.
- Categorias de rede pelo prefixo numérico do nome da VLAN (`30-CFTV`, `50-ENERGIA-IP`) para E006 e E007, sem configuração extra.
- As 12 regras são fixas. Adicionar uma significa acrescentar uma função à lista `REGRAS` e um par ao dicionário `CATALOGO_REGRAS`.
- Não é simulador de rede: confere o que o arquivo declara, não o que um equipamento faria com aquela declaração. Não valida MTU, listas de VLAN permitidas de trunk de fabricante nem capacidade de porta.

## Limitações conhecidas

- Não valida disponibilidade de endereço, nem sobreposição real contra redes fora do arquivo.
- Não conhece resolução de nome nem DNS.
- Não valida MTU, `trunkAllowedVLANs` de fabricante, nem capacidade de porta.
- Não valida licença nem preço de equipamento.
- As 12 regras são fixas.
- Não é simulador: valida o que o arquivo declara, não o comportamento do equipamento.

## Licença

MIT. Ver [LICENSE](LICENSE).

## Autor

Kelvin Oliveira — https://github.com/kelvinoliveira/netlab
