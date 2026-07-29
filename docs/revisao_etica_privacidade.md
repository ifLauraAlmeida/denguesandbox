# Revisão de ética, privacidade e linguagem

Data: 2026-07-29

## Dados individuais

Os arquivos SINAN originais são públicos, mas contêm registros individuais e
exigem minimização. O processador seleciona somente campos analíticos
predefinidos e exclui identificadores diretos, entre eles número da
notificação, nome do paciente, nome da mãe, CNS, logradouro, número,
complemento, bairro, CEP e telefone.

Sexo e idade codificada permanecem no fato local para possíveis análises
epidemiológicas, mas não são exibidos no painel nem exportados pela camada do
dashboard. Os arquivos brutos, processados e o DuckDB são ignorados pelo Git.

O painel consulta apenas tabelas municipais agregadas. Não há busca,
visualização ou exportação de registros individuais.

## Reidentificação

Mesmo sem identificadores diretos, combinações de município, data, idade,
sexo, evolução e óbito podem elevar risco de reidentificação, especialmente
em municípios pequenos. Por isso:

- não publicar o `fact_dengue` individual;
- não criar tabelas públicas com células pequenas sem regra de supressão;
- limitar a demonstração pública a agregados município-período;
- revisar qualquer futura estratificação antes da publicação.

## Linguagem epidemiológica

As saídas usam “casos prováveis” conforme a definição oficial: suspeitos
notificados, exceto descartados. Isso não equivale a casos confirmados. O
painel separa casos classificados explicitamente como dengue e classificações
ainda não rotuladas.

Correlações, regressões e clusters espaciais são descritos como exploratórios,
sem inferência causal. Cenários SIR são condicionais e hipotéticos, não
previsões, recomendações clínicas ou substitutos da vigilância.

## Limitações da revisão

Esta é uma revisão técnica, não um parecer jurídico ou de comitê de ética.
Antes de disponibilização pública, revisar termos das fontes, política
institucional, regras aplicáveis a dados de saúde e configuração do ambiente
de hospedagem.
