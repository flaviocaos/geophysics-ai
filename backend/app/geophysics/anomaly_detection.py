"""Delimitação de corpos-fonte anômalos candidatos numa grade de anomalia
residual (gravimétrica ou magnética, tipicamente já reduzida — anomalia
Bouguer ou anomalia reduzida ao polo) por limiar de z-score seguido de
extração de componentes conexos — o mesmo padrão de detecção de anomalia já
usado na plataforma (ex.: `radar-ai` para detecção de mudança em imagens SAR,
`geology-ai/app/geology/anomaly_detection.py` para anomalias espectrais em
rasters de exploração mineral), aqui aplicado a grades de campo potencial
geofísico já reduzidas.

Método:
    1. z-score = (grid - média(grid)) / desvio_padrão(grid)
    2. máscara = |z-score| >= threshold_sigma (ou apenas um lado, se
       `direction` for "high" ou "low")
    3. `scipy.ndimage.label` extrai componentes conexos (4-conectividade) da
       máscara — cada componente é um corpo-fonte candidato
    4. para cada componente: contagem de células, área (célula * pixel²),
       centroide (linha, coluna), valor médio e valor de pico da anomalia
       original dentro do componente

Isto é uma ferramenta de TRIAGEM estatística, não uma classificação
geológica: aponta ONDE a anomalia se desvia significativamente do fundo
regional da própria grade, não O QUE causa a anomalia (que exigiria
modelagem/inversão direta de corpos-fonte, ou a integração com dados
independentes — sondagens, mapeamento geológico de superfície).
"""
from __future__ import annotations

import numpy as np

from app.geophysics.stats import method_metadata

VALID_DIRECTIONS = ("both", "high", "low")


def detect_anomalous_patches(
    grid: list[list[float]] | np.ndarray,
    threshold_sigma: float = 2.0,
    direction: str = "both",
    pixel_size_m: float = 1.0,
) -> dict:
    """Detecta manchas (patches) anômalas numa grade residual por limiar de
    z-score + rotulagem de componentes conexos.

    Args:
        grid: grade 2D de valores de anomalia (gravimétrica ou magnética já
            reduzida). Valores `NaN` são ignorados no cálculo de média/desvio
            e nunca entram numa mancha detectada.
        threshold_sigma: limiar em desvios-padrão (z-score) — padrão 2.0
            (aproximadamente os 5% mais extremos de uma distribuição normal,
            um limiar comumente usado em triagem de anomalias geofísicas).
        direction: "both" (|z| >= limiar), "high" (z >= limiar, só anomalias
            positivas) ou "low" (z <= -limiar, só anomalias negativas).
        pixel_size_m: tamanho do pixel da grade (metros), usado para
            converter contagem de células em área (m²).
    """
    from scipy import ndimage  # import local — mantém o módulo leve para quem só usa as outras funções

    if direction not in VALID_DIRECTIONS:
        raise ValueError(f"direction deve ser um de {VALID_DIRECTIONS}")
    if threshold_sigma <= 0:
        raise ValueError("threshold_sigma deve ser positivo")
    if pixel_size_m <= 0:
        raise ValueError("pixel_size_m deve ser positivo")

    arr = np.asarray(grid, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError("grid deve ser um array 2D")

    valid = np.isfinite(arr)
    if valid.sum() < 4:
        raise ValueError("grid não tem células válidas (não-NaN) suficientes para calcular estatística de fundo")

    mean = float(np.mean(arr[valid]))
    std = float(np.std(arr[valid]))
    if std == 0:
        raise ValueError("desvio-padrão da grade é zero (grade constante) — z-score indefinido")

    z = np.zeros_like(arr)
    z[valid] = (arr[valid] - mean) / std
    z[~valid] = 0.0

    if direction == "both":
        mask = (np.abs(z) >= threshold_sigma) & valid
    elif direction == "high":
        mask = (z >= threshold_sigma) & valid
    else:
        mask = (z <= -threshold_sigma) & valid

    labeled, n_patches = ndimage.label(mask)
    pixel_area_m2 = pixel_size_m ** 2

    patches = []
    for patch_id in range(1, n_patches + 1):
        patch_mask = labeled == patch_id
        n_cells = int(patch_mask.sum())
        rows, cols = np.nonzero(patch_mask)
        values = arr[patch_mask]
        peak_idx = int(np.argmax(np.abs(values)))

        patches.append(
            {
                "patch_id": patch_id,
                "n_cells": n_cells,
                "area_m2": float(n_cells * pixel_area_m2),
                "centroid_row": float(np.mean(rows)),
                "centroid_col": float(np.mean(cols)),
                "mean_value": float(np.mean(values)),
                "peak_value": float(values[peak_idx]),
                "peak_row": int(rows[peak_idx]),
                "peak_col": int(cols[peak_idx]),
                "mean_z_score": float(np.mean(z[patch_mask])),
            }
        )

    patches.sort(key=lambda p: abs(p["peak_value"]), reverse=True)

    return {
        "n_patches": n_patches,
        "patches": patches,
        "background_mean": mean,
        "background_std": std,
        "threshold_sigma": float(threshold_sigma),
        "direction": direction,
        **method_metadata(
            method=(
                "z-score = (grid-media)/desvio_padrao; mascara = limiar de z-score (direcao "
                "configuravel); scipy.ndimage.label extrai componentes conexos (4-conectividade) "
                "como corpos-fonte candidatos; centroide/area/valor medio/pico por componente"
            ),
            parameters={
                "threshold_sigma": threshold_sigma,
                "direction": direction,
                "pixel_size_m": pixel_size_m,
                "n_valid_cells": int(valid.sum()),
            },
            uncertainty_note=(
                "A estatística de fundo (média/desvio-padrão) é calculada sobre TODA a grade "
                "informada — se a área de estudo contém uma anomalia regional grande (tendência "
                "geológica de longo comprimento de onda) em vez de ruído aproximadamente estacionário, "
                "o z-score resultante mistura sinal local com a tendência regional; para melhores "
                "resultados, aplique este módulo a uma grade JÁ residual (após remoção de tendência "
                "regional), não à anomalia bruta. O número de manchas e sua extensão são sensíveis à "
                "escolha de `threshold_sigma` — não existe um único limiar 'correto' universal."
            ),
            limitations=(
                "Esta é uma ferramenta de TRIAGEM estatística (onde a grade se desvia do próprio "
                "fundo), não uma classificação geológica do corpo-fonte — não estima profundidade, "
                "forma ou natureza litológica da fonte (isso exigiria modelagem/inversão direta de "
                "corpos, fora do escopo deste módulo). Manchas muito pequenas (poucas células) podem "
                "ser ruído de aquisição em vez de um corpo real — nenhum filtro de área mínima é "
                "aplicado automaticamente; o chamador deve avaliar `n_cells`/`area_m2` de cada mancha "
                "antes de tratá-la como um alvo de interesse."
            ),
        ),
    }
