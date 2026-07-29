# Backlog e plano de execução

Atualizado em: 2026-07-29  
Horizonte dos dados: 2020–2024  
Abrangência: 92 municípios do Estado do Rio de Janeiro

## Objetivo final

Entregar uma plataforma reprodutível que colete dados públicos oficiais, preserve sua proveniência, produza indicadores municipais de dengue e saneamento, estime compartimentos epidemiológicos e permita explorar cenários SIR por município.

O produto final deverá combinar:

1. pipeline auditável de dados;
2. banco DuckDB documentado;
3. análise epidemiológica e de saneamento;
4. modelo SIR calibrado e validado;
5. aplicação Streamlit para comparação de cenários;
6. gráficos, tabelas, mapas, relatórios e GIFs reproduzíveis;
7. comunicação explícita de incertezas e limitações.

As simulações serão condicionadas aos dados e às hipóteses. Não serão tratadas como previsões oficiais.

## Perguntas que guiam o projeto

1. Qual foi a evolução temporal da dengue em cada município entre 2020 e 2024?
2. Como população, densidade e indicadores de saneamento variam entre municípios?
3. Há associação estatística ou espacial entre saneamento e incidência?
4. Quanto as conclusões mudam após considerar ano, população, densidade e dados ausentes?
5. Quais cenários SIR são compatíveis com os casos observados e com as hipóteses validadas?
6. Quão sensíveis são as simulações ao período infeccioso, subnotificação, imunidade inicial e transmissão?

## Princípios de execução

Prioridade: `rastreabilidade → qualidade → clareza metodológica → correção matemática → visualização`.

- Nenhuma URL, opção TabNet, variável, indicador ou parâmetro será presumido.
- Arquivos brutos serão imutáveis e identificados por SHA-256.
- Toda transformação deverá apontar para o arquivo e a versão de origem.
- Junções territoriais usarão código IBGE.
- Dados observados, estimados e hipotéticos terão rótulos distintos.
- Correlação não será descrita como causalidade.
- Uma fase só alimentará a seguinte após cumprir seu critério de saída.

## Estado geral

| Marco | Estado | Resultado esperado |
|---|---|---|
| M0 — Fundação técnica | Concluído | Repositório instalável e testado |
| M1 — Fontes e referências validadas | Em andamento | Contratos de dados documentados |
| M2 — Coleta reprodutível | Parcial | Brutos oficiais 2020–2024 |
| M3 — Processamento e banco | Parcial | Fatos e dimensões validados |
| M4 — Indicadores e análise descritiva | Pendente | Painel analítico municipal |
| M5 — Compartimentos e calibração | Parcial | Séries e ajustes por município |
| M6 — Saneamento e análise espacial | Pendente | Resultados associativos robustos |
| M7 — Produto interativo | Concluído | Streamlit integrado aos dados |
| M8 — Auditoria e publicação | Pendente | Versão final reproduzível |

## M0 — Fundação técnica

Estado: concluído.

- [x] Criar estrutura `raw`, `processed`, `metadata`, banco e saídas.
- [x] Criar pacote Python instalável e CLI.
- [x] Definir schemas dos quatro CSVs de metadados.
- [x] Criar tabelas mínimas no DuckDB.
- [x] Implementar SIR por Euler e `solve_ivp`.
- [x] Implementar estimadores de infectados ativos.
- [x] Criar calibração exploratória inicial.
- [x] Criar GIF e aplicação Streamlit com dados sintéticos.
- [x] Criar documentação inicial e guia de commits.
- [x] Executar testes e lint.

Critério de saída cumprido: instalação, banco, simulação sintética, GIF e testes funcionam.

## M1 — Descoberta e validação das fontes

Objetivo: transformar cada fonte oficial em um contrato de dados verificável antes de automatizar a coleta.

### M1.1 — Dimensão territorial

- [x] Localizar fonte oficial dos municípios do RJ e respectivos códigos IBGE.
- [x] Validar os 92 códigos, nomes, UF e código da UF.
- [x] Localizar e validar regiões de saúde.
- [x] Registrar data, URL e versão da dimensão.
- [x] Criar registro explícito de divergências de nomes.

### M1.2 — RIPSA / SES-RJ TabNet

