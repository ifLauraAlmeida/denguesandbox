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

Execute os comandos na ordem apresentada no `README.md`. Os arquivos brutos
ficam em `data/raw`, os processados em `data/processed` e não são versionados
no Git.

O SINAN deve ser sempre processado por município de residência:

```powershell
python -m dengue_rj.cli collect-sinan
python -m dengue_rj.cli process-sinan
python -m dengue_rj.cli load-dengue
```

Após carregar demografia, saneamento, dengue e LIRAa:

```powershell
python -m dengue_rj.cli calculate-dengue-indicators
python -m dengue_rj.cli build-dengue-time-series
python -m dengue_rj.cli build-exploratory-analysis
python -m dengue_rj.cli build-liraa-analysis
python -m dengue_rj.cli build-exploratory-regressions
python -m dengue_rj.cli process-spatial-mesh
python -m dengue_rj.cli build-spatial-analysis
```

A incidência do projeto é calculada por 1.000 habitantes.

## 3. Verificar integridade

```powershell
python -m dengue_rj.cli refresh-file-control
python -m dengue_rj.cli audit-release
python -m ruff check .
python -m pytest
```

O gate falha se houver hash divergente, arquivo ausente, possível segredo,
arquivo versionado acima do limite ou controle de arquivos vazio.

## 4. Criar demonstração agregada

```powershell
python -m dengue_rj.cli build-demo-database
$env:DENGUE_RJ_DATABASE="database/dengue_rj_demo.duckdb"
python -m streamlit run app.py
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
