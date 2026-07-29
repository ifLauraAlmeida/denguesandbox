# Diário de descoberta das fontes

## 2026-07-28 — Dimensão territorial

### IBGE

- Sistema: API de Localidades, versão documentada 1.0.0.
- Documentação: `https://servicodados.ibge.gov.br/api/docs/localidades`.
- Rota validada: `https://servicodados.ibge.gov.br/api/v1/localidades/estados/33/municipios`.
- Resultado observado: HTTP 200, JSON, 92 municípios e 92 identificadores únicos.
- Hash e horário: registrados em `data/metadata/dicionario_coleta.csv`.

A documentação da API declara que os identificadores das divisões político-administrativas são oficialmente designados pelo IBGE.

### Regiões de saúde

- Fonte: documento oficial da Superintendência de Atenção Primária à Saúde, SES-RJ.
- URL: `https://www.saude.rj.gov.br/comum/code/MostrarArquivo.php?C=NzIxMjc%2C`.
- Páginas usadas: 41–42.
- Resultado: nove regiões e 92 municípios após remoção de uma repetição de Itaperuna.
- Divergência nominal: a fonte escreve “Cachoeira de Macacu”; a API do IBGE retorna “Cachoeiras de Macacu”. O código usa o nome IBGE e preserva a decisão neste diário.

## 2026-07-28 — RIPSA / SES-RJ

### Evidência metodológica

A nota `Indicadores_demograficos.pdf` informa dois conjuntos:

1. população pactuada pela SES/CIB;
2. população estimada RIPSA/SVS para 2000–2024.

A nota registra município, região de saúde, região de governo, sexo e faixas etárias como seleções disponíveis. A nota metodológica RIPSA de 2025 descreve estimativas de população residente em 1º de julho, revisão anual, compatibilização territorial e uso de censos e projeções do IBGE.

### Endpoint antigo e bloqueio

O endereço citado em nota técnica da SES-RJ foi testado:

`https://sistemas.saude.rj.gov.br/tabnetbd/dhx.exe?populacao/pop_populacao_estimada.def`

Resultado observado em 2026-07-28:

- HTTP: 200;
- tipo: `text/html`;
- conteúdo: traceback Python com `IndexError`;
- conclusão: página de erro servida com sucesso HTTP aparente.

Esse endereço antigo não é utilizado pelo coletor. O bloqueio foi superado com o formulário funcional registrado a seguir.

### Formulário funcional confirmado

O responsável pelo projeto informou o formulário atualizado:

`https://sistemas.saude.rj.gov.br/tabnetbd/dhx.exe?populacao/pop_populacao_ripsa2024.def`

Validação em 2026-07-28:

- GET do formulário: HTTP 200, HTML, título de população residente 2000–2025;
- destino da consulta: POST para `webtabx.exe`;
- definição: `populacao/pop_populacao_ripsa2024.def`;
- linha: município com código;
- coluna: ano;
- medida: população estimada;
- filtros: ano, município, região, sexo e faixa etária;
- saída utilizada: link CSV gerado pelo próprio resultado TabNet.

A consulta completa de 2020–2024 retornou 92 municípios únicos por ano, totalizando 460 registros. Os CSVs apresentaram variação de codificação entre UTF-8 e Latin-1; a codificação detectada é mantida na saída processada. Os códigos de seis dígitos exibidos pelo TabNet foram conciliados com os códigos oficiais de sete dígitos da dimensão IBGE pelo prefixo validado, e não pela fabricação de dígito verificador.

## 2026-07-28 — Área territorial e densidade derivada (decisão revogada)

- Fonte: IBGE, Áreas Territoriais 2024.
- Arquivo: `AR_BR_RG_UF_RGINT_RGI_MUN_2024.xls`.
- Planilha utilizada: `AR_BR_MUN_2024`.
- Unidade: km².
- Resultado: 92 códigos municipais únicos do RJ, sem área ausente ou não positiva.

O IBGE informa que as áreas são reprocessadas anualmente e podem incorporar alterações legais, judiciais, político-administrativas e aprimoramentos cartográficos. Por isso, o pipeline não chama o resultado anual calculado de “densidade oficial”.

A densidade derivada chegou a ser calculada durante a exploração, mas seu uso foi revogado por decisão do responsável do projeto. O pipeline ativo não contém mais o coletor nem o comando associado.

Nova regra: usar densidade exclusivamente de `sistemas.saude.rj.gov.br`. A busca inicial localizou páginas dos “Retratos Municipais” com densidade bruta e líquida de 2012, insuficientes para representar automaticamente 2020–2024. A variável permanece pendente até que a tabela correta da SES-RJ seja identificada.

