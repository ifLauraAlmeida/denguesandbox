# Changelog

Todas as mudanças relevantes deste projeto serão registradas neste arquivo.
O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e o versionamento segue [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [0.1.0] — 2026-07-29

### Adicionado

- Pipeline reproduzível de coleta, processamento e auditoria de população,
  dengue, saneamento, LIRAa/LIA e malha municipal.
- Banco analítico DuckDB com dimensões, fatos e séries municipais.
- Processamento do SINAN exclusivamente por município de residência
  (`ID_MN_RESI`).
- Indicadores anuais de casos prováveis e classificados de dengue.
- Integração de saneamento SNIS 2020–2022 e SINISA 2023 para água, esgoto,
  resíduos sólidos e águas pluviais.
- Análises exploratórias de saneamento, LIRAa/LIA e autocorrelação espacial.
- Sandbox SIR com Euler e `solve_ivp`, exportação de cenários e GIF agregado.
- Painel Streamlit municipal com mapas e cenários parametrizáveis.
- Banco de demonstração contendo somente agregados municipais.
- Tutorial de reprodução, relatório final e auditoria automatizada da release.

### Alterado

- Incidência municipal e estadual expressa por 1.000 habitantes.
- Linguagem epidemiológica revisada para distinguir associação, cenário e
  previsão.

### Segurança e privacidade

- Identificadores diretos são proibidos no processamento seguro do SINAN.
- A versão pública de demonstração exclui notificações individuais.
- Arquivos brutos permanecem fora do versionamento.

### Limitações conhecidas

- Associações são exploratórias e não causais.
- A densidade municipal da SES-RJ ainda requer fonte temporal validada.
- Indicadores SNIS com múltiplos prestadores não são agregados sem regra
  substantiva validada.
- Ausências nas bases de saneamento não são convertidas em zero.

[0.1.0]: https://github.com/ifLauraAlmeida/denguesandbox/releases/tag/v0.1.0
