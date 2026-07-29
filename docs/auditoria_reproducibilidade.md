# Auditoria de reprodução em ambiente limpo

Data: 29 de julho de 2026.

## Procedimento

Foi criado um clone temporário isolado a partir da tag `v0.1.0`, sem copiar
arquivos ignorados, bancos ou dados locais do diretório de trabalho. Nesse
clone:

1. as dependências foram instaladas exclusivamente pelo `uv.lock`;
2. todas as fontes foram coletadas novamente;
3. todos os produtos processados e bancos foram reconstruídos;
4. as análises e o banco agregado de demonstração foram regenerados;
5. hashes, testes, lint e inicialização do Streamlit foram verificados.

O diretório original não foi usado como origem de dados e não foi alterado
durante a execução do pipeline.

## Resultados observados

- 75 pacotes instalados no ambiente virtual limpo;
- 92 municípios na dimensão territorial;
- 460 registros de população, correspondentes a 92 municípios × 5 anos;
- 15 levantamentos LIRAa/LIA harmonizados;
- 253 indicadores de saneamento inventariados;
- 14.272 registros municipais SINISA em quatro componentes;
- 12.173 registros de indicadores SNIS de resíduos sólidos;
- 6.125 registros de indicadores SNIS de águas pluviais;
- 377.754 notificações SINAN de 2020–2024 mantidas após o filtro por município
  de residência no Estado do Rio de Janeiro;
- indicadores, séries temporais, análises exploratórias, regressões, análise
  espacial e banco de demonstração reconstruídos;
- 84 de 84 hashes de artefatos reconstruídos verificados;
- 74 testes aprovados;
- lint aprovado;
- painel Streamlit iniciado sobre o banco agregado sem exceções.

## Conclusão

O pipeline foi reproduzido integralmente em um clone sem dados prévios. A
sequência efetivamente executada está registrada no
[`tutorial_reproducibilidade.md`](tutorial_reproducibilidade.md).

Os números de artefatos podem crescer em uma execução posterior porque nomes de
arquivos brutos incluem horário de coleta. A auditoria deve ser executada
somente depois de `refresh-file-control`, para que os hashes reflitam os
artefatos da reprodução corrente.
