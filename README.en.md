# rede-lab-topologia

**English** · [Português (Brasil)](README.md)

[![Python 3](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](#) [![PyYAML](https://img.shields.io/badge/PyYAML-only%20dep-3776AB?style=flat-square)](#) [![pytest](https://img.shields.io/badge/pytest-181%20tests-0A9EDC?style=flat-square&logo=pytest)](#) [![MIT License](https://img.shields.io/badge/License-MIT-f4c430?style=flat-square)](LICENSE)

## What it is

**LAN project validator**: loads a topology (VLANs, switches, interfaces, routing) from a YAML file, validates subnets, VLAN overlap, interface consistency and routing capability, and produces a text or JSON report. It is an educational network-design lab.

## Status

An educational lab, working and tested (181 tests).

## Features

- **Project loader** (`cargador.py`): reads YAML of VLANs, switches, interfaces and routing with type validation.
- **Model** (`modelo.py`): dataclasses `Vlan`, `Switch`, `Interface`, `Roteador`, `Projeto`.
- **Validation** (`validador.py`): checks IP addressing, subnets, overlap, VLAN associations, interfaces and routes.
- **Report** (`relatorio.py`): colored text or JSON output with error listing.
- **CLI**: `netlab validar <projeto.yaml>`, `netlab regras`, `netlab resumir`.

## Architecture

A `netlab` package with layers: `cargador` (YAML parse), `modelo` (dataclasses), `validador` (design rules), `relatorio` (output).

## Stack

- Python ≥ 3.10
- PyYAML ≥ 6.0 (only dependency)
- pytest (dev)

## Repository layout

```
rede-lab-topologia/
├── pyproject.toml · BRIEF.md
├── src/netlab/
│   ├── cargador.py · modelo.py · validador.py · relatorio.py · cli.py
├── dados/            # YAML project examples
├── tests/            # 181 tests
└── LICENSE           # MIT
```

## Prerequisites and installation

```bash
pip install -e .
```

## How to run

```bash
netlab validar dados/projeto.yaml
netlab regras
netlab resumir dados/projeto.yaml
```

## Tests and quality

```bash
PYTHONPATH=src python -m pytest tests/
# 181 passed
```

## Technical decisions and trade-offs

- Independent validation rules, easily extensible.
- YAML input format: readable and editable, but no formal schema (manual validation in `cargador`).

## Known limitations

- Hypothetical projects (YAML), no integration with real equipment.
- Does not cover dynamic routing (OSPF/BGP).

## Development process

An individual project by Kelvin Oliveira, built with orchestrated AI agents and reviewed by the author. The topology validation and the review are the author's.

## License and author

MIT — Copyright (c) 2026 Kelvin Rebelo de Oliveira. Author: [Kelvin Oliveira](https://github.com/KelvinOliveiraCode) · [Portfolio](https://kelvinoliveiracode.github.io/portfolio/)
