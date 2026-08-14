"""
This is a is a structural credit risk model that treats equity as a call option
on a firm's assets, and backs out an implied probability of default from
market-observable inputs.
"""

import math
from statistics import NormalDist

_N = NormalDist()


def norm_cdf(x):
    return _N.cdf(x)


def norm_pdf(x):
    return _N.pdf(x)


def kmv_default_barrier(short_term_debt, long_term_debt):
    """
    Uses Moody's KMV convention to calculate the debt barrier
    """
    return short_term_debt + 0.5 * long_term_debt


def d1_d2(V, D, r, T, sigma_V):
    if V <= 0 or D <= 0 or sigma_V <= 0 or T <= 0:
        raise ValueError("V, D, sigma_V, and T must all be positive.")
    d1 = (math.log(V / D) + (r + 0.5 * sigma_V ** 2) * T) / (sigma_V * math.sqrt(T))
    d2 = d1 - sigma_V * math.sqrt(T)
    return d1, d2


def equity_value_from_assets(V, D, r, T, sigma_V):
    d1, d2 = d1_d2(V, D, r, T, sigma_V)
    return V * norm_cdf(d1) - D * math.exp(-r * T) * norm_cdf(d2)


def solve_asset_value(E_observed, D, r, T, sigma_V, V_guess=None, tol=1e-8, max_iter=100):
    V = V_guess if V_guess is not None else E_observed + D  

    for _ in range(max_iter):
        d1, _ = d1_d2(V, D, r, T, sigma_V)
        E_model = equity_value_from_assets(V, D, r, T, sigma_V)
        delta = norm_cdf(d1)  

        if delta == 0:
            raise RuntimeError("Newton step failed: zero derivative. Check inputs.")

        error = E_model - E_observed
        V_new = V - error / delta

        if V_new <= 0:
            V_new = V / 2  

        if abs(V_new - V) < tol:
            return V_new

        V = V_new

    raise RuntimeError(f"Newton-Raphson did not converge after {max_iter} iterations.")


def first_passage_probability_of_default(V, D, r, T, sigma_V):
   
    x0 = math.log(V / D)
    if x0 <= 0:
        return 1.0  

    mu = r - 0.5 * sigma_V ** 2
    denom = sigma_V * math.sqrt(T)

    term1 = norm_cdf((-x0 - mu * T) / denom)

   
    exponent = -2 * mu * x0 / (sigma_V ** 2)
    try:
        scale_factor = math.exp(exponent)
    except OverflowError:
        scale_factor = float("inf") if exponent > 0 else 0.0

    term2 = scale_factor * norm_cdf((-x0 + mu * T) / denom)
    if math.isinf(term2) or math.isnan(term2):
        term2 = 0.0  

    pd = term1 + term2
    return min(max(pd, 0.0), 1.0)  


def calibrate(equity_series, D, r, T=1.0, trading_days_per_year=252, max_outer_iter=50, tol=1e-6):
    
    if len(equity_series) < 30:
        raise ValueError(
            "Need a reasonably long equity series (ideally 250+ daily "
            "observations, i.e. ~1 year) to get a stable volatility estimate."
        )

    
    equity_log_returns = [
        math.log(equity_series[i] / equity_series[i - 1])
        for i in range(1, len(equity_series))
    ]
    mean_ret = sum(equity_log_returns) / len(equity_log_returns)
    variance = sum((x - mean_ret) ** 2 for x in equity_log_returns) / (len(equity_log_returns) - 1)
    sigma_E = math.sqrt(variance * trading_days_per_year)  

    E_latest = equity_series[-1]
    sigma_V = sigma_E * E_latest / (E_latest + D)  

    asset_series = None
    for outer_iter in range(max_outer_iter):
       
        asset_series = []
        V_guess = None
        for E_t in equity_series:
            V_t = solve_asset_value(E_t, D, r, T, sigma_V, V_guess=V_guess)
            asset_series.append(V_t)
            V_guess = V_t

       
        asset_log_returns = [
            math.log(asset_series[i] / asset_series[i - 1])
            for i in range(1, len(asset_series))
        ]
        mean_asset_ret = sum(asset_log_returns) / len(asset_log_returns)
        asset_variance = sum((x - mean_asset_ret) ** 2 for x in asset_log_returns) / (len(asset_log_returns) - 1)
        sigma_V_new = math.sqrt(asset_variance * trading_days_per_year)

        if abs(sigma_V_new - sigma_V) < tol:
            sigma_V = sigma_V_new
            break
        sigma_V = sigma_V_new
    else:
        print(f"WARNING: sigma_V did not converge after {max_outer_iter} outer iterations "
              f"— results below may be unstable. Consider a longer equity series.")

    V_final = asset_series[-1]
    distance_to_default = (
        math.log(V_final / D) + (r - 0.5 * sigma_V ** 2) * T
    ) / (sigma_V * math.sqrt(T))
    probability_of_default = norm_cdf(-distance_to_default)
    probability_of_default_first_passage = first_passage_probability_of_default(
        V_final, D, r, T, sigma_V
    )

    return {
        "asset_value": V_final,
        "sigma_V": sigma_V,
        "sigma_E": sigma_E,
        "distance_to_default": distance_to_default,
        "probability_of_default": probability_of_default,
        "probability_of_default_first_passage": probability_of_default_first_passage,
        "outer_iterations": outer_iter + 1,
        "asset_series": asset_series,
    }
