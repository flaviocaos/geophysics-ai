"""Resistividade aparente de sondagem elétrica vertical (SEV) a partir de
arranjos eletródicos padrão (Wenner e Schlumberger) — cada arranjo tem um
"fator geométrico" `K` que converte a razão medida `V/I` (tensão sobre
corrente injetada) numa resistividade aparente `rho_a = K * (V/I)`:

    Wenner (espaçamento único `a` entre todos os eletrodos adjacentes):
        K = 2*pi*a
        rho_a = 2*pi*a*(V/I)

    Schlumberger (eletrodos de corrente `AB`, separados por `L`; eletrodos
    de potencial `MN`, separados por `l`, ambos centrados no mesmo ponto):
        K = pi*((L/2)^2 - (l/2)^2)/l
        rho_a = pi*((L/2)^2 - (l/2)^2)/l * (V/I)

Referência: Telford, W.M., Geldart, L.P., Sheriff, R.E. (1990), "Applied
Geophysics", 2ª ed., cap. 8 — os mesmos fatores geométricos usados por
praticamente todo software de inversão de SEV 1D.

Este módulo NÃO faz inversão 1D de camadas (que exigiria um modelo de terra
em camadas e um algoritmo de otimização não-linear, ex.: mínimos quadrados
amortecidos sobre curvas de resistividade teóricas) — apenas calcula a curva
de resistividade aparente vs. espaçamento (um proxy comum de profundidade de
investigação) a partir das leituras de campo, e uma profundidade de
investigação estimada por uma regra heurística simples e amplamente citada
na literatura (`a/2` para Wenner; ver `limitations`).
"""
from __future__ import annotations

import numpy as np

from app.geophysics.stats import method_metadata, safe_div

VALID_ARRAY_TYPES = ("wenner", "schlumberger")


def wenner_geometric_factor(spacing_m: float) -> float:
    """Fator geométrico K (metros) do arranjo Wenner: K = 2*pi*a."""
    if spacing_m <= 0:
        raise ValueError("spacing_m (a) deve ser positivo")
    return float(2.0 * np.pi * spacing_m)


def schlumberger_geometric_factor(current_spacing_m: float, potential_spacing_m: float) -> float:
    """Fator geométrico K (metros) do arranjo Schlumberger:
    K = pi*((L/2)^2 - (l/2)^2)/l, com L=`current_spacing_m` (AB) e
    l=`potential_spacing_m` (MN), l < L (a aproximação de dipolo de potencial
    pequeno frente ao espaçamento de corrente exige l << L, tipicamente l <= L/5)."""
    if current_spacing_m <= 0 or potential_spacing_m <= 0:
        raise ValueError("current_spacing_m (L) e potential_spacing_m (l) devem ser positivos")
    if potential_spacing_m >= current_spacing_m:
        raise ValueError("potential_spacing_m (l) deve ser menor que current_spacing_m (L)")
    L, l = current_spacing_m, potential_spacing_m
    return float(np.pi * ((L / 2.0) ** 2 - (l / 2.0) ** 2) / l)


def apparent_resistivity(
    array_type: str,
    voltage_v: float,
    current_a: float,
    spacing_m: float | None = None,
    current_spacing_m: float | None = None,
    potential_spacing_m: float | None = None,
) -> dict:
    """Resistividade aparente de UMA leitura, para o arranjo `array_type`
    ("wenner" usa `spacing_m`; "schlumberger" usa `current_spacing_m` e
    `potential_spacing_m`)."""
    array_type = array_type.lower()
    if array_type not in VALID_ARRAY_TYPES:
        raise ValueError(f"array_type deve ser um de {VALID_ARRAY_TYPES}")
    if current_a <= 0:
        raise ValueError("current_a (I) deve ser positivo")

    if array_type == "wenner":
        if spacing_m is None:
            raise ValueError("spacing_m (a) é obrigatório para o arranjo Wenner")
        k = wenner_geometric_factor(spacing_m)
        investigation_depth_m = spacing_m / 2.0  # regra heurística usual (a/2) — ver limitations
    else:
        if current_spacing_m is None or potential_spacing_m is None:
            raise ValueError("current_spacing_m (L) e potential_spacing_m (l) são obrigatórios para Schlumberger")
        k = schlumberger_geometric_factor(current_spacing_m, potential_spacing_m)
        investigation_depth_m = current_spacing_m / 4.0  # regra heurística usual (L/4) — ver limitations

    rho_a = k * safe_div(voltage_v, current_a)

    return {
        "array_type": array_type,
        "geometric_factor_m": k,
        "apparent_resistivity_ohm_m": float(rho_a),
        "estimated_investigation_depth_m": float(investigation_depth_m),
    }


