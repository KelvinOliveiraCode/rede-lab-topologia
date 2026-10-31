# rede-lab-topologia

[English](README.en.md) · **Português (Brasil)**

[![Python 3](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](#) [![PyYAML](https://img.shields.io/badge/PyYAML-%C3%BAnica%20dep-3776AB?style=flat-square)](#) [![pytest](https://img.shields.io/badge/pytest-181%20testes-0A9EDC?style=flat-square&logo=pytest)](#) [![MIT License](https://img.shields.io/badge/License-MIT-f4c430?style=flat-square)](LICENSE)

## O que é

**Validador de projeto de rede LAN**: carrega a topologia (VLANs, switches, interfaces, roteamento) de um arquivo YAML, valida sub-redes, sobreposição de VLANs, consistência de interfaces e capacidade de roteamento, e gera relatório em texto ou JSON. É um laboratório educacional de projeto de redes.

## Status

Laboratório educacional funcional e testado (181 testes).

## Funcionalidades

- **Carga de projeto** (`cargador.py`): lê YAML de VLANs, switches, interfaces e roteamento com validação de tipos.
- **Modelo** (`modelo.py`): dataclasses `Vlan`, `Switch`, `Interface`, `Roteador`, `Projeto`.
- **Validação** (`validador.py`): verifica endereçamento IP, sub-redes, sobreposição, VLANs associadas, interfaces e rotas.
- **Relatório** (`relatorio.py`): saída em texto colorido ou JSON, com lista de erros.
- **CLI**: `netlab validar <projeto.yaml>`, `netlab regras`, `netlab resumir`.

## Arquitetura

Pacote `netlab` com camadas: `cargador` (parse YAML), `modelo` (dataclasses), `validador` (regras de projeto), `relatorio` (saída).

## Stack

- Python ≥ 3.10
- PyYAML ≥ 6.0 (única dependência)
- pytest (dev)

## Estrutura do repositório

```
rede-lab-topologia/
├── pyproject.toml · BRIEF.md
├── src/netlab/
│   ├── cargador.py · modelo.py · validador.py · relatorio.py · cli.py
├── dados/            # exemplos YAML de projeto
├── tests/            # 181 testes
└── LICENSE           # MIT
```

## Pré-requisitos e instalação

```bash
pip install -e .
```

## Como executar

```bash
netlab validar dados/projeto.yaml
netlab regras
netlab resumir dados/projeto.yaml
```

## Testes e qualidade

```bash
PYTHONPATH=src python -m pytest tests/
# 181 passed
```

## Decisões técnicas e trade-offs

- Validação baseada em regras independentes, facilmente extensível.
- YAML como formato de entrada: legível e editável, mas sem schema formal (validação manual em `cargador`).

## Limitações conhecidas

- Projetos hipotéticos (YAML), sem integração com equipamentos reais.
- Não cobre roteamento dinâmico (OSPF/BGP).

## Processo de desenvolvimento

Projeto individual de Kelvin Oliveira, construído com agentes de IA orquestrados e revisado pelo autor. A validação de topologia e a revisão são do autor.

## Licença e autor

MIT — Copyright (c) 2026 Kelvin Rebelo de Oliveira. Autor: [Kelvin Oliveira](https://github.com/KelvinOliveiraCode) · [Portfólio](https://kelvinoliveiracode.github.io/portfolio/)
