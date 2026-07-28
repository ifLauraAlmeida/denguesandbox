"""Solução e validação do modelo SIR simplificado."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.integrate import solve_ivp

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class SIRParameters:
    """Parâmetros e condições iniciais do SIR."""

    population: float
    initial_infected: float
    initial_removed: float
    beta: float
    gamma: float

    def validate(self) -> None:
        """Valida domínio e consistência das condições iniciais."""
        values = (self.population, self.initial_infected, self.initial_removed)
        if not all(np.isfinite(values)):
            raise ValueError(f"Condições devem ser finitas; recebido {values}")
        if self.population <= 0:
            raise ValueError(f"population deve ser > 0; recebido {self.population}")
        if min(self.initial_infected, self.initial_removed) < 0:
            raise ValueError("Compartimentos iniciais não podem ser negativos")
        if self.initial_infected + self.initial_removed > self.population:
            raise ValueError("initial_infected + initial_removed excede population")
        if not np.isfinite(self.beta) or self.beta < 0:
            raise ValueError(f"beta deve ser finito e >= 0; recebido {self.beta}")
        if not np.isfinite(self.gamma) or self.gamma <= 0:
            raise ValueError(f"gamma deve ser finito e > 0; recebido {self.gamma}")

    @property
    def initial_susceptible(self) -> float:
        return self.population - self.initial_infected - self.initial_removed

    @property
    def basic_reproduction_number(self) -> float:
        return self.beta / self.gamma


@dataclass(frozen=True)
class SIRResult:
    time: FloatArray
    susceptible: FloatArray
    infected: FloatArray
    removed: FloatArray
    new_infections: FloatArray
    new_removals: FloatArray
    effective_reproduction_number: FloatArray


def _derivative(state: FloatArray, params: SIRParameters) -> FloatArray:
    susceptible, infected, _ = state
    infections = params.beta * susceptible * infected / params.population
    removals = params.gamma * infected
    return np.array([-infections, infections - removals, removals], dtype=float)


def _result(time: FloatArray, states: FloatArray, params: SIRParameters) -> SIRResult:
    susceptible, infected, removed = states.T
    new_infections = params.beta * susceptible * infected / params.population
    new_removals = params.gamma * infected
    effective = params.basic_reproduction_number * susceptible / params.population
    return SIRResult(time, susceptible, infected, removed, new_infections, new_removals, effective)


def solve_euler(params: SIRParameters, days: int, step: float = 1.0) -> SIRResult:
    """Resolve o SIR por Euler explícito para fins didáticos."""
    params.validate()
    if days < 1 or step <= 0 or days / step % 1:
        raise ValueError(f"days >= 1 e days/step inteiro; recebido days={days}, step={step}")
    time = np.linspace(0.0, float(days), int(days / step) + 1)
    states = np.empty((len(time), 3), dtype=float)
    states[0] = (params.initial_susceptible, params.initial_infected, params.initial_removed)
    for index in range(1, len(time)):
        states[index] = states[index - 1] + step * _derivative(states[index - 1], params)
        if np.any(states[index] < -1e-9):
            raise ValueError("Euler gerou compartimento negativo; reduza step")
        states[index] = np.maximum(states[index], 0.0)
    return _result(time, states, params)


def solve_sir(params: SIRParameters, days: int, step: float = 1.0) -> SIRResult:
    """Resolve o SIR com scipy.integrate.solve_ivp."""
    params.validate()
    if days < 1 or step <= 0:
        raise ValueError(f"days e step devem ser positivos; recebido {days}, {step}")
    time = np.arange(0.0, days + step / 2, step)
    initial = [params.initial_susceptible, params.initial_infected, params.initial_removed]
    solution = solve_ivp(
        lambda _time, state: _derivative(state, params),
        (0.0, float(days)),
        initial,
        t_eval=time,
        rtol=1e-8,
        atol=1e-10,
    )
    if not solution.success:
        raise RuntimeError(f"solve_ivp falhou: {solution.message}")
    states = np.maximum(solution.y.T, 0.0)
    return _result(time, states, params)
