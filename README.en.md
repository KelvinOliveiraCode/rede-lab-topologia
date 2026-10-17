# rede-lab-topologia

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white)
![deps](https://img.shields.io/badge/deps-PyYAML%20only-blue?style=flat-square)
![license](https://img.shields.io/badge/license-MIT-yellow?style=flat-square)
![platform](https://img.shields.io/badge/platform-Windows%20Linux%20macOS-blue?style=flat-square)
![tests](https://img.shields.io/badge/tests-181%20passing-brightgreen?style=flat-square)
![coverage](https://img.shields.io/badge/coverage-96%25-brightgreen?style=flat-square)

LAN network design validator from a declarative YAML file. Reads VLANs, address ranges, trunks, DHCP pools and routes, and returns violations before any cable, switch or open ceiling exists. No emulator, no equipment, no network: twelve rules, none needs anything plugged in.

## Problem / Why it exists

A company decides the topology in a spreadsheet before going to the field. The addressing error only shows up later, with the team idle and patch cable in hand. Nothing in the validator requires hardware: a text file and twelve rules.

The first version of this tool did not work for three code-reading reasons:

- Subnet overlap compared as text. `192.168.20.0/24` and `192.168.20.0/25` are different notations, so a string comparison does not find overlap. But the networks do overlap: the `/25` is inside the `/24`. The fix uses `ipaddress.IPv4Network.overlaps()`, from the standard library.
- Gateway validated by convention, not by rule. The version required the address to end in `.1`, which is convention: a gateway at `.254` on a `/24` is valid. And it compared only the first two octets, letting `192.168.99.4` pass on VLAN `192.168.10.0/24`.
- DHCP pool reported one error per address. A pool of 150 addresses outside the range generated 150 identical findings. Nobody reads a report like that. The rule now reports one error per pool, with the affected range.

The data file also did not exist. The six-module code was ready, but `dados/projeto-predio.yaml` was not, so nothing could be executed.

## What it does

Reads a network project in YAML and runs twelve validation rules:

| Code | Rule |
| --- | --- |
| E001 | Subnet overlap between VLANs, by subnet arithmetic, not text |
| E002 | Management address outside its own VLAN range |
| E003 | DHCP pool outside VLAN range, one error per pool |
| E004 | VLAN used on interface but not declared |
| E005 | Trunk references nonexistent VLAN |
| E006 | CCTV with default route to internet |
| E007 | ENERGY-IP with default route to internet |
| E008 | Trunk without permitted management VLAN |
| E009 | Duplicate address on different switches |
| E010 | SNMP community in write mode |
| E011 | Access point with unmapped SSID VLAN |
| E012 | Subnet mask inconsistent with addressing plan |

Terminal text output, colored when a terminal is present, or JSON. Exit codes: 0 approved, 1 design violation, 2 file could not be read. In automation, corrupted file and bad design do not exit the same.

The repository includes two project files:

- `dados/projeto-predio.yaml`: three-story commercial building, five RFC 1918 VLANs, nine switches in three layers, two access points, firewall, two servers, NVR, SNMP collector, and energy meter. Passes all twelve rules with zero errors.
- `dados/projeto-com-erros.yaml`: same design with one planted case per rule. Triggers all twelve rules and returns exit code 1. It is the file that proves the validator detects errors, not just approves.

Example usage

```
python -m netlab validar dados/projeto-predio.yaml
```

Expected output:

```
Project: projeto-predio - North Building - 3 floors
5 VLANs | 9 switches | 13 ports | 2 APs | 12 rules applied

0 errors on 9 devices, 5 VLANs
```

Exit code 0.

```
python -m netlab validar dados/projeto-com-erros.yaml
```

Expected output: `12 error(s) found: 9 high, 3 medium`, one line per rule code, with location and suggestion for each, and exit code 1.

## Stack

- Python 3.10 or higher
- PyYAML 6.0 or higher: only runtime dependency
- `ipaddress` from standard library: subnet arithmetic, CIDR overlap, and address membership test
- pytest and pytest-cov: development dependencies
- setuptools: build and packaging in `src` layout

No emulator, network simulator, or vendor library. Everything runs on what the file declares.

## How it works

1. The loader (`src/netlab/cargador.py`) reads the YAML and builds the domain model: `Vlan`, `Switch`, `Interface`, `PortaTrunk`, `PoolDhcp`, `Rota`, `AccessPoint` and `Projeto`. Rejects unknown port type, non-CIDR range, and reference to undeclared equipment, before any rule runs.
2. The validator (`src/netlab/validador.py`) runs the twelve rules in order over the model, using `ipaddress.IPv4Network.overlaps()` for subnet overlap.
3. The report (`src/netlab/relatorio.py`) emits terminal text or JSON, with one entry per rule code, violation location and correction suggestion. One error per problem, not per occurrence: a pool with 30 out-of-range addresses yields one finding, not 30.

CLI subcommands:

| Command | What it does |
| --- | --- |
| `validar FILE` | Validates the project and lists violations |
| `resumir FILE` | Shows structure without validating |
| `regras` | Lists the twelve rules |

`validar` arguments: `--formato texto|json`, `--saida FILE` and `--json-saida FILE`.

## How to run

Requires Python 3.10 or higher. Works on Windows, Linux and macOS.

```
git clone https://github.com/kelvinoliveira/netlab.git
cd netlab
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Validate the reference project:

```
python -m netlab validar dados/projeto-predio.yaml
```

Output: `0 errors on 9 devices, 5 VLANs`, exit code 0.

See the project with planted errors:

```
python -m netlab validar dados/projeto-com-erros.yaml
```

Output: the twelve violations, exit code 1.

Other commands

```
python -m netlab resumir projeto.yaml     # structure, without validating
python -m netlab regras                   # the 12 rules
python -m netlab validar projeto.yaml --formato json   # JSON output
python -m netlab validar projeto.yaml --saida rel.txt  # writes to file
python -m netlab validar projeto.yaml --json-saida r.json
```

Tests and verification

```
python -m pytest --cov=netlab --cov-report=term-missing
python tools/verificar_encoding.py
python tools/verificar_aceite.py
```

- 181 tests, 96% coverage, floor set at 70%.
- `verificar_encoding.py` fails if any file has replacement character (U+FFFD) or CJK ideograph.
- `verificar_aceite.py` implements acceptance criteria: valid project passes with zero errors, project with errors triggers all 12 rules, and the three CLI exit codes are correct.

## Project structure

```
rede-lab-topologia/
├── src/netlab/
│   ├── __main__.py   entry point: python -m netlab
│   ├── __init__.py   public API and version 1.0.0
│   ├── cargador.py   reads YAML and rejects broken references
│   ├── modelo.py     Vlan, Switch, Interface, PortaTrunk, PoolDhcp, Rota, AccessPoint, Projeto
│   ├── relatorio.py  terminal text and JSON
│   └── validador.py  the 12 rules over stdlib ipaddress
├── tests/            181 tests, 96% coverage
├── tools/
│   ├── verificar_encoding.py   U+FFFD and CJK ideograph gate
│   ├── verificar_aceite.py     acceptance criteria proof
│   └── gerar_exemplos.py       regenerates example files with real output
├── dados/
│   ├── projeto-predio.yaml      5 VLANs, 9 switches, approved with 0 errors
│   └── projeto-com-erros.yaml   one planted case per rule
├── docs/
│   ├── topologia.md             reference building and diagram
│   └── regras-de-projeto.md     the 12 rules and what each protects
├── exemplos/
│   ├── saida-valida.txt         real output of approved project
│   └── saida-com-erros.txt      real output of project with 12 violations
├── pyproject.toml               build, scripts, pytest and coverage
├── requirements.txt             pytest, pytest-cov, PyYAML
├── LICENSE                      MIT
└── README.md
```

## Trade-offs and decisions

- Subnet arithmetic with `ipaddress` from standard library, not text comparison: `192.168.20.0/24` and `192.168.20.0/25` are different notations of the same problem; only `overlaps` correctly answers whether they overlap.
- One error per pool (E003) instead of one per address: a pool of 150 out-of-range addresses would generate 150 identical lines. The error project report goes from 162 findings to 12, one per rule, still covering everything.
- Gateway validated by rule, not convention: does not require ending in `.1`; a gateway at `.254` on a `/24` is valid.
- Exit code is part of the contract: unreadable file returns 2, project with violation returns 1. A generic `except` returning 0 when the file does not open would make the pipeline announce approval when nothing ran.
- Network categories by numeric prefix of VLAN name (`30-CFTV`, `50-ENERGIA-IP`) for E006 and E007, no extra configuration.
- The 12 rules are fixed. Adding one means adding a function to the `REGRAS` list and a pair to the `CATALOGO_REGRAS` dictionary.
- Not a network simulator: checks what the file declares, not what equipment would do with that declaration. Does not validate MTU, vendor trunk allowed VLANs, or port capacity.

## Known limitations

- Does not validate address availability, nor real overlap against networks outside the file.
- Does not know name resolution or DNS.
- Does not validate MTU, `trunkAllowedVLANs` from vendor, or port capacity.
- Does not validate license or equipment price.
- The 12 rules are fixed.
- Not a simulator: validates what the file declares, not equipment behavior.

## License

MIT. See [LICENSE](LICENSE).

## Author

Kelvin Oliveira — https://github.com/kelvinoliveira/netlab
