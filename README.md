# Sandbox matemático da transmissão da dengue nos municípios do Estado do Rio de Janeiro

Jumpstart reprodutível para coleta, tratamento, análise e modelagem SIR da dengue nos 92 municípios fluminenses, entre 2020 e 2024.

> Este projeto possui finalidade acadêmica, metodológica e exploratória. As simulações não constituem previsão oficial, recomendação clínica ou substituição da vigilância epidemiológica.

## Pergunta de pesquisa

Em que medida indicadores municipais de saneamento apresentam associação estatística e espacial com a incidência de dengue? Correlação não implica causalidade: clima, urbanização, densidade, mobilidade, imunidade prévia, sorotipo, acesso, vigilância, subnotificação e controle vetorial são potenciais confundidores.

## Fontes e escopo

- Demografia: RIPSA / SES-RJ TabNet.
- Saneamento: SNIS 2020–2022 e SINISA referência 2023, cobrindo abastecimento
  de água, esgotamento sanitário, resíduos sólidos e drenagem/manejo de águas
  pluviais.
- Dengue: SINAN / DATASUS, por município de residência e preferencialmente pela data dos primeiros sintomas.
- Período: 2020–2024; abrangência: todos os municípios do Estado do Rio de Janeiro.

URLs, opções TabNet, indicadores e valores epidemiológicos só serão preenchidos após inspeção e validação das fontes. Os arquivos brutos são imutáveis e cada coleta registra origem, horário, filtros, status e SHA-256.

## Arquitetura

`raw → stg → dimensões/fatos → indicadores → SIR → visualizações`

Os arquivos originais ficam em `data/raw`, os produtos rastreáveis em `data/processed`, os metadados em `data/metadata` e o banco analítico em `database/dengue_rj.duckdb`. Junções territoriais usam `codigo_ibge_municipio`, nunca apenas o nome.

## Instalação e configuração

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
```

Copie `.env.example` para `.env` apenas se uma fonte validada exigir configuração. Edite os YAMLs em `config/`; campos `null` são intencionais.

## Uso

```bash
python -m dengue_rj.cli init-metadata
python -m dengue_rj.cli collect-territory
python -m dengue_rj.cli collect-demography
python -m dengue_rj.cli collect-sinan-pilot
python -m dengue_rj.cli process-sinan-pilot
python -m dengue_rj.cli collect-sinan
python -m dengue_rj.cli process-sinan
python -m dengue_rj.cli collect-snis-historical
python -m dengue_rj.cli collect-solid-waste
python -m dengue_rj.cli collect-stormwater
python -m dengue_rj.cli collect-sinisa
python -m dengue_rj.cli collect-sinisa-crosswalk
python -m dengue_rj.cli collect-sanitation-glossaries
python -m dengue_rj.cli build-sanitation-indicator-inventory
python -m dengue_rj.cli build-sinisa-crosswalk
python -m dengue_rj.cli build-sanitation-harmonization
python -m dengue_rj.cli process-sinisa-municipal
python -m dengue_rj.cli load-sanitation
python -m dengue_rj.cli load-dengue
python -m dengue_rj.cli calculate-dengue-indicators
python -m dengue_rj.cli build-dengue-time-series
python -m dengue_rj.cli collect --source all
python -m dengue_rj.cli process --source all
python -m dengue_rj.cli build-database
python -m dengue_rj.cli calculate-indicators
python -m dengue_rj.cli simulate --municipality-code 3304557 --population 100000 --infected 10 --beta 0.3 --gamma 0.1
python -m dengue_rj.cli generate-gif --input outputs/tables/3304557_simulacao_sintetica_sir.csv
python -m dengue_rj.cli validate
streamlit run app.py
```

`collect` recusa fontes sem URL validada. Isso evita fabricar endpoints. O comando `simulate` exige todos os valores hipotéticos na linha de comando e rotula a saída como sintética.

## Indicadores e SIR

Incidência é `casos / população × 100.000`; agregações usam a razão entre somas. Infectados ativos podem ser estimados por janela fixa ou saída proporcional. O SIR inclui Euler e `solve_ivp`, valida parâmetros, conserva `S + I + R = N` e calcula `R₀ = β/γ` e `Rₑ(t) = R₀S(t)/N`.

O `β` do SIR humano simplificado resume o ciclo humano–mosquito–humano. `R` significa “recuperados ou removidos”, com imunidade específica ao sorotipo assumido. Casos notificados não equivalem ao total de infecções. Consulte `docs/` para calibração, limitações e pressupostos.

## Calibração, GIF e aplicação

A base contém ajuste por mínimos quadrados a infectados ativos, com limites explícitos e métricas MAE/RMSE. Não se recomenda ajuste apenas a acumulados. O GIF usa posições fixas e estados reproduzíveis; não é uma simulação espacial nem individual.

A aplicação Streamlit usa somente dados sintéticos informados pelo usuário até que as fontes oficiais sejam coletadas e validadas.

## Testes e qualidade

```bash
make test
# ou
pytest
```

Os testes cobrem conservação, parâmetros, compartimentos, indicadores, estimadores, território, hashing, conteúdo HTTP inválido, metadados e GIF.

## Ética, limitações e licença

Evite reidentificação, inferências causais indevidas e comunicação de cenários como previsões. O SIR simples não representa vetor, clima, sorotipos ou reinfecções explicitamente. Licença MIT; fontes de dados mantêm suas próprias condições de uso.

## Referências

A principal referência conceitual planejada é *Dengue: teorias e práticas* (Editora Fiocruz). Capítulos, páginas e parâmetros permanecem `TODO` até validação bibliográfica em `docs/referencias_metodologicas.md`.
