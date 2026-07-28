# Modelo SIR

`dS/dt = -βSI/N`, `dI/dt = βSI/N - γI` e `dR/dt = γI`, com `N=S+I+R`.

`R₀=β/γ` é o número básico do cenário; `Rₑ(t)=R₀S(t)/N`. No código, `initial_removed`, `basic_reproduction_number` e `effective_reproduction_number` são nomes distintos.

Euler existe para aprendizado; `solve_ivp` é a solução numérica padrão. Condições iniciais exigem histórico anterior suficiente para estimar `I₀`; `R₀` inicial deve ser zero, histórico, soroprevalência ou manual, sempre rotulado.
