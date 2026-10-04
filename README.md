<div align="center">

<p>
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/tests-181%20passing-brightgreen?style=flat-square" alt="Tests">
  <img src="https://img.shields.io/badge/coverage-96%25-brightgreen?style=flat-square" alt="Coverage">
  <img src="https://img.shields.io/badge/deps-PyYAML%20only-blue?style=flat-square" alt="Deps">
  <img src="https://img.shields.io/badge/license-MIT-yellow?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/platform-Windows-blue?style=flat-square" alt="Windows">
</p>

</div>

# rede-lab-topologia

Validador de projeto de rede LAN a partir de arquivo declarativo. Le um YAML com
VLANs, faixas, trunks, DHCP e rotas, e devolve as violacoes antes de existir cabo,
switch e teto aberto.

LAN design validator driven by a declarative YAML file.

Sem emulador, sem equipamento, sem rede. Doze regras, nenhuma delas precisa de
nada ligado.

---

## PT-BR

### O que e

Empresa decide topologia em planilha antes de subir em campo. Erro de
enderecamento so aparece depois, com a equipe parada e o patch de cabo na mao.
Esta ferramenta roda o projeto por 12 regras e devolve a lista do que esta
errado, em segundos, sem tocar em nada.

```powershell
python -m netlab validar dados/projeto-predio.yaml
# 0 erros em 9 dispositivos, 5 VLANs
```

O projeto de exemplo e um predio comercial de tres andares: cinco VLANs RFC 1918,
nove switches em tres camadas, dois pontos de acesso, firewall, servidores, NVR,
sensor SNMP e medidor de energia. Detalhes em
[`docs/topologia.md`](docs/topologia.md).

### Por que foi feito

A primeira versao desta ferramenta nao funcionava, e a falha era de leitura de
codigo, nao de teste.

**A sobreposicao de sub-rede era comparada como texto.** `192.168.20.0/24` e
`192.168.20.0/25` sao notacoes diferentes, entao comparar string nao achava
nada. Mas as duas redes se sobrepoem: a `/25` esta contida na `/24`. O validador
usa agora `ipaddress.IPv4Network.overlaps()`, que faz a conta de verdade, e o
teste `test_nao_compara_texto` fixa esse contrato.

**O gateway era validado por convencao, e nao por regra.** A versao anterior
exigia que o endereco terminasse em `.1`, o que e convencao e nao verdade: um
gateway em `.254` numa `/24` e valido. E comparava so os dois primeiros octetos,
o que deixava passar `192.168.99.4` numa VLAN `192.168.10.0/24`, porque os dois
primeiros octetos batem.

**O pool DHCP era validado olhando o quarto octeto.** Um pool com 30 enderecos
fora da faixa gerava 30 achados, e um pool de 150 gerava 150. O mesmo problema,
150 vezes, com a mesma correcao. Ninguem le um relatorio assim. A regra passou a
reportar um erro por pool, com o intervalo afetado na mensagem.

**O arquivo de dados nao existia.** O codigo de seis modulos estava la, mas
`dados/projeto-predio.yaml` nao, entao nada podia ser executado.

A correcao foi reescrever o nucleo em cima de `ipaddress` da biblioteca padrao
e escrever os dois arquivos de projeto com um caso de cada regra plantado.

### Como rodar

Requer Python 3.10 ou superior. Windows, Linux e macOS.

```powershell
# 1. Instalar
git clone https://github.com/kelvinoliveira/netlab.git
cd netlab
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# 2. Validar o projeto de referencia
python -m netlab validar dados/projeto-predio.yaml

# 3. Ver o projeto que tem erro
python -m netlab validar dados/projeto-com-erros.yaml
```

O primeiro comando devolve `0 erros em 9 dispositivos, 5 VLANs` e codigo de
saida 0. O segundo lista as 12 violacoes e devolve codigo de saida 1.

Outros comandos:

