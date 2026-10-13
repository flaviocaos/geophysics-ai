import numpy as np
import pytest

from app.geophysics.seismic_refraction import interpret_two_layer_refraction

# Dados sintéticos gerados A PARTIR de V1, V2 e profundidade VERDADEIROS
# conhecidos, usando as equações padrão de refração de 2 camadas (Kearey,
# Brooks & Hill, 2002): onda direta t=x/V1; onda refratada crítica
# t=x/V2 + 2*depth*cos(theta_c)/V1, theta_c=asin(V1/V2). Valores conferidos
# numericamente (ver processo de verificação da tarefa):
#   theta_c ~= 14.4775 graus, x_cross ~= 51.6398 m, t_i ~= 77.4597 ms
#   -> a interpretação deve recuperar V1=500, V2=2000, depth=20 dentro de tolerância pequena.
TRUE_V1 = 500.0
TRUE_V2 = 2000.0
TRUE_DEPTH = 20.0


def _synthetic_refraction_data():
    theta_c = np.arcsin(TRUE_V1 / TRUE_V2)
    x_cross = 2 * TRUE_DEPTH * np.sqrt((TRUE_V2 + TRUE_V1) / (TRUE_V2 - TRUE_V1))

    offsets_direct = np.linspace(1.0, x_cross * 0.9, 6)
    times_direct = offsets_direct / TRUE_V1

    offsets_refracted = np.linspace(x_cross * 1.1, x_cross * 3.0, 8)
    times_refracted = offsets_refracted / TRUE_V2 + 2 * TRUE_DEPTH * np.cos(theta_c) / TRUE_V1

    offsets = np.concatenate([offsets_direct, offsets_refracted])
    times_ms = np.concatenate([times_direct, times_refracted]) * 1000.0
    is_direct = [True] * len(offsets_direct) + [False] * len(offsets_refracted)
    return offsets.tolist(), times_ms.tolist(), is_direct, x_cross


def test_interpretation_recovers_true_v1_v2_and_depth():
    offsets, times_ms, is_direct, x_cross_true = _synthetic_refraction_data()
    result = interpret_two_layer_refraction(offsets, times_ms, is_direct_wave=is_direct)

    assert result["v1_m_s"] == pytest.approx(TRUE_V1, rel=1e-6)
    assert result["v2_m_s"] == pytest.approx(TRUE_V2, rel=1e-6)
    assert result["crossover_distance_m"] == pytest.approx(x_cross_true, rel=1e-6)
    assert result["depth_m"] == pytest.approx(TRUE_DEPTH, rel=1e-4)
    # As duas estimativas independentes de profundidade devem concordar entre si.
    assert result["depth_from_intercept_time_m"] == pytest.approx(TRUE_DEPTH, rel=1e-4)
    assert result["critical_angle_deg"] == pytest.approx(14.477512185929925, abs=1e-4)


def test_interpretation_with_noise_stays_within_reasonable_tolerance():
    offsets, times_ms, is_direct, _ = _synthetic_refraction_data()
    rng = np.random.default_rng(7)
    noisy_times_ms = (np.asarray(times_ms) + rng.normal(0, 0.3, len(times_ms))).tolist()  # ruído de 0.3ms

    result = interpret_two_layer_refraction(offsets, noisy_times_ms, is_direct_wave=is_direct)
    assert result["v1_m_s"] == pytest.approx(TRUE_V1, rel=0.05)
    assert result["v2_m_s"] == pytest.approx(TRUE_V2, rel=0.05)
    assert result["depth_m"] == pytest.approx(TRUE_DEPTH, rel=0.15)


def test_v2_must_exceed_v1_or_raises():
    # Ramos invertidos deliberadamente (V2 aparente < V1 aparente) -> erro explícito.
    offsets = [1.0, 5.0, 10.0, 15.0, 20.0, 25.0]
    times_ms = [t for t in np.array(offsets) / 500.0 * 1000.0]  # tudo na mesma reta rápida
    is_direct = [True, True, True, False, False, False]
    with pytest.raises(ValueError):
        interpret_two_layer_refraction(offsets, times_ms, is_direct_wave=is_direct)


def test_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        interpret_two_layer_refraction([1.0, 2.0, 3.0], [1.0, 2.0], is_direct_wave=[True, True, False])


def test_rejects_too_few_points():
    with pytest.raises(ValueError):
        interpret_two_layer_refraction([1.0, 2.0, 3.0], [2.0, 4.0, 6.0], is_direct_wave=[True, True, False])
