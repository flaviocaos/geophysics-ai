"""Interpretação de refração sísmica de duas camadas pelo método da
distância de cruzamento (crossover distance) — o método clássico de
interpretação manual/analítica de um levantamento de refração de cobertura
simples (um tiro, um alinhamento de geofones):

Para um par de camadas horizontais (V1 na camada superior, V2 > V1 na
camada inferior, a condição física necessária para haver refração crítica),
a curva tempo-distância (dromocrônica) tem dois ramos lineares:

    onda direta (offsets pequenos):    t(x) = x/V1
    onda refratada crítica (offsets    t(x) = x/V2 + t_i,
      grandes, após a distância de       t_i = 2*h*cos(theta_c)/V1
      cruzamento x_cross):                theta_c = arcsin(V1/V2)  (ângulo crítico)

`V1` e `V2` são recuperados como o inverso da inclinação (slope) de cada
ramo, ajustado por mínimos quadrados a partir dos pares (offset, tempo de
chegada) observados. A distância de cruzamento `x_cross` é o offset onde as
duas retas ajustadas se cruzam (`t_direto(x_cross) = t_refratado(x_cross)`).
A profundidade da interface é então:

    depth = (x_cross/2) * sqrt((V2-V1)/(V2+V1))

Referência: Kearey, P., Brooks, M., Hill, I. (2002), "An Introduction to
Geophysical Exploration", 3ª ed., cap. 5 — a formulação padrão de refração
sísmica de duas camadas horizontais ensinada em qualquer curso introdutório
de geofísica aplicada.
"""
from __future__ import annotations

import numpy as np

from app.geophysics.stats import fit_line_least_squares, method_metadata

_MIN_POINTS_PER_BRANCH = 2


def _classify_branches(offsets_m: np.ndarray, crossover_hint_m: float | None) -> np.ndarray:
    """Separa os pontos em ramo direto (offset menor) e refratado (offset
    maior) usando um palpite de distância de cruzamento, se informado —
    senão usa a mediana dos offsets como separador inicial (heurística
    grosseira, adequada apenas quando os dois ramos já estão claramente
    identificados nos dados de entrada por `is_direct_wave`)."""
    threshold = crossover_hint_m if crossover_hint_m is not None else float(np.median(offsets_m))
    return offsets_m <= threshold


