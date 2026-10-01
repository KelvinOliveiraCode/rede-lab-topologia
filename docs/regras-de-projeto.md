# As 12 regras de projeto de rede

Este documento explica o que cada regra protege, por que ela existe e o que
acontece em campo quando ela e ignorada. O detalhamento de cada uma estao em
[`docs/regras-de-projeto.md`](regras-de-projeto.md); aqui fica a visao geral.

## O problema que o validador resolve

Empresa decide topologia em planilha antes de subir em campo. O erro de
enderecamento so aparece depois, no teto, com a equipe parada e o patch de cabo
na mao. Uma regra de validacao aqui custa um segundo; em campo custa uma tarde
e um Switch tomada emprestado.

Nenhuma das 12 regras precisa de emulador, de switch ou de cabo. O validador le
um YAML e devolve violacoes.

## As regras

| Codigo | Regra | Criticidade |
| --- | --- | --- |
| E001 | Sobreposicao de sub-rede entre VLANs | alta |
| E002 | Endereco de gateway fora da propria faixa | alta |
| E003 | Pool DHCP fora da faixa da VLAN | alta |
| E004 | VLAN usada em interface mas nao declarada | alta |
| E005 | Trunk referencia VLAN inexistente | alta |
| E006 | CFTV com rota default para a internet | alta |
| E007 | ENERGIA-IP com rota default para a internet | alta |
| E008 | Trunk sem VLAN de gerenciamento permitida | media |
| E009 | Endereco duplicado em switch diferente | alta |
| E010 | Community SNMP em modo escrita | alta |
| E011 | AP sem SSID mapeado para VLAN | media |
| E012 | Mascara de sub-rede inconsistente | media |

Nove de criticidade alta, tres media.

## As duas mais importantes: E006 e E007

Segmentacao de rede e requisito real de seguranca eletronica e de gestao de
energia, e nao recomendacao de estilo. Estas duas regras existem por causa
disso, e por isso a documentacao delas e a mais longa do projeto.

**E006, CFTV com rota default para a internet.** Um NVR que alcanca a web pode
ser alcancado de fora. Camera alimentada por circuito dedicado e uma promessa
que so vale se a camera nao tem caminho de volta para a internet.

**E007, ENERGIA-IP com rota default para a internet.** Medidor de energia
alcancado pela internet vira ponto de entrada para a rede eletrica. Este e o
caso em que falha de segmentacao deixa de ser teoria de sala de aula: e o
acidente que documento de seguranca eletronica precisa evitar.

A diferenca entre as duas regras e o que elas exigem: nao e "existe rota
default", e "existe rota default **para essa categoria**". As duas regras olham
o prefixo numerico do nome da VLAN, e nao o id, entao `30-CFTV` e
`30-VISITANTES` caem na mesma regra, e uma VLAN sem prefixo numerico nao cai
em nenhuma.

## As duas que custam mais caro em campo: E009 e E002

**E009, endereco duplicado.** Dois equipamentos com o mesmo endereco em switches
diferentes geram ARP duplicado. O sintoma e o pior possivel para quem
investiga: o acesso responde e deixa de responder conforme o switch que ganha o
ARP. Passa-se uma semana chamando de "problema de rede".

**E002, endereco de gerenciamento fora da faixa.** O SVI de um switch tem que
estar dentro da faixa da VLAN que ele gerencia. Fora dela, o SVI fica
inalcancavel de dentro da rede, e o switch perde gerenciamento justamente no
momento em que seria preciso reconfigura-lo.

A versao anterior desta ferramenta verificava se o gateway terminava em `.1`, o
que e convencao e nao regra: um gateway em `.254` numa `/24` e perfectly
valido. E comparava so os dois primeiros octetos, o que deixava passar
`192.168.99.4` numa VLAN `192.168.10.0/24`, porque os dois primeiros octetos
batem.

## Arquetim de sub-rede, e nao comparacao de texto

A E001 da versao anterior comparava as notacoes de CIDR como texto. Isso so
funciona para o caso mais obvio, e erra justo no caso que importa.

O arquivo de erro deste repositorio tem `192.168.20.0/24` e `192.168.20.0/25`.
As duas notacoes sao **diferentes**, entao comparar string nao acha
sobreposicao alguma. Mas as duas redes se sobrepoem: a `/25` esta contida na
`/24`.

O validador usa `ipaddress.IPv4Network.overlaps()`, da biblioteca padrao, que
faz a conta de verdade. O teste `test_nao_compara_texto` fixa esse contrato.

## Um erro por problema, nao um por ocorrencia

A E003 da primeira versao reportava um erro por endereco fora da faixa. Um pool
de 150 enderecos todo fora da faixa gerava 150 achados do mesmo problema, com a
mesma correcao.

Um relatorio com 150 linhas iguais nao e lido por ninguem, e um relatorio nao
lido vale menos do que um relatorio curto. A regra passou a reportar **um erro
por pool**, com o intervalo afetado e a contagem na mensagem:

```
pool DHCP da VLAN 20-VOIP entrega 30 endereco(s) fora de 192.168.20.0/24:
192.168.10.200 ate 192.168.10.229
```

Com isso, o projeto de exemplo passa de 162 achados para 12, um por regra, e
todos legiveis.

## Codigos de saida

| Codigo | Significado |
| --- | --- |
| 0 | projeto aprovado, nenhum erro |
| 1 | projeto tem violacao |
| 2 | o arquivo nao pode ser lido |

O terceiro existe porque em automacao **arquivo corrompido e projeto ruim nao
podem sair igual**. Um `except` generico que devolve 0 quando o arquivo nao abre
faz o pipeline dizer que o projeto passou quando nao passou nada. O passo do CI
para o arquivo com erros checa explicitamente que o codigo e 1.

## Arquivo com erro, um caso por regra

`dados/projeto-com-erros.yaml` existe para provar que o validador **detecta**
erro, e nao apenas aprova. Um validador que nunca acusa nada satisfaz a
metade da especificacao e nao serve para uso nenhum.

Cada bloco do arquivo tem comentario com o codigo que ele dispara. O arquivo
tem de produzir os 12 codigos, e tanto a suite quanto
`tools/verificar_aceite.py` exigem isso.