# Modelo SIR

`dS/dt = -βSI/N`, `dI/dt = βSI/N - γI` e `dR/dt = γI`, com `N=S+I+R`.

`R₀=β/γ` é o número básico do cenário; `Rₑ(t)=R₀S(t)/N`. No código, `initial_removed`, `basic_reproduction_number` e `effective_reproduction_number` são nomes distintos.

Euler existe para aprendizado; `solve_ivp` é a solução numérica padrão. Condições iniciais exigem histórico anterior suficiente para estimar `I₀`; `R₀` inicial deve ser zero, histórico, soroprevalência ou manual, sempre rotulado.

## Estoque ativo estimado

Casos notificados são fluxos e não equivalem diretamente a `I(t)`. O projeto
implementa duas aproximações, que devem receber também o histórico anterior ao
dia inicial de interesse:

- janela fixa: soma os casos dos últimos `d` dias;
- saída proporcional: `I(t) = I(t-1) + C(t) - γI(t-1)`, com `γ = 1/d`.

`compare_active_estimators` materializa os dois métodos e permite cenários
explícitos para a probabilidade de detecção `ρ`. A correção
`casos_notificados/ρ` é apenas uma hipótese de sensibilidade. O projeto não
estima `ρ` a partir dos dados disponíveis e não apresenta esses cenários como
medidas reais de subnotificação.

## Calibração exploratória

`fit_beta_temporal` ajusta `β` somente no início da série de infectados ativos
estimados. Quando há um período de validação, os pontos finais não participam
da otimização: são apenas projetados pelo parâmetro ajustado no treino.

O resultado registra intervalo de busca, objetivo MSE, convergência, MAE, RMSE,
resíduos completos e métricas separadas de treino e validação. Essas métricas
não tornam o ajuste automaticamente aceitável. Um critério de rejeição deve
ser definido antes da aplicação empírica e considerar escala, resíduos,
estabilidade e finalidade do cenário.
