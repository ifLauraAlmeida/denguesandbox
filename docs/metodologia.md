# Metodologia

Incidência municipal é `casos/população × 1.000`; a agregada é `Σcasos/Σpopulação × 1.000`. Atraso é a diferença entre notificação e primeiros sintomas.

Casos são fluxos, não o estoque `I(t)`. O estoque pode ser aproximado por janela fixa ou por `I_t = I_{t-1} + C_t - γI_{t-1}`. A calibração deve separar treino e validação, registrar objetivo, limites, convergência, MAE, RMSE e resíduos. Ajustar apenas acumulados é desencorajado.

## Densidade demográfica

A densidade será obtida exclusivamente de `sistemas.saude.rj.gov.br`. O projeto não calculará densidade dividindo população RIPSA por área territorial externa.

Até a validação da tabela apropriada da SES-RJ, a variável permanece ausente. Os “Retratos Municipais” localizados apresentam densidade bruta e líquida com referência 2012 e não serão usados automaticamente como se representassem 2020–2024.

Associações com saneamento serão avaliadas por estatísticas descritivas, Pearson, Spearman, regressões exploratórias e, quando houver geometria validada, análise espacial. Não há inferência causal sem desenho e controle adequados.
