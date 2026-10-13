import pytest

from app.geophysics.resistivity_sounding import (
    apparent_resistivity,
    compute_sounding_curve,
    schlumberger_geometric_factor,
    wenner_geometric_factor,
)

# Valores conferidos por cálculo direto (ver processo de verificação da
# tarefa): a=10m, V=0.05V, I=0.02A ->
#   Wenner:       K=2*pi*10=62.83185307..., rho_a=157.07963267948966 ohm.m
#   Schlumberger: L=40m, l=2m -> K=pi*((20)^2-(1)^2)/2=626.7477343911637,
#                 rho_a=1566.8693359779093 ohm.m (mesmo V/I)
SPACING_M = 10.0
VOLTAGE_V = 0.05
CURRENT_A = 0.02
EXPECTED_WENNER_RHO = 157.07963267948966

CURRENT_SPACING_M = 40.0
POTENTIAL_SPACING_M = 2.0
EXPECTED_SCHLUMBERGER_RHO = 1566.8693359779093


def test_wenner_geometric_factor_matches_hand_computed_value():
    k = wenner_geometric_factor(SPACING_M)
    assert k == pytest.approx(62.83185307179586, abs=1e-9)


def test_schlumberger_geometric_factor_matches_hand_computed_value():
    k = schlumberger_geometric_factor(CURRENT_SPACING_M, POTENTIAL_SPACING_M)
    assert k == pytest.approx(626.7477343911637, abs=1e-6)


def test_schlumberger_geometric_factor_rejects_potential_ge_current_spacing():
    with pytest.raises(ValueError):
        schlumberger_geometric_factor(current_spacing_m=10.0, potential_spacing_m=10.0)


def test_apparent_resistivity_wenner_matches_hand_computed_value():
    result = apparent_resistivity("wenner", voltage_v=VOLTAGE_V, current_a=CURRENT_A, spacing_m=SPACING_M)
    assert result["apparent_resistivity_ohm_m"] == pytest.approx(EXPECTED_WENNER_RHO, abs=1e-6)
    assert result["estimated_investigation_depth_m"] == pytest.approx(SPACING_M / 2.0)


def test_apparent_resistivity_schlumberger_matches_hand_computed_value():
    result = apparent_resistivity(
        "schlumberger",
        voltage_v=VOLTAGE_V,
        current_a=CURRENT_A,
        current_spacing_m=CURRENT_SPACING_M,
        potential_spacing_m=POTENTIAL_SPACING_M,
    )
    assert result["apparent_resistivity_ohm_m"] == pytest.approx(EXPECTED_SCHLUMBERGER_RHO, abs=1e-6)
    assert result["estimated_investigation_depth_m"] == pytest.approx(CURRENT_SPACING_M / 4.0)


def test_apparent_resistivity_rejects_unknown_array_type():
    with pytest.raises(ValueError):
        apparent_resistivity("dipole-dipole", voltage_v=1.0, current_a=1.0, spacing_m=10.0)


def test_apparent_resistivity_wenner_requires_spacing():
    with pytest.raises(ValueError):
        apparent_resistivity("wenner", voltage_v=1.0, current_a=1.0)


def test_compute_sounding_curve_sorts_by_spacing_and_reports_range():
    # Resistividade verdadeira crescente com a profundidade — três leituras Wenner
    # fora de ordem de entrada; a curva deve ser ordenada por espaçamento crescente.
    readings = [
        {"spacing_m": 20.0, "voltage_v": 0.02, "current_a": 0.01},  # rho = 2*pi*20*2 = 251.33
        {"spacing_m": 5.0, "voltage_v": 0.05, "current_a": 0.01},   # rho = 2*pi*5*5 = 157.08
        {"spacing_m": 40.0, "voltage_v": 0.01, "current_a": 0.01},  # rho = 2*pi*40*1 = 251.33
    ]
    result = compute_sounding_curve("wenner", readings)
    assert result["n_readings"] == 3
    spacings = [p["estimated_investigation_depth_m"] * 2 for p in result["sounding_curve"]]
    assert spacings == sorted(spacings)
    assert result["sounding_curve"][0]["estimated_investigation_depth_m"] == pytest.approx(2.5)
    assert result["max_investigation_depth_m"] == pytest.approx(20.0)


def test_compute_sounding_curve_requires_at_least_two_readings():
    with pytest.raises(ValueError):
        compute_sounding_curve("wenner", [{"spacing_m": 10.0, "voltage_v": 1.0, "current_a": 1.0}])