- [x] Identificar formulário oficial funcional informado pelo responsável do projeto.
- [x] Validar formulário GET, destino POST e exportação CSV.
- [x] Documentar parâmetros reais de POST, opções, formatos e limites observados.
- [x] Confirmar na nota técnica estimativas anuais de população para 2000–2024.
- [ ] Localizar e validar densidade municipal publicada em `sistemas.saude.rj.gov.br`; não confundir a tabela RIPSA de população com densidade.
- [x] Verificar metodologia, revisões, projeções e denominador populacional.
- [x] Salvar formulário e HTML puro da resposta TabNet sem processá-los.
- [x] Coletar e validar 2020–2024 para os 92 municípios.
- [x] Preservar em `processed` o CSV oficial obtido por “Salva como CSV”.

### M1.3 — SINISA

- [x] Identificar catálogos oficiais SINISA e SNIS legado.
- [x] Validar o aplicativo oficial SNIS — Série Histórica.
- [x] Inventariar e coletar os cinco módulos oficiais SINISA com referência 2023.
- [x] Inventariar indicadores operacionais de água e esgoto selecionados.
- [x] Inventariar códigos, nomes, unidades, famílias e fórmulas originais.
- [x] Localizar a publicação oficial “De-Para SINISA–SNIS–ACERTAR”.
- [x] Preservar, renderizar e extrair o “de-para” oficial em formato tabular.
- [x] Confirmar que o documento relaciona informações, não indicadores calculados.
- [x] Comparar fórmulas dos seis indicadores prioritários de água e esgoto.
- [x] Processar valores municipais SINISA 2023 dos quatro componentes.
- [ ] Validar mudanças metodológicas SNIS → SINISA com o “de-para” oficial.
- [x] Avaliar cobertura municipal e valores ausentes na extração SNIS 2020–2022.
- [ ] Definir tabela de correspondência original → padronizado.

### M1.4 — SINAN / DATASUS

- [x] Identificar acesso oficial e granularidade disponível.
- [x] Confirmar campos de município de residência (`ID_MN_RESI`) e sintomas (`DT_SIN_PRI`).
- [ ] Verificar classificações finais e critérios por ano, incluindo códigos históricos.
- [x] Confirmar regra oficial de casos prováveis: suspeitos exceto descartados.
- [x] Separar casos prováveis de classificações explícitas de dengue no indicador.
- [ ] Documentar mudanças de layout e codificação.
- [ ] Definir tratamento seguro para dados potencialmente sensíveis.

### M1.5 — Referência epidemiológica

- [ ] Confirmar edição da obra *Dengue: teorias e práticas*.
- [ ] Registrar capítulo e página do período infeccioso.
- [ ] Registrar capítulo e página da incubação e viremia.
- [ ] Documentar transmissão, sorotipos, imunidade e limitações.
- [ ] Preencher parâmetros somente após dupla conferência.

### M1.6 — LIRAa/LIA

- [x] Identificar a página oficial e os ZIPs anuais da SES-RJ.
- [x] Coletar e validar as planilhas de 2020–2024.
- [x] Reconciliar códigos municipais exclusivamente por código IBGE.
- [x] Preservar IIP, IB, estratos, criadouros, período e status.
- [x] Produzir relatório de cobertura por levantamento.
- [ ] Validar valores extremos com a SES-RJ antes de modelagem.

Critério de saída: cada fonte possui URL oficial, contrato, campos, filtros, amostra, limitações e responsável pela validação; os parâmetros epidemiológicos possuem citação completa.

## M2 — Coleta reprodutível

Objetivo: obter os arquivos oficiais de 2020–2024 sem alterar o conteúdo original.