## 2026-07-28 — Transição SNIS/SINISA

Fontes oficiais localizadas:

- resultados SINISA: `https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/saneamento/sinisa/resultados-sinisa`;
- catálogo de arquivos SINISA: `https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/saneamento/sinisa/arquivos`;
- diagnósticos históricos SNIS: `https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/saneamento/snis/produtos-do-snis/diagnosticos-snis`.

O Ministério das Cidades informa que o SNIS encerrou suas atividades em 2023 e que o SINISA começou a operar em 2024. A primeira divulgação é chamada “SINISA 2024”, mas contém ano de referência 2023. Portanto, o pipeline não poderá usar diretamente o ano contido no nome do produto como ano dos dados.

Para 2020–2022, a fonte histórica é o SNIS. Para 2023, há os cinco módulos da primeira coleta SINISA: Gestão Municipal, Abastecimento de Água, Esgotamento Sanitário, Resíduos Sólidos e Águas Pluviais. Em 2026-07-28, a página pública de resultados localizada ainda descrevia essa primeira coleta com referência 2023. A disponibilidade pública de resultados com referência 2024 precisa ser confirmada antes de completar a série.

Os códigos SINISA não serão equiparados aos códigos SNIS apenas por semelhança nominal. O catálogo oficial contém glossários, planilhas de indicadores e uma planilha “de-para” SINISA–SNIS–ACERTAR; esses documentos formarão o inventário da próxima etapa.

### Coleta dos pacotes SINISA

Em 2026-07-28 foram baixados e preservados os cinco módulos da divulgação
SINISA 2024, todos com ano de referência 2023:

- Gestão Municipal (`xlsx`);
- Abastecimento de Água (`zip`);
- Esgotamento Sanitário (`zip`);
- Resíduos Sólidos (`rar`);
- Águas Pluviais (`rar`).

O HTML do catálogo oficial também foi preservado. As assinaturas dos formatos
foram validadas antes da gravação; os ZIPs e o XLSX passaram pela verificação
interna de integridade. Água e esgoto contêm bases municipais próprias, além de
consolidações e bases por prestador. Nenhum pacote foi tratado como se tivesse
ano de referência 2024.

A página oficial, atualizada em 02/07/2026, ainda descreve somente a primeira
coleta com referência 2023. Assim, não há evidência pública suficiente nessa
página para preencher 2024 como SINISA. A série 2020–2022 deverá ser obtida no
SNIS legado e harmonizada apenas com apoio do “de-para” oficial.

### SNIS — Série Histórica

O responsável pelo projeto indicou
`https://app4.cidades.gov.br/serieHistorica/`. A inspeção confirmou o título
“SNIS - Série Histórica”, versão pública 2024.006. O próprio aplicativo declara
que permite consultar informações e indicadores desde os primeiros anos de
coleta e oferece componentes para Água e Esgotos, Resíduos Sólidos, Municípios
e Águas Pluviais.

Este aplicativo é a fonte operacional correta para obter os anos históricos
anteriores à primeira coleta SINISA. Ele não transforma os dados antigos em
SINISA: a origem e os códigos continuarão identificados como SNIS, e qualquer
harmonização será registrada explicitamente.

### Contrato observado da consulta SNIS

A captura de rede fornecida pelo responsável do projeto revelou o endpoint
`POST /serieHistorica/agregado/getGridData`. O formulário envia os filtros
serializados dentro do campo `data`, resultando em dupla codificação URL. A
resposta é JSON no formato jqGrid e contém paginação, colunas, prestador,
município, ano e indicadores.

A consulta reproduzida selecionou 2020–2022, Rio de Janeiro e as famílias 9 e
10, correspondentes aos indicadores operacionais de água e esgoto. Foram
obtidos 183 registros no nível prestador-município-ano em 13 páginas:

| Ano | Registros | Municípios |
|---:|---:|---:|
| 2020 | 58 | 54 |
| 2021 | 60 | 52 |
| 2022 | 65 | 55 |

Há 65 municípios distintos no conjunto e 16 combinações município-ano com mais
de um prestador. Por isso, percentuais não serão somados ou promediados sem a
regra oficial de agregação. A saída longa preserva os seis indicadores
prioritários `IN015`, `IN016`, `IN046`, `IN049`, `IN055` e `IN056`, inclusive
valores ausentes. Os 13 JSONs brutos foram preservados separadamente.

### Resíduos sólidos — planilhas anuais

Como a rotina assíncrona `agrupamentoRs/getGridConfig` falhou ao tentar abrir
uma conexão HTTPS do servidor com ele mesmo, a coleta passou a usar os pacotes
ZIP oficiais dos Diagnósticos SNIS. Foram preservadas e verificadas as
planilhas nacionais de referência 2020, 2021 e 2022.