```powershell
python -m netlab validar projeto.yaml --formato json   # saida em JSON
python -m netlab validar projeto.yaml --saida rel.txt  # grava em arquivo
python -m netlab validar projeto.yaml --json-saida r.json
python -m netlab resumir projeto.yaml                   # estrutura, sem validar
python -m netlab regras                                # as 12 regras
```

### Validar

```powershell
python -m pytest --cov=netlab --cov-report=term-missing
python tools/verificar_encoding.py
python tools/verificar_aceite.py
```

- **181 testes**, **96%** de cobertura, piso configurado em 70%.
- `verificar_encoding.py` falha se algum arquivo tiver caractere de
  substituicao (U+FFFD) ou ideograma CJK.
- `verificar_aceite.py` implementa o criterio de aceite: o projeto valido passa
  com zero erro, o projeto com erros dispara **as 12 regras**, e os tres codigos
  de saida da CLI estao corretos.

Cada regra tem dois testes: um que dispara e um que **nao** dispara. O segundo e
o que importa, porque uma regra que nunca erra acerta tudo.

O CI tambem regenera os exemplos e falha se ficarem desatualizados, entao um
numero errado em documento derruba o build.

### As 12 regras

| Codigo | Regra |
| --- | --- |
| E001 | Sobreposicao de sub-rede entre VLANs |
| E002 | Endereco de gateway fora da propria faixa |
| E003 | Pool DHCP fora da faixa da VLAN |
| E004 | VLAN usada em interface mas nao declarada |
| E005 | Trunk referencia VLAN inexistente |
| E006 | CFTV com rota default para a internet |
| E007 | ENERGIA-IP com rota default para a internet |
| E008 | Trunk sem VLAN de gerenciamento permitida |
| E009 | Endereco duplicado em switch diferente |
| E010 | Community SNMP em modo escrita |
| E011 | AP sem SSID mapeado para VLAN |
| E012 | Mascara de sub-rede inconsistente |

**E006 e E007 sao as mais importantes.** Video e gesto de energia nao convivem
com a internet. Um NVR alcancavel de fora vira caminho de entrada, e um medidor
de energia alcancavel pela internet vira caminho de entrada para a rede
eletrica. Por isso as duas regras exigem que a categoria nao tenha rota para a
internet, e nao apenas que exista regra de firewall em algum lugar.
Justificativa completa em [`docs/regras-de-projeto.md`](docs/regras-de-projeto.md).

### O que aprendi

**Sobreposicao de CIDR e aritmetica, nao texto.** Dois componentes que passam
em revisao comparando string nao vao achar `192.168.20.0/24` sobre
`192.168.20.0/25`. A biblioteca padrao ja resolve, e resolver na mao significa
errar.

**Convencao nao e regra.** Exigir que o gateway termine em `.1` e um detalhe de
projeto, nao uma condicao de correcao. Uma regra que confunde as duas recusa
projetos validos e treina quem usa a ferramenta a ignorar os achados.

**Erro repetido nao e informacao.** Um achado por pool e um por endereco sao a
mesma informacao com mil vezes o ruido. O relatorio inteiro passou de 162
achados para 12, e continua cobrindo tudo.

**Codigo de saida e parte do contrato.** Em automacao, arquivo corrompido e
projeto com erro nao podem devolver o mesmo codigo. Um `except` generico que
devolve 0 quando o arquivo nao abre faz o pipeline anunciar que o projeto
passou quando nao passou nada.

**Arquivo de dados que dispara as regras e o que prova que elas funcionam.** Um
validador aprovado no projeto bom e nunca testado no ruim satisfaz metade da
especificacao. `dados/projeto-com-erros.yaml` tem um caso de cada regra, e tanto
a suite quanto o script de aceite exigem os 12 codigos.

### Limitacoes

- Nao valida disponibilidade de endereco, nem sobreposicao real de faixas em relacao
  a outras redes fora do arquivo.
