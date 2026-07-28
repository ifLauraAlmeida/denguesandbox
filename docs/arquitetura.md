# Arquitetura

O fluxo é `fonte oficial → raw imutável → staging padronizado → dimensões/fatos DuckDB → indicadores → modelos → saídas`. Cada produto deve apontar para o bruto por metadados e hash. `codigo_ibge_municipio` é a chave territorial.

As tabelas `raw_*` preservam a origem; `stg_*` limpam tipos, datas e territórios; `dim_*` e `fact_*` alimentam análises. Alterações de schema devem ganhar versão.
