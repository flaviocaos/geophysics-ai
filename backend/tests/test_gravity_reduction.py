import pytest

from app.geophysics.gravity_reduction import (
    calculate_bouguer_anomaly,
    free_air_correction,
    normal_gravity_igf80,
    simple_bouguer_correction,
)

# Valores conferidos por cálculo numérico direto (ver processo de verificação
# da tarefa): latitude=-15.78°, elevação=1000m, densidade=2670 kg/m³,
# g_observado=978331.0 mGal ->
#   g_teorico (IGF80)  = 978414.6642372936 mGal
#   FAC                = 308.6 mGal
#   BC                 = 111.9531 mGal
#   anomalia Bouguer   = 112.98266270635236 mGal
LAT_DEG = -15.78
ELEVATION_M = 1000.0
DENSITY_KG_M3 = 2670.0
OBSERVED_GRAVITY_MGAL = 978331.0

EXPECTED_G_THETA = 978414.6642372936
EXPECTED_FAC = 308.6
EXPECTED_BC = 111.9531
EXPECTED_BOUGUER_ANOMALY = 112.98266270635236


def test_normal_gravity_igf80_matches_hand_computed_value():
    g_theta = normal_gravity_igf80(LAT_DEG)
    assert g_theta == pytest.approx(EXPECTED_G_THETA, abs=1e-6)


def test_normal_gravity_at_equator_is_minimum_reference_value():
    # No equador (lat=0), sin²(lat)=0 e sin²(2*lat)=0 -> g_theta = 978032.7 mGal exatamente.
    assert normal_gravity_igf80(0.0) == pytest.approx(978032.7, abs=1e-9)


def test_normal_gravity_increases_towards_the_poles():
    # A gravidade teórica cresce do equador para os polos (achatamento da Terra).
    assert normal_gravity_igf80(0.0) < normal_gravity_igf80(45.0) < normal_gravity_igf80(90.0)


def test_free_air_correction_matches_hand_computed_value():
    assert free_air_correction(ELEVATION_M) == pytest.approx(EXPECTED_FAC, abs=1e-9)


def test_free_air_correction_is_zero_at_datum():
    assert free_air_correction(0.0) == pytest.approx(0.0, abs=1e-12)


def test_simple_bouguer_correction_matches_hand_computed_value():
    bc = simple_bouguer_correction(ELEVATION_M, DENSITY_KG_M3)
    assert bc == pytest.approx(EXPECTED_BC, abs=1e-6)


def test_simple_bouguer_correction_rejects_nonpositive_density():
    with pytest.raises(ValueError):
        simple_bouguer_correction(ELEVATION_M, density_kg_m3=0.0)


def test_calculate_bouguer_anomaly_matches_hand_computed_value():
    result = calculate_bouguer_anomaly(
        observed_gravity_mgal=OBSERVED_GRAVITY_MGAL,
        latitude_deg=LAT_DEG,
        elevation_m=ELEVATION_M,
        density_kg_m3=DENSITY_KG_M3,
    )
    assert result["normal_gravity_mgal"] == pytest.approx(EXPECTED_G_THETA, abs=1e-6)
    assert result["free_air_correction_mgal"] == pytest.approx(EXPECTED_FAC, abs=1e-9)
    assert result["bouguer_correction_mgal"] == pytest.approx(EXPECTED_BC, abs=1e-6)
    assert result["bouguer_anomaly_mgal"] == pytest.approx(EXPECTED_BOUGUER_ANOMALY, abs=1e-6)
    assert "method" in result and "limitations" in result
    assert "terreno" in result["limitations"].lower() or "terrain" in result["limitations"].lower()


def test_calculate_bouguer_anomaly_uses_default_density_when_omitted():
    result = calculate_bouguer_anomaly(
        observed_gravity_mgal=OBSERVED_GRAVITY_MGAL, latitude_deg=LAT_DEG, elevation_m=ELEVATION_M
    )
    assert result["density_kg_m3"] == pytest.approx(2670.0)


def test_calculate_bouguer_anomaly_rejects_implausible_elevation():
    with pytest.raises(ValueError):
        calculate_bouguer_anomaly(observed_gravity_mgal=OBSERVED_GRAVITY_MGAL, latitude_deg=LAT_DEG, elevation_m=-10000.0)


def test_normal_gravity_rejects_invalid_latitude():
    with pytest.raises(ValueError):
        normal_gravity_igf80(120.0)