- [x] Implementar coletor territorial.
- [x] Implementar coletor RIPSA.
- [x] Implementar coletor SINISA para a divulgação oficial com referência 2023.
- [x] Implementar coletor SNIS Série Histórica para água e esgoto em 2020–2022.
- [x] Coletar e processar as planilhas anuais SNIS de resíduos sólidos de 2020–2022.
- [x] Coletar e processar as planilhas anuais SNIS de águas pluviais de 2020–2022.
- [x] Implementar coletor SINAN para os CSVs anuais oficiais.
- [x] Coletar e processar SINAN/Dengue 2020–2024 por residência.
- [x] Salvar bruto RIPSA antes de qualquer transformação.
- [ ] Impedir sobrescrita silenciosa.
- [ ] Registrar requisição, filtros, HTTP, horário, tamanho e SHA-256.
- [ ] Detectar resposta vazia e página de erro em HTTP 200.
- [ ] Implementar repetição controlada e retomada segura.
- [x] Criar testes unitários do contrato de formulário e exportação RIPSA.
- [x] Criar relatório de cobertura por fonte e ano para saneamento.
- [x] Executar coleta piloto de um ano (2020).
- [x] Revisar contrato territorial, campos e cobertura do piloto.
- [x] Executar coleta RIPSA completa de 2020–2024.

Critério de saída: toda coleta pode ser repetida, auditada e ligada a um registro de metadados; nenhuma fonte contém lacuna silenciosa.

## M3 — Processamento, qualidade e DuckDB

Objetivo: construir tabelas padronizadas, rastreáveis e adequadas para análise.

### Territorial e temporal

- [ ] Padronizar códigos e nomes sem perder valores originais.
- [ ] Impedir junções baseadas apenas em texto.
- [x] Criar `dim_municipio` oficial.
- [ ] Criar `dim_tempo` diária, semanal, mensal e anual.
- [ ] Validar datas, semanas epidemiológicas e limites 2020–2024.

### Demografia

- [x] Tipar população, município e ano; densidade segue pendente de fonte oficial.
- [ ] Documentar ausência, revisão, projeção ou interpolação.
- [x] Popular `stg_demografia` e `fact_demografia` com população RIPSA.

### Saneamento

- [x] Preservar nome, código, unidade, valor e status originais nos arquivos processados SNIS/SINISA.
- [x] Cobrir os quatro componentes legais: água, esgoto, resíduos sólidos e águas pluviais.
- [x] Criar dimensão preliminar de indicadores originais SNIS/SINISA.
- [x] Classificar comparabilidade dos seis indicadores prioritários de água e esgoto.
- [ ] Criar dimensão harmonizada somente após validação do “de-para” oficial.
- [ ] Harmonizar apenas indicadores metodologicamente comparáveis.
- [x] Marcar rupturas prioritárias, valores não calculados, não participação e dados ausentes.
- [x] Popular `stg_saneamento` e `fact_saneamento`.

### LIRAa/LIA

- [x] Popular `stg_liraa` e `fact_liraa`.
- [x] Criar painel município–levantamento com dengue mensal.
- [x] Preservar status, ausências e flag de valor extremo.

### Dengue

- [ ] Padronizar classificações e critérios por versão da fonte.
- [x] Marcar descartados e casos prováveis com regra oficial auditável.
- [x] Definir primeiros sintomas (`DT_SIN_PRI`) como eixo temporal prioritário.
- [x] Preservar notificação para cálculo de atraso.
- [ ] Detectar duplicidades sem apagar silenciosamente.
- [x] Popular `stg_dengue` e `fact_dengue` exclusivamente por residência.

### Validação

- [ ] Criar testes de schema, domínio, unicidade e integridade.
- [ ] Criar relatório de linhas rejeitadas.
- [x] Criar relatório de cobertura município × ano para saneamento.
- [x] Reconciliar os totais populacionais processados com os totais oficiais.
- [ ] Atualizar dicionários de variáveis e controle de arquivos.

Critério de saída: fatos reconciliados com as fontes, chaves íntegras, ausências explícitas e relatório de qualidade aprovado.

## M4 — Indicadores epidemiológicos

Objetivo: produzir medidas municipais comparáveis e documentadas.

- [x] Calcular casos prováveis por município e ano dos primeiros sintomas.
- [x] Calcular incidência municipal por 1.000 habitantes com população RIPSA.
- [x] Calcular incidência agregada pela razão entre somas.
- [x] Calcular atraso de notificação.
- [ ] Produzir média, mediana, percentis e distribuição do atraso.
- [x] Criar indicadores de cobertura e qualidade dos dados do SINAN.
- [x] Materializar tabelas por semana, mês e ano.
- [ ] Implementar tratamento explícito de divisão por zero e ausentes.
- [ ] Registrar fórmulas no dicionário de cálculos.
- [ ] Validar resultados contra consultas oficiais de referência.