A tabela de indicadores foi filtrada por `UF=RJ`, conciliada com a dimensão
IBGE e convertida para formato longo sem eliminar valores ausentes:

| Ano | Municípios respondentes | Indicadores | Registros |
|---:|---:|---:|---:|
| 2020 | 84 | 47 | 3.948 |
| 2021 | 87 | 47 | 4.089 |
| 2022 | 88 | 47 | 4.136 |

A própria planilha de 2022 informa que indicadores dependentes da população
urbana foram removidos porque o Censo Demográfico 2022 ainda não havia
publicado esse dado. Por isso, `IN014`, `IN016`, `IN030`, `IN032` e `IN054`
estão integralmente ausentes em 2022 por decisão metodológica da fonte, e não
por falha do coletor. O `IN015`, baseado na população total, permanece
disponível para os 88 respondentes.

### Águas pluviais — planilhas anuais

Os pacotes nacionais oficiais `Planilhas_AP2020.zip`, `Planilhas_AP2021.zip`
e `Planilhas_AP2022.zip` foram baixados dos Diagnósticos SNIS, preservados
integralmente e validados como arquivos ZIP. A aba municipal da tabela de
indicadores foi filtrada por `UF=RJ`, conciliada com a dimensão IBGE e
convertida para formato longo:

| Ano | Municípios respondentes | Indicadores | Registros |
|---:|---:|---:|---:|
| 2020 | 77 | 25 | 1.925 |
| 2021 | 82 | 25 | 2.050 |
| 2022 | 86 | 25 | 2.150 |

Os 6.125 registros preservam família, código, nome, fórmula, unidade e valor
originais. Valores ausentes permanecem explícitos. A densidade demográfica da
área urbana (`IN043`) é um indicador do módulo de águas pluviais e não deve ser
confundida com a população residente da tabela RIPSA.

Com essa coleta, o SNIS 2020–2022 cobre os quatro componentes do saneamento
básico: o módulo Água e Esgoto fornece dois componentes distintos,
abastecimento de água e esgotamento sanitário; os outros módulos fornecem
resíduos sólidos e drenagem/manejo de águas pluviais.

### Inventário SNIS–SINISA

Foi criada uma dimensão preliminar com 253 registros de metadados originais:
87 variantes do SNIS e 166 indicadores do SINISA. Ela preserva sistema,
componente, código, nome, unidade, família, fórmula e intervalo de referência.

Foram identificadas nove variantes adicionais de metadados no SNIS, todas
mantidas com versão própria. Isso evita que mudanças de nome, unidade ou
fórmula sejam sobrescritas. Os campos padronizados permanecem vazios e o
status `pendente_de_para_oficial` até a conferência da planilha oficial
SINISA–SNIS–ACERTAR.

A publicação oficial foi localizada em:
`https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/saneamento/sinisa/arquivos/Planilha_De_Para_SINISA_SNIS_ACERTAR___20250623.pdf`.
A Nota Informativa SEI nº 5886717 registra a planilha como regra de transição
do SNIS para o SINISA. A extração e validação visual das tabelas são a próxima
etapa; a localização do documento, isoladamente, não autoriza preencher o
campo padronizado.

O PDF possui cinco páginas e 74 correspondências únicas: 26 diretas, 46 por
composição ou ajuste e duas sem correspondência identificada (`QD026` e
`QD027`). Vinte e seis linhas possuem comentário metodológico.

A inspeção visual e a extração tabular confirmaram que o documento relaciona
**informações** SNIS (`AG`, `ES`, `FN`, `QD`) a informações SINISA (`GTA`,
`GTE`, `GFI`, `OGM`). Ele não relaciona diretamente os indicadores calculados
SNIS (`IN`) aos indicadores SINISA (`IAG`, `IES`, `IFR`, `IRS`, `IAP`, `IGR`).
Consequentemente, a harmonização de indicadores exige combinar este de-para
com as fórmulas e glossários oficiais; igualar códigos ou nomes diretamente
seria metodologicamente incorreto.

### Comparabilidade prioritária — água e esgoto

Os glossários oficiais SNIS 2022 e SINISA referência 2023 foram preservados e
as páginas relevantes foram inspecionadas visualmente. A comparação dos seis
indicadores usados no pipeline resultou em:

| SNIS | SINISA | Classificação |
|---|---|---|
| `IN055` | `IAG0001` | comparável diretamente |
| `IN056` | `IES0001` | comparável diretamente |
| `IN049` | `IAG2013` | não comparável; denominador alterado |
| `IN015` | `IES2002` | similar; ruptura na definição do volume coletado |
| `IN016` | `IES2004` | similar; ruptura herdada no denominador |
| `IN046` | `IES2003` | comparável somente na base municipal |

