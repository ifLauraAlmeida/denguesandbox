# Tutorial de reprodutibilidade

## 1. Preparar o ambiente

Requisitos: Python 3.11 ou superior, Git e acesso às fontes oficiais.

```powershell
git clone <URL-DO-REPOSITORIO>
cd denguesandbox
uv sync --extra dev
```

O arquivo `uv.lock` fixa as dependências. Não use dados ou parâmetros
epidemiológicos externos sem registrar fonte e versão.

## 2. Coletar e processar

Os arquivos brutos ficam em `data/raw`, os processados em `data/processed` e
não são versionados no Git. A sequência integral validada é:

```powershell
uv run python -m dengue_rj.cli init-metadata

uv run python -m dengue_rj.cli collect-territory
uv run python -m dengue_rj.cli collect-demography
uv run python -m dengue_rj.cli collect-liraa
uv run python -m dengue_rj.cli collect-spatial-mesh
uv run python -m dengue_rj.cli process-liraa
uv run python -m dengue_rj.cli process-spatial-mesh

uv run python -m dengue_rj.cli collect-sinisa
uv run python -m dengue_rj.cli collect-sinisa-crosswalk
uv run python -m dengue_rj.cli collect-sanitation-glossaries
uv run python -m dengue_rj.cli collect-snis-historical
uv run python -m dengue_rj.cli collect-solid-waste
uv run python -m dengue_rj.cli collect-stormwater
uv run python -m dengue_rj.cli build-sanitation-indicator-inventory
uv run python -m dengue_rj.cli build-sinisa-crosswalk
uv run python -m dengue_rj.cli build-sanitation-harmonization
uv run python -m dengue_rj.cli process-sinisa-municipal

uv run python -m dengue_rj.cli collect-sinan
uv run python -m dengue_rj.cli process-sinan

uv run python -m dengue_rj.cli build-database
uv run python -m dengue_rj.cli load-demography
uv run python -m dengue_rj.cli load-sanitation
uv run python -m dengue_rj.cli load-liraa
uv run python -m dengue_rj.cli load-dengue

uv run python -m dengue_rj.cli calculate-dengue-indicators
uv run python -m dengue_rj.cli build-dengue-time-series
uv run python -m dengue_rj.cli build-exploratory-analysis
uv run python -m dengue_rj.cli build-liraa-analysis
uv run python -m dengue_rj.cli build-exploratory-regressions
uv run python -m dengue_rj.cli build-spatial-analysis
uv run python -m dengue_rj.cli build-demo-database
```

O SINAN é sempre processado por município de residência:

```powershell
uv run python -m dengue_rj.cli collect-sinan
uv run python -m dengue_rj.cli process-sinan
uv run python -m dengue_rj.cli load-dengue
```

A incidência do projeto é calculada por 1.000 habitantes.

## 3. Verificar integridade

```powershell
uv run python -m dengue_rj.cli refresh-file-control
uv run python -m dengue_rj.cli audit-release
uv run ruff check .
uv run pytest
```

O gate falha se houver hash divergente, arquivo ausente, possível segredo,
arquivo versionado acima do limite ou controle de arquivos vazio.

## 4. Criar demonstração agregada

```powershell
uv run python -m dengue_rj.cli build-demo-database
$env:DENGUE_RJ_DATABASE="database/dengue_rj_demo.duckdb"
uv run streamlit run app.py
```

O banco de demonstração contém somente dimensão municipal, indicadores anuais,
série mensal e saneamento. Ele não contém `fact_dengue`, staging ou arquivos
individuais.

## 5. Interpretar resultados

- casos prováveis não equivalem a casos confirmados;
- correlação e autocorrelação espacial não implicam causalidade;
- parâmetros SIR são hipotéticos enquanto não houver calibração validada;
- cenários não são previsões oficiais;
- nunca publique fatos individuais ou estratificações com risco de
  reidentificação.
