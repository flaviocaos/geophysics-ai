import numpy as np
import pytest

from app.geophysics.anomaly_detection import detect_anomalous_patches

# Grade sintética 40x40: ruído de fundo gaussiano (sigma=0.7, seed fixo) mais
# duas anomalias gaussianas conhecidas — uma positiva forte centrada em
# (linha=10, coluna=10), uma negativa forte centrada em (linha=30, coluna=28).
# Valores conferidos numericamente (ver processo de verificação da tarefa):
# com threshold_sigma=2.0 e seed=1, a rotulagem de componentes conexos
# produz exatamente 2 manchas, com centroides muito próximos aos centros
# verdadeiros das gaussianas (dentro de ~1 célula) e sinais (mean_value)
# corretos (positivo/negativo).
N = 40
NOISE_SIGMA = 0.7
SEED = 1
BUMP1_CENTER = (10, 10)  # (linha, coluna)
BUMP1_AMPLITUDE = 15.0
BUMP2_CENTER = (30, 28)
BUMP2_AMPLITUDE = -12.0


def _synthetic_grid():
    rng = np.random.default_rng(SEED)
    background = rng.normal(0, NOISE_SIGMA, (N, N))
    rows, cols = np.mgrid[0:N, 0:N]
    bump1 = BUMP1_AMPLITUDE * np.exp(-(((cols - BUMP1_CENTER[1]) ** 2 + (rows - BUMP1_CENTER[0]) ** 2)) / (2 * 3.0 ** 2))
    bump2 = BUMP2_AMPLITUDE * np.exp(-(((cols - BUMP2_CENTER[1]) ** 2 + (rows - BUMP2_CENTER[0]) ** 2)) / (2 * 2.5 ** 2))
    return background + bump1 + bump2


def test_detects_exactly_two_patches_at_known_locations():
    grid = _synthetic_grid()
    result = detect_anomalous_patches(grid, threshold_sigma=2.0, direction="both", pixel_size_m=10.0)

    assert result["n_patches"] == 2
    # Ordenado por |peak_value| decrescente — a anomalia positiva (amplitude 15) vem primeiro.
    positive_patch, negative_patch = result["patches"]

    assert positive_patch["mean_value"] > 0
    assert positive_patch["centroid_row"] == pytest.approx(BUMP1_CENTER[0], abs=1.0)
    assert positive_patch["centroid_col"] == pytest.approx(BUMP1_CENTER[1], abs=1.0)

    assert negative_patch["mean_value"] < 0
    assert negative_patch["centroid_row"] == pytest.approx(BUMP2_CENTER[0], abs=1.0)
    assert negative_patch["centroid_col"] == pytest.approx(BUMP2_CENTER[1], abs=1.0)

    # Área reportada em m² deve ser coerente com n_cells * pixel_size_m².
    assert positive_patch["area_m2"] == pytest.approx(positive_patch["n_cells"] * 100.0)


def test_direction_high_only_detects_the_positive_patch():
    grid = _synthetic_grid()
    result = detect_anomalous_patches(grid, threshold_sigma=2.0, direction="high", pixel_size_m=10.0)
    assert result["n_patches"] == 1
    assert result["patches"][0]["mean_value"] > 0


def test_direction_low_only_detects_the_negative_patch():
    grid = _synthetic_grid()
    result = detect_anomalous_patches(grid, threshold_sigma=2.0, direction="low", pixel_size_m=10.0)
    assert result["n_patches"] == 1
    assert result["patches"][0]["mean_value"] < 0


def test_higher_threshold_detects_fewer_or_equal_cells():
    grid = _synthetic_grid()
    low_threshold = detect_anomalous_patches(grid, threshold_sigma=1.5, direction="both", pixel_size_m=10.0)
    high_threshold = detect_anomalous_patches(grid, threshold_sigma=3.0, direction="both", pixel_size_m=10.0)
    total_cells_low = sum(p["n_cells"] for p in low_threshold["patches"])
    total_cells_high = sum(p["n_cells"] for p in high_threshold["patches"])
    assert total_cells_high <= total_cells_low


def test_rejects_invalid_direction():
    with pytest.raises(ValueError):
        detect_anomalous_patches(_synthetic_grid(), direction="sideways")


def test_rejects_constant_grid():
    with pytest.raises(ValueError):
        detect_anomalous_patches(np.ones((10, 10)))


def test_rejects_nonpositive_threshold():
    with pytest.raises(ValueError):
        detect_anomalous_patches(_synthetic_grid(), threshold_sigma=0.0)