Critério de saída: indicadores reproduzíveis, reconciliados e disponíveis por município e período, com denominadores identificáveis.

## M5 — Compartimentos, SIR e calibração

Objetivo: construir cenários matemáticos condicionados aos dados observados.

### Estimativa de compartimentos

- [ ] Validar o período infeccioso na literatura.
- [ ] Carregar histórico anterior ao início de cada simulação.
- [ ] Aplicar janela fixa.
- [ ] Aplicar saída proporcional.
- [ ] Comparar os dois métodos.
- [ ] Implementar cenários para `initial_removed`.
- [ ] Implementar sensibilidade à probabilidade de detecção `ρ`.

### Calibração

- [ ] Ajustar a casos incidentes.
- [ ] Ajustar ao estoque ativo estimado.
- [ ] Separar treino e validação temporal.
- [ ] Definir limites e valores iniciais justificados.
- [ ] Registrar objetivo, convergência, MAE, RMSE e resíduos.
- [ ] Implementar análise de sensibilidade.
- [ ] Comparar Euler e `solve_ivp`.
- [ ] Definir critérios para rejeitar ajustes ruins.
- [ ] Popular `fact_sir_simulacao`.

### Cenários

- [ ] Criar cenário base.
- [ ] Criar redução hipotética de transmissão.
- [ ] Criar cenários de detecção sem atribuir realidade aos valores.
- [ ] Criar cenários de imunidade inicial.
- [ ] Calcular pico, dia do pico, acumulado, `R₀` e `Rₑ(t)`.
- [ ] Gerar relatório metodológico por execução.

Critério de saída: cada cenário informa dados de entrada, hipóteses, versão, ajuste, incerteza e limitações; não há parâmetro sem fonte ou rótulo hipotético.

## M6 — Saneamento, associação e análise espacial

Objetivo: responder à pergunta de pesquisa sem extrapolar causalidade.

- [x] Descrever cobertura, distribuição, extremos e ausências.
- [ ] Cruzar saneamento, incidência, população e densidade.
- [x] Calcular Pearson e Spearman na seção transversal SINISA 2023.
- [x] Calcular associações exploratórias LIRAa–dengue com defasagens de 0–3 meses.
- [x] Produzir dispersões com identificação de extremos.
- [x] Implementar regressões exploratórias para o painel LIRAa.
- [x] Avaliar `log1p` do desfecho e heterocedasticidade.
- [x] Incluir ajuste temporal, efeitos fixos de município/rodada e erros agrupados.
- [x] Obter malha municipal oficial e documentar versão.
- [x] Construir matriz de vizinhança com regra explícita.
- [x] Avaliar autocorrelação espacial global e local.
- [x] Testar sensibilidade espacial com pesos torre e k-vizinhos.
- [x] Testar sensibilidade à retirada individual de municípios extremos.
- [x] Documentar fatores de confusão não observados.
- [x] Usar linguagem associativa, nunca causal.

Critério de saída: resultados reproduzíveis, acompanhados de diagnóstico, sensibilidade, limitações e separação explícita entre associação, correlação espacial, plausibilidade e causalidade.

## M7 — Produto interativo e comunicação

Objetivo: tornar resultados auditáveis e compreensíveis sem ocultar pressupostos.

- [x] Conectar Streamlit ao DuckDB.
- [x] Selecionar município sem padrão silencioso.
- [x] Selecionar intervalo compatível com os dados.
- [x] Exibir casos, incidência, saneamento e qualidade.
- [x] Permitir ajuste de parâmetros e cenários.
- [x] Informar unidade, fonte e natureza de cada parâmetro.
- [x] Comparar base e intervenção.
- [x] Exibir curvas, pico, acumulado, `R₀` e `Rₑ(t)`.
- [x] Exportar tabela, figura e relatório.
- [x] Gerar GIF com semente e resolução configuráveis.
- [x] Adicionar mapas após validação espacial.
- [x] Criar avisos permanentes de uso e limitações.
- [x] Testar acessibilidade, desempenho e mensagens de erro.

Critério de saída: um usuário consegue selecionar um município, entender a origem dos dados, reproduzir um cenário e exportar resultados sem interpretá-los como previsão.

