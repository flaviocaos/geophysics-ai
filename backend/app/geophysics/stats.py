"""Helpers compartilhados: unidades, divisão segura, arredondamento/serialização e
o ajuste de reta por mínimos quadrados reutilizado por `seismic_refraction.py`
(e disponível a qualquer outro módulo que precise de um ajuste linear simples).

Mesmo padrão usado em toda a plataforma (ex.: `gnss-ai/app/gnss/stats.py`).
"""
from __future__ import annotations

import numpy as np


def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Divisão que nunca lança ZeroDivisionError nem produz inf/NaN silenciosos."""
    if denominator == 0 or not np.isfinite(denominator):
        return default
    result = numerator / denominator
    return result if np.isfinite(result) else default


def mgal_from_si(value_m_s2: float) -> float:
    """Converte aceleração de m/s² para mGal (1 mGal = 1e-5 m/s²)."""
    return float(value_m_s2) * 1.0e5


def round_floats(value, ndigits: int = 6):
    """Arredonda floats recursivamente em estruturas dict/list, para serialização JSON estável.

    numpy scalars (np.float64/np.bool_/np.int64) são convertidos para tipos
    nativos do Python — necessário porque `json.dumps` não serializa tipos numpy.
    """
    if isinstance(value, dict):
        return {k: round_floats(v, ndigits) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [round_floats(v, ndigits) for v in value]
    if isinstance(value, (np.floating,)):
        v = float(value)
        return round(v, ndigits) if np.isfinite(v) else None
    if isinstance(value, float):
        return round(value, ndigits) if np.isfinite(value) else None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def method_metadata(method: str, parameters: dict, uncertainty_note: str, limitations: str) -> dict:
    """Bloco padrão exigido em toda resposta de análise (ARQUITETURA.md §4):
    nunca reportar um número sem citar método, parâmetros e limitações."""
    return {
        "method": method,
        "parameters": parameters,
        "uncertainty_note": uncertainty_note,
        "limitations": limitations,
    }


def fit_line_least_squares(x: np.ndarray, y: np.ndarray) -> dict:
    """Ajusta `y = slope*x + intercept` por mínimos quadrados ordinários,
    reutilizado por `seismic_refraction.py` para ajustar cada ramo
    (direto/refratado) da curva tempo-distância.

    Retorna também o RMS dos resíduos e o número de pontos usados — uma
    reta ajustada com apenas 2 pontos tem RMS exatamente zero e nenhuma
    redundância para avaliar a qualidade do ajuste.
    """
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if x.shape != y.shape:
        raise ValueError("x e y devem ter o mesmo tamanho")
    if len(x) < 2:
        raise ValueError("são necessários ao menos 2 pontos para ajustar uma reta")

    A = np.column_stack([x, np.ones_like(x)])
    (slope, intercept), residuals_sum, rank, _ = np.linalg.lstsq(A, y, rcond=None)
    fitted = A @ np.array([slope, intercept])
    residuals = y - fitted
    rms = float(np.sqrt(np.mean(residuals ** 2)))

    return {
        "slope": float(slope),
        "intercept": float(intercept),
        "residual_rms": rms,
        "n_points": int(len(x)),
    }