def compute_sounding_curve(
    array_type: str,
    readings: list[dict],
) -> dict:
    """Calcula a curva de resistividade aparente vs. espaçamento (proxy de
    profundidade) para uma sequência de leituras de uma sondagem elétrica
    vertical (SEV), ordenando por espaçamento crescente.

    Args:
        array_type: "wenner" ou "schlumberger".
        readings: lista de leituras, cada uma um dict com `voltage_v`,
            `current_a`, e (Wenner) `spacing_m`, ou (Schlumberger)
            `current_spacing_m` + `potential_spacing_m`.
    """
    array_type = array_type.lower()
    if array_type not in VALID_ARRAY_TYPES:
        raise ValueError(f"array_type deve ser um de {VALID_ARRAY_TYPES}")
    if len(readings) < 2:
        raise ValueError("são necessárias ao menos 2 leituras para uma curva de sondagem")

    points = []
    for r in readings:
        result = apparent_resistivity(
            array_type=array_type,
            voltage_v=r["voltage_v"],
            current_a=r["current_a"],
            spacing_m=r.get("spacing_m"),
            current_spacing_m=r.get("current_spacing_m"),
            potential_spacing_m=r.get("potential_spacing_m"),
        )
        sort_key = r.get("spacing_m") if array_type == "wenner" else r.get("current_spacing_m")
        points.append({"sort_key": float(sort_key), **result})

    points.sort(key=lambda p: p["sort_key"])
    for p in points:
        p.pop("sort_key")

    depths = [p["estimated_investigation_depth_m"] for p in points]
    resistivities = [p["apparent_resistivity_ohm_m"] for p in points]

    return {
        "array_type": array_type,
        "n_readings": len(points),
        "sounding_curve": points,
        "min_apparent_resistivity_ohm_m": float(np.min(resistivities)),
        "max_apparent_resistivity_ohm_m": float(np.max(resistivities)),
        "max_investigation_depth_m": float(np.max(depths)),
        **method_metadata(
            method=(
                "resistividade aparente por arranjo eletrodico padrao: Wenner rho_a=2*pi*a*(V/I); "
                "Schlumberger rho_a=pi*((L/2)^2-(l/2)^2)/l*(V/I) (Telford et al. 1990, cap. 8); "
                "profundidade de investigacao estimada por regra heuristica (a/2 Wenner, L/4 Schlumberger)"
            ),
            parameters={"array_type": array_type, "n_readings": len(points)},
            uncertainty_note=(
                "A resistividade aparente calculada aqui é exata dado V, I e a geometria informados — "
                "a incerteza real vem da medição de campo (contato eletrodo-solo, ruído telúrico, erro "
                "de posicionamento dos eletrodos) e não é propagada por este módulo. Espaçamentos "
                "muito pequenos são mais sensíveis a heterogeneidades rasas locais (vegetação, "
                "compactação do solo perto do eletrodo)."
            ),
            limitations=(
                "Este módulo NÃO realiza inversão 1D de camadas (modelo de terra estratificada com "
                "espessura/resistividade por camada) — apenas a curva de resistividade aparente bruta "
                "vs. espaçamento. A profundidade de investigação é uma REGRA HEURÍSTICA de uso comum "
                "(a/2 para Wenner, L/4 para Schlumberger), não uma profundidade de sensibilidade "
                "formal calculada (que dependeria da função de sensibilidade de Fréchet do arranjo e "
                "do próprio modelo de resistividade do subsolo, desconhecido antes da inversão) — "
                "trate como uma referência aproximada de escala, não uma profundidade exata de "
                "interface geológica."
            ),
        ),
    }
