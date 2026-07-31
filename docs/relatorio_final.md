# Relatório final — Sandbox SIR da dengue nos municípios do Rio de Janeiro

## Escopo e objetivo

Este projeto constrói uma base municipal reproduzível para explorar a dengue
nos 92 municípios do Estado do Rio de Janeiro entre 2020 e 2024. Ele integra
notificações do SINAN, população pactuada pela SES-RJ, saneamento SNIS/SINISA,
levantamentos LIRAa/LIA e a malha municipal do IBGE.

A pergunta central é se indicadores municipais de saneamento e infestação
vetorial apresentam associação com a incidência de dengue. As análises são
exploratórias e não estimam efeitos causais. O simulador SIR é um sandbox
matemático de cenários, não uma previsão epidemiológica oficial.

## Definições e decisões metodológicas

- Casos de dengue são agregados **sempre pelo município de residência**
  (`ID_MN_RESI`).
- Caso provável segue a regra operacional adotada pelo Ministério da Saúde:
  notificação suspeita, exceto a classificação final descartada.
- A incidência é expressa por **1.000 habitantes**:
  `casos prováveis / população residente × 1.000`.
- A população anual provém das estimativas pactuadas pela SES-RJ.
- Junções territoriais utilizam o código IBGE do município.
- O banco de demonstração contém somente agregados municipais e exclui a tabela
  de notificações individuais.

## Dados consolidados

O painel anual possui 460 observações município–ano: 92 municípios em cada um
dos cinco anos. O total estadual de casos prováveis e a incidência agregada
foram:

| Ano | Casos prováveis | População | Incidência por 1.000 |
|---:|---:|---:|---:|
| 2020 | 4.390 | 17.222.305 | 0,2549 |
| 2021 | 2.853 | 17.220.455 | 0,1657 |
| 2022 | 11.094 | 17.211.760 | 0,6446 |
| 2023 | 50.341 | 17.213.813 | 2,9245 |
| 2024 | 301.811 | 17.219.679 | 17,5271 |

Em 2024, as maiores incidências municipais ocorreram em Cantagalo
(145,2290 por 1.000), Bom Jardim (99,6772), Paraty (95,3921), Vassouras
(95,3654) e Itatiaia (92,5858). Rankings por incidência não equivalem a
rankings por número absoluto de casos.

## Saneamento

A seção transversal SINISA de 2024 apresentou:

- atendimento de água: Pearson `r = -0,0280` (`p = 0,7954`, 88 municípios) e
  Spearman `ρ = -0,1622` (`p = 0,1312`);
- atendimento de esgoto: Pearson `r = -0,0197` (`p = 0,8754`, 66 municípios) e
  Spearman `ρ = 0,1151` (`p = 0,3576`).

Esses resultados não oferecem evidência de uma associação linear robusta na
seção transversal analisada. Não devem ser interpretados como ausência de
efeito causal do saneamento. A série histórica SNIS possui 32 chaves
município–ano–indicador com múltiplos prestadores e não foi agregada sem uma
regra substantiva validada.

## Estrutura espacial

O Moran global da incidência, com pesos de contiguidade rainha, foi `0,0541`
em 2020, `0,2920` em 2021, `0,2913` em 2022, `0,5694` em 2023 e `0,3863` em
2024. A autocorrelação foi compatível com aleatoriedade espacial em 2020
(`p = 0,246`) e positiva nos demais anos (`p ≤ 0,002`, 999 permutações).

O sinal e a ordem de grandeza permaneceram semelhantes com contiguidade torre
e quatro vizinhos mais próximos. Clusters locais são diagnósticos
exploratórios; não identificam mecanismos de transmissão.

## LIRAa/LIA

Foram harmonizados 15 levantamentos entre 2020 e 2024. As correlações entre
IIP e incidência contemporânea ou defasada foram positivas, porém pequenas:
Pearson entre `0,0715` e `0,1382` e Spearman entre `0,1308` e `0,1657`.

Nas regressões exploratórias com `log1p(incidência)`, efeitos fixos de
município e rodada e erro-padrão agrupado por município, o coeficiente
padronizado do IIP variou de `0,0386` a `0,0521`. Os resultados permanecem
sujeitos a sazonalidade, heterocedasticidade, clima, intervenções, sorotipos e
outros confundidores.

## Sandbox SIR

O módulo SIR implementa integração por Euler e `solve_ivp`, conserva
`S + I + R = N` e reporta `R₀ = β/γ` e `Rₑ(t) = R₀S(t)/N`. Casos notificados
são fluxos e não podem ser usados diretamente como o estoque `I(t)`.

O parâmetro `β` resume, de forma deliberadamente simplificada, o ciclo
humano–mosquito–humano. O modelo não representa explicitamente vetor, clima,
sorotipos, reinfecções ou mobilidade. Seus resultados dependem dos parâmetros
hipotéticos escolhidos pelo usuário.

## Reprodutibilidade, qualidade e privacidade

A auditoria automatizada verifica inventário, metadados e hashes dos artefatos.
Na conclusão deste relatório, 107 de 107 hashes foram verificados e a suíte
possuía 74 testes aprovados. O painel pode operar sobre
`database/dengue_rj_demo.duckdb`, que contém somente quatro tabelas agregadas.

Os dados brutos não devem ser publicados. Campos identificadores diretos são
proibidos no processamento seguro do SINAN. Resultados municipais,
especialmente em populações pequenas, exigem comunicação cuidadosa para evitar
estigma ou falsa precisão.

## Conclusão

O projeto entrega uma trilha auditável da coleta à visualização e demonstra um
forte crescimento da dengue em 2024, heterogeneidade municipal e
autocorrelação espacial positiva entre 2021 e 2024. As associações bivariadas
de saneamento em 2024 foram fracas, enquanto os índices LIRAa/LIA apresentaram
associações positivas pequenas com a incidência subsequente.

Esses achados orientam hipóteses e priorizam análises futuras, mas não sustentam
inferência causal nem previsão operacional. Os próximos avanços científicos
devem incorporar clima, densidade validada pela SES-RJ, sorotipos, mobilidade,
defasagens temporais e um desenho longitudinal explícito.

## Como reproduzir

As instruções completas estão em
[`tutorial_reproducibilidade.md`](tutorial_reproducibilidade.md). Relatórios
intermediários e tabelas de suporte ficam em `outputs/reports` e
`outputs/tables`; pressupostos e limitações adicionais estão em
[`metodologia.md`](metodologia.md) e [`limitacoes.md`](limitacoes.md).