- Nao conhece resolucao de nome nem DNS.
- Nao valida MTU, trunkAllowedVLANs de fabricante, nem capacidade de porta.
- Nao valida licenca nem preco de equipamento.
- As 12 regras sao fixas. Adicionar regra e acrescentar funcao na lista
  `REGRAS` e o par no `CATALOGO_REGRAS`.
- Nao e um simulador de rede: ele confere o que o arquivo **declara**, nao o que
  um equipamento faria com essa declaracao.

### Licenca

MIT. Ver [LICENSE](LICENSE).

---

## EN

### What it is

A LAN design validator driven by a declarative YAML file. It reads VLANs,
subnets, trunks, DHCP and routes, and reports what is wrong before there is
cable, a switch and an open ceiling.

LAN design validator driven by a declarative YAML file.

No emulator, no gear, no network. Twelve rules, none of which needs anything
plugged in.

### Why it was built

The first version of this tool did not work, and the failure was readable in the
code rather than in a test.

**Subnet overlap was compared as text.** `192.168.20.0/24` and
`192.168.20.0/25` are different strings, so a string comparison finds nothing.
But the two networks do overlap: the `/25` sits inside the `/24`. The validator
now uses `ipaddress.IPv4Network.overlaps()`, which does the arithmetic, and
`test_nao_compara_texto` holds that contract.

**The gateway was checked by convention instead of by rule.** The previous
version required the address to end in `.1`, which is a convention and not a
truth: a gateway at `.254` on a `/24` is perfectly valid. And it compared only
the first two octets, which let `192.168.99.4` pass on a `192.168.10.0/24` VLAN,
because the first two octets match.

**The DHCP pool was validated by looking at the fourth octet.** A pool with 30
addresses out of range produced 30 findings, and a pool of 150 produced 150.
Same problem, 150 times, same fix. Nobody reads that report. The rule now
reports one finding per pool, with the affected range in the message.

**The data file did not exist.** The code across six modules was there, but
`dados/projeto-predio.yaml` was not, so nothing could run.

The fix was to rewrite the core on top of `ipaddress` from the standard library
and write the two project files with one planted case per rule.

### How to run

Requires Python 3.10 or newer. Windows, Linux and macOS.

```powershell
# 1. Install
git clone https://github.com/kelvinoliveira/netlab.git
cd netlab
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 2. Validate the reference project
python -m netlab validar dados/projeto-predio.yaml

# 3. See the project that has errors
python -m netlab validar dados/projeto-com-erros.yaml
```

The first returns `0 erros em 9 dispositivos, 5 VLANs` and exit code 0. The second
lists the 12 violations and returns exit code 1.

Other commands:

```powershell
python -m netlab validar project.yaml --formato json  # JSON output
python -m netlab validar project.yaml --saida out.txt # write to a file
python -m netlab resumir project.yaml                  # structure, no validation
python -m netlab regras                               # the 12 rules
```

### Validate

```powershell
python -m pytest --cov=netlab --cov-report=term-missing
python tools/verificar_encoding.py
python tools/verificar_aceite.py
```

- **181 tests**, **96%** coverage, floor configured at 70%.
- `verificar_encoding.py` fails if any file holds a replacement character
  (U+FFFD) or a CJK ideograph.
- `verificar_aceite.py` implements the acceptance criterion: the valid project
  passes with zero errors, the project with errors triggers **all 12 rules**, and
  the three CLI exit codes are correct.

Every rule has two tests: one that triggers it and one that does **not**. The
second is the one that matters, because a rule that never errs gets everything
right.

CI also regenerates the examples and fails if they go stale, so a wrong number in
a document breaks the build.

### The 12 rules

| Code | Rule |
| --- | --- |
| E001 | Overlapping subnets between VLANs |
| E002 | Gateway address outside its own subnet |
| E003 | DHCP pool outside the VLAN subnet |
| E004 | VLAN used on an interface but not declared |
| E005 | Trunk referencing a non-existent VLAN |
| E006 | CFTV with a default route to the internet |
| E007 | IP energy with a default route to the internet |
| E008 | Trunk without the management VLAN allowed |
| E009 | Duplicate address on different switches |
| E010 | SNMP community in write mode |
| E011 | AP with an SSID not mapped to a VLAN |
| E012 | Subnet mask inconsistent with the addressing plan |