O glossário SINISA chama os códigos SNIS de “correspondentes ou similares”; a
classificação acima refina essa indicação mediante comparação das fórmulas e
dos comentários do de-para. Somente `IN055 → IAG0001` e
`IN056 → IES0001` estão liberados para continuidade temporal direta.

### Valores municipais SINISA — referência 2023

As planilhas municipais oficiais da primeira divulgação SINISA foram
processadas para os quatro componentes. Códigos IBGE foram reconciliados com
os 92 municípios do estado, e os arquivos mantêm família, código, nome,
fórmula, unidade, valor original e situação da resposta.

| Componente | Municípios na base | Com valor numérico | Indicadores | Registros |
|---|---:|---:|---:|---:|
| Abastecimento de água | 92 | 92 | 55 | 5.060 |
| Esgotamento sanitário | 67 | 67 | 40 | 2.680 |
| Resíduos sólidos | 92 | 89 | 44 | 4.048 |
| Águas pluviais | 92 | 89 | 27 | 2.484 |

Água e esgoto estão no nível município–prestador; resíduos sólidos e águas
pluviais, no nível municipal. Textos como `Div/0`, `Dados Não Inf.` e
`Regra 2 Não Atend.` permanecem em `valor_origem` e `status_valor`, com
`valor` numérico nulo. Assim, valores não calculados não são convertidos em
zero. Em resíduos sólidos e águas pluviais, três municípios constam na base
como não respondentes/não participantes.

O relatório
`data/processed/saneamento/cobertura_saneamento_snis_sinisa_2020_2023.csv`
consolida a cobertura dos quatro componentes para SNIS 2020–2022 e SINISA
2023.

## 2026-07-29 — SINAN/Dengue por residência

A fonte selecionada é o conjunto oficial `Sinan/Dengue` do Portal de Dados
Abertos do SUS. O portal fornece CSVs nacionais anuais compactados, informa
atualização semanal e recomenda o local de residência para o cálculo da
incidência.

Regra territorial obrigatória: todas as linhas e agregações municipais usam
`ID_MN_RESI`. O código de seis dígitos publicado pelo SINAN é reconciliado
deterministicamente com o código IBGE de sete dígitos da `dim_municipio`.
Município de notificação não é aceito como substituto.

O piloto de 2020 preservou o ZIP nacional bruto e produziu um recorte
analítico sem identificador da notificação:

| Ano | Registros residentes no RJ | Municípios | Data de sintomas ausente |
|---:|---:|---:|---:|
| 2020 | 8.715 | 84 | 0 |
| 2021 | 5.793 | 82 | 0 |
| 2022 | 11.094 | 90 | 0 |
| 2023 | 49.951 | 92 | 0 |
| 2024 | 302.201 | 92 | 0 |

O arquivo contém casos suspeitos, incluindo descartados. Segundo o portal,
casos prováveis correspondem aos suspeitos exceto os descartados. A
classificação final moderna usa `5` para descartado, `10` para dengue, `11`
para dengue com sinais de alarme e `12` para dengue grave; códigos históricos
presentes na base permanecerão originais até validação específica. O eixo
temporal prioritário será `DT_SIN_PRI`, preservando `DT_NOTIFIC` para cálculo
do atraso.

Foi observada uma ruptura de domínio: `CLASSI_FIN=5` está presente em
2020–2021 e ausente em 2022–2024, enquanto os códigos `0` e `8`, não
pertencentes ao domínio moderno do dicionário consultado, aparecem em parte
da série. Esses códigos continuam sem rótulo inventado. Para a variável
booleana `caso_provavel`, porém, aplica-se literalmente a definição publicada
pelo Ministério da Saúde: todos os casos notificados, exceto os classificados
como descartados. Assim, somente `CLASSI_FIN=5` recebe
`caso_descartado=true`.

O DuckDB contém 377.754 registros em `stg_dengue` e `fact_dengue`, dos quais
370.730 são marcados como casos prováveis e 7.024 como descartados. Todas as
datas de primeiros sintomas foram convertidas; não foram encontrados atrasos
de notificação negativos. A mediana anual do atraso foi de quatro dias em
2020–2022 e três dias em 2023–2024.

Fontes oficiais:

- `https://dadosabertos.saude.gov.br/dataset/arboviroses-dengue`;
- `https://portalsinan.saude.gov.br/images/documentos/Agravos/Dengue/DIC_DADOS_ONLINE.pdf`.
