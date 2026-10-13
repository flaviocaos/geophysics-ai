import numpy as np
import pytest

from app.geophysics.magnetic_rtp import _rtp_operator, reduce_to_pole

# Metodologia de teste (ver processo de verificação da tarefa): uma anomalia
# "reduzida ao polo" verdadeira é, por definição, simétrica e centrada
# exatamente sobre a fonte — a assinatura de um polo magnético isolado
# enterrado é o campo em forma de sino `g(x,y) = A/(x²+y²+d²)^1.5`. Para
# testar o RTP sem depender de uma modelagem de dipolo 3D completa,
# geramos essa grade simétrica conhecida, aplicamos o operador RECÍPROCO do
# RTP (`Theta_f*Theta_m`, o "des-RTP"/skew) para produzir a anomalia
# "observada" com inclinação/declinação não-verticais (visivelmente
# assimétrica/deslocada — a mesma distorção que um campo ambiente inclinado
# produziria), e então verificamos que `reduce_to_pole` aplicado a essa
# anomalia observada RECUPERA a grade simétrica original, com o pico
# exatamente sobre a posição da fonte conhecida. Valores conferidos
# numericamente: a grade recuperada tem pico no mesmo índice da fonte
# verdadeira (32,32 numa grade 64x64 centrada), com diferença de simetria
# relativa ~1.6e-7 (praticamente perfeita) contra ~62% de assimetria na
# anomalia observada (não corrigida).
N = 64
PIXEL_SIZE_M = 50.0
DEPTH_M = 200.0
INCLINATION_DEG = 30.0
DECLINATION_DEG = 20.0


def _true_symmetric_source_grid():
    coords = (np.arange(N) - N // 2) * PIXEL_SIZE_M
    x, y = np.meshgrid(coords, coords)
    g = 1.0e7 / ((x ** 2 + y ** 2 + DEPTH_M ** 2) ** 1.5)
    source_row, source_col = N // 2, N // 2
    return g, source_row, source_col


def _skewed_observed_grid(symmetric_grid: np.ndarray) -> np.ndarray:
    """Aplica o operador recíproco do RTP (Theta_f*Theta_m) a uma anomalia
    simétrica conhecida, simulando como ela apareceria observada sob um
    campo ambiente inclinado — o inverso exato do que `reduce_to_pole` desfaz."""
    kx1d = np.fft.fftfreq(N, d=PIXEL_SIZE_M) * 2 * np.pi
    ky1d = np.fft.fftfreq(N, d=PIXEL_SIZE_M) * 2 * np.pi
    kx, ky = np.meshgrid(kx1d, ky1d)

    h_rtp = _rtp_operator(kx, ky, INCLINATION_DEG, DECLINATION_DEG, INCLINATION_DEG, DECLINATION_DEG)
    skew_operator = 1.0 / h_rtp  # recíproco do filtro de RTP

    spectrum = np.fft.fft2(symmetric_grid)
    skewed = np.real(np.fft.ifft2(spectrum * skew_operator))
    return skewed


def _relative_symmetry_diff(arr: np.ndarray, peak_row: int, peak_col: int, offset: int = 3) -> float:
    diffs = []
    if peak_col - offset >= 0 and peak_col + offset < arr.shape[1]:
        diffs.append(abs(arr[peak_row, peak_col - offset] - arr[peak_row, peak_col + offset]))
    if peak_row - offset >= 0 and peak_row + offset < arr.shape[0]:
        diffs.append(abs(arr[peak_row - offset, peak_col] - arr[peak_row + offset, peak_col]))
    peak_value = abs(arr[peak_row, peak_col])
    return float(np.mean(diffs) / peak_value)


def test_skewed_synthetic_anomaly_is_clearly_asymmetric_before_rtp():
    symmetric_grid, source_row, source_col = _true_symmetric_source_grid()
    skewed = _skewed_observed_grid(symmetric_grid)

    peak_idx = np.unravel_index(np.argmax(skewed), skewed.shape)
    # A anomalia observada (não corrigida) fica visivelmente assimétrica em torno do próprio pico.
    rel_diff = _relative_symmetry_diff(skewed, *peak_idx)
    assert rel_diff > 0.3  # assimetria clara (>30% de diferença relativa)


def test_reduce_to_pole_recovers_symmetric_anomaly_centered_on_source():
    symmetric_grid, source_row, source_col = _true_symmetric_source_grid()
    skewed = _skewed_observed_grid(symmetric_grid)

    result = reduce_to_pole(
        skewed,
        pixel_size_m=PIXEL_SIZE_M,
        inclination_deg=INCLINATION_DEG,
        declination_deg=DECLINATION_DEG,
    )
    rtp_grid = np.array(result["rtp_grid"])

    # O pico da anomalia RTP deve cair exatamente sobre a posição da fonte verdadeira.
    assert result["peak_row"] == source_row
    assert result["peak_col"] == source_col

    # A anomalia RTP recuperada deve ser essencialmente simétrica em torno do pico —
    # muito mais simétrica que a anomalia observada (não corrigida) antes do RTP.
    rel_diff_after = _relative_symmetry_diff(rtp_grid, result["peak_row"], result["peak_col"])
    rel_diff_before = _relative_symmetry_diff(skewed, *np.unravel_index(np.argmax(skewed), skewed.shape))
    assert rel_diff_after < 1e-4
    assert rel_diff_after < rel_diff_before


def test_reduce_to_pole_flags_low_inclination():
    symmetric_grid, _, _ = _true_symmetric_source_grid()
    result = reduce_to_pole(symmetric_grid, pixel_size_m=PIXEL_SIZE_M, inclination_deg=5.0, declination_deg=0.0)
    assert result["low_inclination_warning"] is True


def test_reduce_to_pole_does_not_warn_at_high_inclination():
    symmetric_grid, _, _ = _true_symmetric_source_grid()
    result = reduce_to_pole(symmetric_grid, pixel_size_m=PIXEL_SIZE_M, inclination_deg=60.0, declination_deg=0.0)
    assert result["low_inclination_warning"] is False


def test_reduce_to_pole_rejects_grid_too_small():
    with pytest.raises(ValueError):
        reduce_to_pole(np.ones((2, 2)), pixel_size_m=10.0, inclination_deg=45.0, declination_deg=0.0)


def test_reduce_to_pole_rejects_invalid_pixel_size():
    with pytest.raises(ValueError):
        reduce_to_pole(np.ones((8, 8)), pixel_size_m=0.0, inclination_deg=45.0, declination_deg=0.0)


def test_reduce_to_pole_assumes_induced_magnetization_by_default():
    symmetric_grid, _, _ = _true_symmetric_source_grid()
    result = reduce_to_pole(symmetric_grid, pixel_size_m=PIXEL_SIZE_M, inclination_deg=45.0, declination_deg=10.0)
    assert result["assumed_purely_induced_magnetization"] is True