## M8 — Auditoria, reprodutibilidade e publicação

Objetivo: preparar uma versão final verificável por terceiros.

- [x] Executar pipeline do zero em ambiente limpo.
- [x] Fixar versões e produzir arquivo de lock.
- [x] Executar testes, lint e cobertura.
- [x] Auditar segredos e arquivos grandes.
- [x] Conferir hashes e metadados.
- [x] Inventariar licenças das dependências; termos das fontes seguem pendentes.
- [x] Revisar ética, privacidade e linguagem epidemiológica.
- [x] Criar relatório final.
- [x] Criar tutorial reproduzível.
- [x] Criar versão de demonstração sem dados sensíveis.
- [x] Publicar release com changelog e tag.

Critério de saída: terceiro consegue instalar, reconstruir o banco e reproduzir os principais resultados seguindo apenas a documentação.

## Ordem recomendada para as próximas sessões

### Sprint 1 — Contratos oficiais

1. Dimensão municipal.
2. RIPSA.
3. SINISA.
4. SINAN.
5. Referência Fiocruz.

Entrega: documento de descoberta das fontes, amostras brutas e decisão de viabilidade.

### Sprint 2 — Coleta piloto

1. Implementar infraestrutura comum de metadados.
2. Implementar um coletor completo.
3. Rodar um ano piloto.
4. Reconciliar e revisar.
5. Replicar o padrão nas demais fontes.

Entrega: coleta piloto auditável e testes simulados.

### Sprint 3 — Camada analítica

1. Dimensões territorial e temporal.
2. Processadores.
3. Regras de qualidade.
4. DuckDB.
5. Reconciliação.

Entrega: banco validado com cobertura e inconsistências conhecidas.

### Sprint 4 — Indicadores e compartimentos

1. Casos, incidência e atraso.
2. Métodos de infectados ativos.
3. Parâmetros bibliográficos.
4. Calibração inicial.
5. Sensibilidade.

Entrega: primeira análise municipal reproduzível.

### Sprint 5 — Pesquisa e produto

1. Saneamento e dengue.
2. Análise espacial.
3. Integração Streamlit.
4. Exportações e relatórios.
5. Auditoria final.

Entrega: produto acadêmico final.

## Ritual de trabalho

Em cada sessão:

1. escolher um item desbloqueado e seu critério de aceite;
2. registrar fontes e decisões antes de programar;
3. implementar em pequena unidade testável;
4. executar testes e validações;
5. atualizar metadados e documentação;
6. marcar o item somente após evidência;
7. registrar bloqueios, riscos e próximo item.

## Definição de pronto

Um item só está pronto quando:

- código, configuração e documentação concordam;
- há teste automatizado proporcional ao risco;
- I/O externo possui simulação;
- erros informam valor recebido e formato esperado;
- saídas têm fonte, versão e data;
- não há dado ou parâmetro inventado;
- limitações e ausências estão registradas;
- lint e testes passam;
- o resultado pode ser repetido por outra pessoa.

## Riscos e decisões pendentes

| Risco/decisão | Impacto | Mitigação |
|---|---|---|
| Endpoints oficiais instáveis | Alto | preservar bruto, versionar contrato e testar mudanças |
| Mudança SINISA/SINAN entre anos | Alto | manter código/nome original e harmonização versionada |
| Acesso apenas agregado | Alto | respeitar granularidade e adaptar perguntas/modelo |
| Parâmetros epidemiológicos sem página validada | Alto | manter `null` e bloquear calibração oficial |
| Subnotificação | Alto | cenários de sensibilidade, nunca correção apresentada como real |
| Ausência de clima e sorotipo | Médio/alto | declarar confundimento e preparar extensão futura |
| Dados municipais ausentes | Médio | relatório de cobertura e análise de sensibilidade |
| SIR inadequado ao ciclo vetorial | Alto | uso didático, limites explícitos e extensão futura vetorial |

## Próxima ação recomendada

Conectar o Streamlit ao DuckDB e incorporar os indicadores e mapas já
validados, sem seleção municipal silenciosa. Não agregar a série SNIS nos
municípios com múltiplos prestadores sem regra metodológica validada. A
densidade permanece fora dos modelos até localizar e validar sua tabela
específica no SES-RJ.
