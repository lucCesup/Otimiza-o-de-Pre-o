from typing import List, Optional
from pydantic import BaseModel, Field


class OptimizeRequest(BaseModel):
    """
    Entrada para a otimização do preço.

    Modelo de demanda:
        q(p) = alpha - beta * p

    Função lucro:
        π(p) = p * q(p) - (F + c * q(p))
    """

    alpha: float = Field(ge=0, description="Demanda potencial (quando o preço tende a 0).")
    beta: float = Field(gt=0, description="Sensibilidade da demanda ao preço (queda por +1 real).")
    c: float = Field(ge=0, description="Custo variável por consulta.")
    F: float = Field(ge=0, description="Custo fixo mensal.")
    pMin: float = Field(ge=0, description="Preço mínimo permitido.")
    pMax: float = Field(ge=0, description="Preço máximo permitido.")


class Derivation(BaseModel):
    """
    Representa a derivação simbólica da função lucro, para uso em relatório/explicação.
    """
    objective: str       # π(p)
    d1: str              # π'(p)
    d2: str              # π''(p)
    pStarFormula: str    # fórmula simbólica de p*

    objective_latex: str
    d1_latex: str
    d2_latex: str
    pStarFormula_latex: str


class OptimizeResponse(BaseModel):
    """
    Resultado numérico da otimização.
    """
    pOpt: float          # preço ótimo
    qOpt: float          # quantidade ótima
    profitOpt: float     # lucro ótimo
    revenue: float       # receita em pOpt
    margin: float        # margem média (após custo variável)
    elasticity: float    # elasticidade-preço da demanda em pOpt
    usedBoundary: bool   # True se o ótimo está em pMin ou pMax
    derivation: Optional[Derivation] = None


class FitPoint(BaseModel):
    """
    Um ponto de dado real (preço, quantidade).
    """
    price: float
    quantity: float


class FitRequest(BaseModel):
    """
    Requisição para ajuste da curva de demanda.
    """
    data: List[FitPoint]


class FitResponse(BaseModel):
    """
    Resultado do ajuste linear da demanda:

    Ajusta: q = intercept + slope * p
    Converte para: q(p) = alpha - beta * p
    """
    alpha: float      # intercepto da demanda (demanda potencial)
    beta: float       # sensibilidade ao preço (> 0)
    slope: float      # slope original da regressão
    intercept: float  # intercept original da regressão
    r2: float         # coeficiente de determinação