**E006 and E007 are the most important.** Video and energy metering do not
belong on the internet. A reachable NVR becomes an entry point, and an energy
meter reachable from the internet becomes an entry point to the electrical
grid. That is why both rules require the category to have no route to the
internet, rather than merely expecting a firewall rule somewhere. Full reasoning
in [`docs/regras-de-projeto.md`](docs/regras-de-projeto.md) (Portuguese).

### What I learned

**CIDR overlap is arithmetic, not text.** Two components that pass review by
comparing strings will not find `192.168.20.0/24` overlapping
`192.168.20.0/25`. The standard library already solves it, and solving it by hand
means getting it wrong.

**Convention is not a rule.** Requiring the gateway to end in `.1` is a project
detail, not a correctness condition. A rule that confuses the two rejects valid
designs and trains people to ignore its findings.

**A repeated error is not information.** One finding per pool and one per
address are the same information with a thousand times the noise. The report
went from 162 findings to 12 while still covering everything.

**Exit code is part of the contract.** In automation, a corrupt file and a
project with errors cannot return the same code. A broad `except` returning 0
when the file will not open makes the pipeline announce that the project passed
when nothing ran.

**A data file that triggers the rules is what proves they work.** A validator
that passes on the good project and is never tested on the bad one satisfies
half the specification. `dados/projeto-com-erros.yaml` has one case per rule, and
both the suite and the acceptance script require all 12 codes.

### Limitations

- It does not check address availability, nor real subnet overlap against
  networks outside the file.
- It knows nothing about name resolution or DNS.
- It does not validate MTU, vendor trunk allowed-VLAN lists, or port capacity.
- It does not validate licensing or equipment cost.
- The 12 rules are fixed. Adding one means adding a function to `REGRAS` and an
  entry in `CATALOGO_REGRAS`.
- It is not a network simulator: it checks what the file **declares**, not what a
  device would do with that declaration.

### License

MIT. See [LICENSE](LICENSE).

---

## Estrutura / Structure

```
netlab/
├── src/netlab/
│   ├── modelo.py      Vlan, Interface, PortaTrunk, Switch, AccessPoint,
│   │                  PoolDhcp, Rota, Projeto
│   ├── cargador.py    Le o YAML e recusa referencia quebrada
│   ├── validador.py   As 12 regras, sobre ipaddress da stdlib
│   ├── relatorio.py   Texto no terminal e JSON
│   └── cli.py         validar, resumir, regras
├── tests/             181 testes, 96% de cobertura
├── tools/
│   ├── verificar_encoding.py   Gate de U+FFFD e ideograma CJK
│   ├── verificar_aceite.py     Prova de aceite do criterio de aceitacao
│   └── gerar_exemplos.py       Regera os exemplos com saida real
├── dados/
│   ├── projeto-predio.yaml      5 VLANs, 9 switches, passa com 0 erro
│   └── projeto-com-erros.yaml   um caso plantado por regra
├── docs/
│   ├── topologia.md       O predio de referencia e o desenho
│   └── regras-de-projeto.md As 12 regras e o que elas protegem
├── exemplos/
│   ├── saida-valida.txt     Saida real do projeto aprovado
│   └── saida-com-erros.txt  Saida real do projeto com 12 violacoes
└── .github/workflows/ci.yml   Windows, com gate de cobertura e de aceite
```

## Comandos / Commands

| Comando | O que faz |
| --- | --- |
| `netlab validar` | Valida o projeto e lista as violacoes |
| `netlab resumir` | Mostra a estrutura sem validar |
| `netlab regras` | Lista as 12 regras |

Argumentos de `validar`: `--formato texto\|json`, `--saida ARQUIVO` e
`--json-saida ARQUIVO`.