def interpret_two_layer_refraction(
    offsets_m: list[float],
    travel_times_ms: list[float],
    is_direct_wave: list[bool] | None = None,
) -> dict:
    """Interpreta um levantamento de refração sísmica de duas camadas
    horizontais pelo método da distância de cruzamento.

    Args:
        offsets_m: distância fonte-receptor de cada primeira chegada (metros).
        travel_times_ms: tempo de primeira chegada correspondente (milissegundos).
        is_direct_wave: opcional — para cada leitura, `True` se pertence ao
            ramo da onda direta e `False` se pertence ao ramo da onda
            refratada crítica (a classificação correta normalmente vem da
            inspeção visual do sismograma pelo intérprete de campo — a
            quebra de inclinação na dromocrônica). Quando omitido, o offset
            mediano é usado como separador aproximado entre os dois ramos —
            adequado apenas para dados sintéticos/já ordenados por ramo;
            dados de campo reais devem sempre informar a classificação
            explícita.
    """
    offsets = np.asarray(offsets_m, dtype=np.float64)
    times_ms = np.asarray(travel_times_ms, dtype=np.float64)
    if offsets.shape != times_ms.shape:
        raise ValueError("offsets_m e travel_times_ms devem ter o mesmo tamanho")
    if len(offsets) < 2 * _MIN_POINTS_PER_BRANCH:
        raise ValueError(
            f"são necessários ao menos {_MIN_POINTS_PER_BRANCH} pontos em cada ramo "
            f"(mínimo {2 * _MIN_POINTS_PER_BRANCH} leituras no total)"
        )
    if np.any(offsets < 0):
        raise ValueError("offsets_m não pode ser negativo")
    if np.any(times_ms <= 0):
        raise ValueError("travel_times_ms deve ser estritamente positivo")

    times_s = times_ms / 1000.0

    if is_direct_wave is not None:
        direct_mask = np.asarray(is_direct_wave, dtype=bool)
        if direct_mask.shape != offsets.shape:
            raise ValueError("is_direct_wave, quando informado, deve ter o mesmo tamanho de offsets_m")
    else:
        direct_mask = _classify_branches(offsets, None)

    refracted_mask = ~direct_mask
    if direct_mask.sum() < _MIN_POINTS_PER_BRANCH or refracted_mask.sum() < _MIN_POINTS_PER_BRANCH:
        raise ValueError(
            f"cada ramo (direto/refratado) precisa de ao menos {_MIN_POINTS_PER_BRANCH} pontos "
            "após a classificação — verifique is_direct_wave ou a distribuição dos offsets"
        )

    direct_fit = fit_line_least_squares(offsets[direct_mask], times_s[direct_mask])
    refracted_fit = fit_line_least_squares(offsets[refracted_mask], times_s[refracted_mask])

    slope_direct = direct_fit["slope"]
    slope_refracted = refracted_fit["slope"]
    if slope_direct <= 0 or slope_refracted <= 0:
        raise ValueError("inclinação de um dos ramos não é positiva — dados incompatíveis com um modelo de 2 camadas com V2>V1")

    v1 = 1.0 / slope_direct
    v2 = 1.0 / slope_refracted
    if v2 <= v1:
        raise ValueError(
            f"V2 ({v2:.1f} m/s) deve ser maior que V1 ({v1:.1f} m/s) para haver refração crítica — "
            "verifique a classificação dos ramos (is_direct_wave) ou a qualidade dos dados"
        )

    intercept_direct = direct_fit["intercept"]
    intercept_time_s = refracted_fit["intercept"]

    # distância de cruzamento: intersecção das duas retas ajustadas
    # t_direto(x) = x/v1 + intercept_direct ; t_refratado(x) = x/v2 + intercept_time_s
    denom = (1.0 / v1) - (1.0 / v2)
    x_crossover_m = (intercept_time_s - intercept_direct) / denom

    critical_angle_rad = np.arcsin(v1 / v2)
    depth_m = (x_crossover_m / 2.0) * np.sqrt((v2 - v1) / (v2 + v1))

    # profundidade alternativa via tempo de intercepto (t_i), consistência cruzada
    depth_from_intercept_m = intercept_time_s * v1 * v2 / (2.0 * np.sqrt(v2 ** 2 - v1 ** 2))

    return {
        "v1_m_s": float(v1),
        "v2_m_s": float(v2),
        "critical_angle_deg": float(np.degrees(critical_angle_rad)),
        "crossover_distance_m": float(x_crossover_m),
        "intercept_time_s": float(intercept_time_s),
        "depth_m": float(depth_m),
        "depth_from_intercept_time_m": float(depth_from_intercept_m),
        "n_direct_points": int(direct_mask.sum()),
        "n_refracted_points": int(refracted_mask.sum()),
        "direct_branch_residual_rms_s": direct_fit["residual_rms"],
        "refracted_branch_residual_rms_s": refracted_fit["residual_rms"],
        **method_metadata(
            method=(
                "refracao sismica de 2 camadas horizontais, metodo da distancia de cruzamento "
                "(crossover distance): V1=1/slope(onda direta), V2=1/slope(onda refratada critica) "
                "por minimos quadrados; depth=(x_crossover/2)*sqrt((V2-V1)/(V2+V1)) "
                "(Kearey, Brooks & Hill, 2002, cap. 5)"
            ),
            parameters={
                "n_readings": int(len(offsets)),
                "n_direct_points": int(direct_mask.sum()),
                "n_refracted_points": int(refracted_mask.sum()),
                "branch_classification": "informada (is_direct_wave)" if is_direct_wave is not None else "heuristica (mediana dos offsets)",
            },
            uncertainty_note=(
                "V1, V2 e a profundidade dependem inteiramente da qualidade da leitura manual/"
                "automática dos tempos de primeira chegada e da correta separação dos dois ramos da "
                "dromocrônica — `residual_rms_s` de cada ramo é o indicador principal de qualidade do "
                "ajuste: um RMS alto sugere leituras ruidosas, um ramo mal classificado, ou uma "
                "subsuperfície que não é bem aproximada por 2 camadas horizontais planas. As duas "
                "estimativas de profundidade (`depth_m` via distância de cruzamento e "
                "`depth_from_intercept_time_m` via tempo de intercepto) devem ser próximas entre si "
                "quando o modelo de 2 camadas é adequado; uma divergência grande entre elas é um "
                "indício de mergulho da interface ou de mais de 2 camadas reais."
            ),
            limitations=(
                "Assume exatamente 2 camadas horizontais planas e paralelas (sem mergulho/dip da "
                "interface, que exigiria tiros recíprocos/direto+reverso para ser detectado e "
                "corrigido) e velocidade constante dentro de cada camada (sem gradiente de "
                "velocidade). Não detecta uma terceira camada oculta (camada de baixa velocidade "
                "'escondida', um problema clássico de não-unicidade em refração sísmica) nem aplica "
                "o método de tempo-intercepto generalizado (generalized reciprocal method, GRM) usado "
                "em levantamentos multi-camada/mergulhantes — fora do escopo deste módulo. A "
                "classificação de qual leitura pertence a qual ramo, quando não informada "
                "explicitamente (`is_direct_wave`), usa uma heurística grosseira (mediana dos "
                "offsets) que só é confiável em dados já ordenados/sintéticos."
            ),
        ),
    }
