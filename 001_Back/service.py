from typing import List
from sympy import symbols, diff, Eq, solve, simplify, latex
from werkzeug.exceptions import BadRequest

from classes import (
    OptimizeRequest,
    OptimizeResponse,
    FitPoint,
    FitResponse,
    Derivation,
)


# ----------------------------------------------------------------------
# Parte simbólica: constrói q(p), π(p), π'(p), π''(p) e p*
# ----------------------------------------------------------------------
def _build_symbolic_model():
    """
    Constrói, simbolicamente, o modelo:

        q(p) = alpha - beta * p
        π(p) = p * q(p) - (F + c * q(p))

    E deriva:
        π'(p), π''(p), p* (ótimo interno, solução de π'(p)=0).
    """
    p = symbols("p", real=True)
    alpha, beta, c, F = symbols("alpha beta c F", real=True)

    # Demanda
    q = alpha - beta * p

    # Lucro
    pi = p * q - (F + c * q)

    # Derivadas
    dpi = diff(pi, p)
    d2 = diff(dpi, p)

    # p* tal que π'(p*) = 0
    p_star_solutions = solve(Eq(dpi, 0), p)
    p_star_expr = simplify(p_star_solutions[0]) if p_star_solutions else None

    return {
        "syms": (p, alpha, beta, c, F),
        "q": simplify(q),
        "pi": simplify(pi),
        "dpi": simplify(dpi),
        "d2": simplify(d2),
        "p_star": simplify(p_star_expr) if p_star_expr is not None else None,
    }


SYMS = _build_symbolic_model()


# ----------------------------------------------------------------------
# Serviço de otimização usando SymPy
# ----------------------------------------------------------------------
def optimize_with_sympy(req: OptimizeRequest) -> OptimizeResponse:
    """
    Recebe um OptimizeRequest (alpha, beta, c, F, pMin, pMax) e
    devolve um OptimizeResponse com o preço ótimo e métricas associadas.
    """
    if req.beta <= 0:
        raise BadRequest("beta deve ser > 0 (demanda precisa cair quando o preço sobe).")
    if req.pMin > req.pMax:
        raise BadRequest("pMax deve ser >= pMin.")

    p, alpha_s, beta_s, c_s, F_s = SYMS["syms"]

    # Fórmula simbólica de p*
    p_star_expr = SYMS["p_star"]
    if p_star_expr is None:
        raise BadRequest("Não foi possível determinar simbolicamente o preço ótimo.")

    # Substitui parâmetros na fórmula de p*
    p_star_num = float(
        p_star_expr.subs(
            {
                alpha_s: req.alpha,
                beta_s: req.beta,
                c_s: req.c,
            }
        ).evalf()
    )

    # Respeita domínio [pMin, pMax]
    p_opt = min(max(p_star_num, req.pMin), req.pMax)
    used_boundary = abs(p_opt - p_star_num) > 1e-12

    # Demanda ótima
    q_expr = SYMS["q"]
    q_opt = float(
        max(
            0.0,
            q_expr.subs(
                {alpha_s: req.alpha, beta_s: req.beta, p: p_opt}
            ).evalf(),
        )
    )

    # Receita e lucro
    revenue = p_opt * q_opt
    profit_opt = revenue - (req.F + req.c * q_opt)

    # Margem média (só custo variável)
    margin = (revenue - req.c * q_opt) / revenue if revenue > 0 else 0.0

    # Elasticidade-preço da demanda em p_opt
    elasticity = (
        (-req.beta * p_opt) / (req.alpha - req.beta * p_opt)
        if q_opt > 0
        else 0.0
    )

    # Strings simbólicas e LaTeX
    pi_str = str(SYMS["pi"])
    d1_str = str(SYMS["dpi"])
    d2_str = str(SYMS["d2"])
    pstar_str = str(p_star_expr)

    pi_latex = latex(SYMS["pi"])
    d1_latex = latex(SYMS["dpi"])
    d2_latex = latex(SYMS["d2"])
    pstar_latex = latex(p_star_expr)

    deriv = Derivation(
        objective=pi_str,
        d1=d1_str,
        d2=d2_str,
        pStarFormula=pstar_str,
        objective_latex=pi_latex,
        d1_latex=d1_latex,
        d2_latex=d2_latex,
        pStarFormula_latex=pstar_latex,
    )

    return OptimizeResponse(
        pOpt=p_opt,
        qOpt=q_opt,
        profitOpt=float(profit_opt),
        revenue=float(revenue),
        margin=float(margin),
        elasticity=float(elasticity),
        usedBoundary=used_boundary,
        derivation=deriv,
    )


# ----------------------------------------------------------------------
# Serviço de ajuste linear da demanda (OLS)
# ----------------------------------------------------------------------
def fit_linear(pontos: List[FitPoint]) -> FitResponse:
    """
    Ajusta uma reta q = intercept + slope * price aos dados (preço, quantidade)
    usando mínimos quadrados, e converte para o modelo:

        q(p) = alpha - beta * p, com beta > 0.

    Retorna alpha, beta, slope, intercept, r2.
    """
    n = len(pontos)
    if n < 2:
        raise BadRequest("Forneça pelo menos 2 pares (preço, quantidade).")

    # Somatórios básicos
    sumP = sum(pt.price for pt in pontos)
    sumQ = sum(pt.quantity for pt in pontos)
    sumPP = sum(pt.price * pt.price for pt in pontos)
    sumPQ = sum(pt.price * pt.quantity for pt in pontos)

    # Médias
    meanP = sumP / n
    meanQ = sumQ / n

    # Sxx e Sxy
    sxx = sumPP - n * meanP * meanP
    sxy = sumPQ - n * meanP * meanQ

    if abs(sxx) < 1e-12:
        raise BadRequest("Variância de preços ~ 0 (todos os preços são iguais).")

    # Coeficientes da regressão q = intercept + slope * p
    slope = sxy / sxx
    intercept = meanQ - slope * meanP

    # R²
    ss_tot = sum((pt.quantity - meanQ) ** 2 for pt in pontos)
    ss_res = sum(
        (pt.quantity - (intercept + slope * pt.price)) ** 2
        for pt in pontos
    )
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    # Conversão para q(p) = alpha - beta * p
    alpha = intercept
    beta = -slope  # queremos beta > 0, então slope deve ser < 0

    if beta <= 0:
        raise BadRequest(
            "Slope não negativo (demanda não cai com o preço). "
            "Verifique seus dados de (preço, quantidade)."
        )

    return FitResponse(
        alpha=float(alpha),
        beta=float(beta),
        slope=float(slope),
        intercept=float(intercept),
        r2=float(r2),
    )
