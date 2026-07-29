# Arquitetura

O fluxo é `fonte oficial → raw imutável → staging padronizado → dimensões/fatos DuckDB → indicadores → modelos → saídas`. Cada produto deve apontar para o bruto por metadados e hash. `codigo_ibge_municipio` é a chave territorial.

As tabelas `raw_*` preservam a origem; `stg_*` limpam tipos, datas e territórios; `dim_*` e `fact_*` alimentam análises. Alterações de schema devem ganhar versão.

`fact_sir_simulacao` armazena cenários explicitamente rotulados por
`execution_id`. A chave `(execution_id, tempo)` impede duplicação de uma
execução; novas simulações são acrescentadas e nunca substituem silenciosamente
uma execução anterior. Esses fatos são cenários matemáticos hipotéticos, não
observações epidemiológicas nem previsões oficiais.
