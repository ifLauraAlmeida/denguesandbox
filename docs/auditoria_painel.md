# Auditoria funcional do painel

Data: 2026-07-29

## Escopo

Validação automatizada com `streamlit.testing.v1` sobre o banco local
processado, sem servidor externo.

## Resultados

- Estado inicial sem município selecionado: aprovado.
- Seleção explícita de Angra dos Reis: aprovada.
- Quatro abas carregadas sem exceções.
- Todos os campos interativos possuem rótulo textual.
- Mensagem explícita quando `I₀ + R inicial` excede a população RIPSA.
- Ausência de erros no cenário padrão.
- Tempo observado nesta máquina:
  - estado inicial: 2,15 segundos;
  - município selecionado: 1,07 segundo.
- GIF gerado somente por ação explícita, evitando custo em cada atualização.
- Tabelas, figura, relatório e GIF possuem botões com finalidade identificada.

## Limitações

O teste automatizado não substitui avaliação com leitores de tela, navegação
completa por teclado ou usuários com diferentes necessidades. Os mapas não
devem ser a única fonte para interpretar valores: tabelas e exportações
permanecem disponíveis.
