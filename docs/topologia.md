# Topologia do predio de referencia

O arquivo `dados/projeto-predio.yaml` descreve um predio comercial de tres
andares com cinco VLANs. Este documento explica o desenho e o motivo de cada
escolha, para que o arquivo possa ser lido como um projeto e nao como uma lista
de valores.

## O predio

Edificio Predial Norte, tres andares. Estacoes de trabalho, telefonia IP, cameras
de seguranca, rede de visitantes e medicao de energia. Nove switches: um core
que roteia, dois de distribuicao e seis de acesso. Dois pontos de acesso. Um
firewall, dois servidores, um NVR, um coletor de SNMP e um medidor de energia.

Toda a topologia cabe em um arquivo de texto, e nenhum item precisa de emulador,
de switch ou de cabo para ser conferido.

## As cinco VLANs

| Id | Nome | Faixa | Para que serve |
| ---: | --- | --- | --- |
| 10 | 10-CORPORATIVO | 192.168.10.0/24 | estacoes, servidores e gerenciamento |
| 20 | 20-VOIP | 192.168.20.0/24 | telefones e coleta de chamada |
| 30 | 30-CFTV | 192.168.30.0/24 | cameras e NVR |
| 40 | 40-GUEST | 192.168.40.0/24 | visitantes, com portal cativo |
| 50 | 50-ENERGIA-IP | 192.168.50.0/24 | medidores e BMS |

Todas RFC 1918 e todas em `/24`. O prefixo numerico do nome nao e decoracao: as
regras E006 e E007 classificam a categoria de rede pelo prefixo do nome. E o que
permite escrever `30-CFTV` no documento de projeto e ter a regra de segmentacao
ligada a ela sem configuracao extra.

Faixa `/24` em todas porque o plano de enderecamento e por bloco de 256, e
porque o DHCP de cada VLAN tem folga para crescer sem mudar mascara.

## Hierarquia de switches

```
core-1  (L3, roteia, VLAN 10 em 192.168.10.2)
  |
  +-- dist-1a  (L3, 192.168.10.3)  -- acc-1a, acc-1b
  |
  +-- dist-1b  (L3, 192.168.10.4)  -- acc-2a, acc-2b
  |
  +-- acc-3a, acc-cftv
```

Três camadas porque o predio tem tres andares, e porque o crescimento do trafego
nao e uniforme. Camera e telefone trafegam pouco e nao precisam passar pelo
core; estacao de trabalho passa.

`acc-cftv` tem endereco de gerenciamento na **VLAN 30**, e nao na 10. E a decisao
mais significativa do arquivo: o equipamento que serve as cameras e
gerenciado pela rede das cameras, e nao pela rede corporativa. Um compromisso de
gerenciao colado a outra equipe vira caminho de acesso, e o caminho mais usado e
o que oSnap mais gente usa.

## Trunks

Todo trunk leva a VLAN 10 de gerenciamento. Essa e a regra E008, e ela nao e
formalidade: um trunk sem a VLAN de gerenciamento deixa os equipamentos atras
dele inalcanceveis, e a reparacao custa subir no teto com o patch de cabo.

```
core-1 Te1/0/1  VLAN 10 (nativa), 20, 40, 50
core-1 Te1/0/2  VLAN 10 (nativa), 30
dist-1a Te1/0/1 VLAN 10 (nativa)
dist-1b Te1/0/1 VLAN 10 (nativa)
acc-cftv Gi0/8  VLAN 10 (nativa), 30
```

A VLAN nativa e a 10 em todos os enlaces. Um enlace com uma VLAN nativa nao
gerenciada obrigaria quem assumisse esse enlace a atravessar a rede antes de ter
gerencia dela.

Note que CFTV e ENERGIA-IP nao aparecem em trunk com a 10 de outro lado. O
`core-1 Te1/0/1` leva 10, 20, 40 e 50; a CFTV e a energia ficam no `Te1/0/2` e
em enlaces proprios. Isso mantem o trafego de camera e medidor em caminho
fisico separado, e nao so em VLAN separada: separacao por VLAN ainda passa pelo
mesmo Switch e pelo mesmo trunk.

## Rotas

```yaml
- { vlan: 10, destino: "0.0.0.0/0", proximo_salto: "firewall-1", padrao_para_internet: true }
- { vlan: 20, destino: "0.0.0.0/0", proximo_salto: "firewall-1", padrao_para_internet: true }
- { vlan: 40, destino: "0.0.0.0/0", proximo_salto: "firewall-1", padrao_para_internet: true }
- { vlan: 30, destino: "192.168.0.0/16", proximo_salto: "core-1" }
- { vlan: 50, destino: "192.168.0.0/16", proximo_salto: "core-1" }
```

As tres primeiras sao a internet, passando pelo firewall. A 30 e a 50 tem rota
apenas para a rede interna.

**E esta a linha mais importante do arquivo.** CFTV e ENERGIA-IP nao tem rota
para a internet, e essa e a E006 e a E007 cobrem. Detalhamento em
[`regras-de-projeto.md`](regras-de-projeto.md).

Se alguem precisar de acesso remoto a camera ou ao medidor, o caminho e VPN com
autenticacao, e nao rota default. A diferenca entre as duas e que a segunda
nao pede credencial a ninguem.

## DHCP

| VLAN | Faixa | Gateway |
| --- | --- | --- |
| 10 | 192.168.10.100-199 | 192.168.10.1 |
| 20 | 192.168.20.100-199 | 192.168.20.1 |
| 30 | 192.168.30.50-59 | 192.168.30.1 |
| 40 | 192.168.40.100-249 | 192.168.40.1 |
| 50 | 192.168.50.50-59 | 192.168.50.1 |

Todo pool inteiro dentro da faixa da sua VLAN, que e o que a E003 exige.

CFTV e ENERGIA-IP recebem endereco por pool minimo de 10, e nao estatico. Camera
e medidor sao poucos e nao mudam de lugar; pool pequeno reduz o intervalo de
varredura de um conflito de endereco e deixa o tracado mais legivel.

O gateway de cada pool e o `.1` da faixa, que e o endereco do firewall. A regra
E002 **nao** exige `.1`: exige que o endereco esteja dentro da faixa. Um gateway
em `.254` numa `/24` e valido.

## Pontos de acesso

```yaml
aps:
  - nome: ap-visitantes-1a
    switch: acc-1a
    porta: Gi0/20
    ssids:
      Rede-predio: 10
      Visitantes: 40
```

Todo SSID mapeado para uma VLAN, que e a E011. Um SSID sem VLAN cai na rede de
gerenciamento por padrao em quase todo equipamento: o hotspot corporativo de
visitas aparece na rede corporativa, e ninguem percebe ate um ataque com o
celular de alguem.

## SNMP

Todos os nove switches com community em modo leitura. A E010 exige: community em
escrita e senha de Administrador que viaja em texto no fio, e nao existe
motivo operacional para escrever em switch por SNMP. Quem precisar escrever,
migra para SNMPv3, que tem autenticacao e cifra.

## Como conferir

```powershell
python -m netlab validar dados/projeto-predio.yaml
# 0 erros em 9 dispositivos, 5 VLANs

python -m netlab resumir dados/projeto-predio.yaml
python -m netlab mapa
```

`resumir` mostra a estrutura sem validar, util para conferir se o YAML que voce
acabou de editar carregou do jeito que voce pensava.