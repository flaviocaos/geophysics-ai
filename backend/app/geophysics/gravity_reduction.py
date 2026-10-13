"""Redução Bouguer de gravimetria — a cadeia clássica de correções que separa
o efeito geológico de interesse (a anomalia Bouguer) do efeito previsível da
forma da Terra, da altitude da estação e da massa de rocha entre a estação e
o datum de referência:

    g_teorico(lat)      Fórmula Internacional da Gravidade 1980 (GRS80/IGF80,
                        Moritz, 1980 — "Geodetic Reference System 1980"):
                            g_theta = 978032.7 * (1 + 0.0053024*sin²(lat)
                                      - 0.0000058*sin²(2*lat))   [mGal]

    FAC (ar-livre)       FAC = 0.3086 * h                         [mGal], h em metros
                        (gradiente vertical padrão da gravidade no ar livre)

    BC (Bouguer simples) BC = 0.04193 * rho * h                   [mGal],
                        rho em g/cm³ (densidade crustal assumida — o valor
                        clássico de Hayford-Bowie é rho=2.67 g/cm³ = 2670 kg/m³),
                        h em metros — aproxima a massa de rocha entre a
                        estação e o datum como uma lâmina plana infinita
                        (placa de Bouguer), SEM levar em conta o relevo ao
                        redor da estação.

    Anomalia Bouguer     g_observado - g_teorico + FAC - BC

Terreno (correção de terreno completa, que soma de volta a massa "faltante"
em vales e subtrai o excesso de massa em morros ao redor da estação) NÃO é
calculado neste módulo — ver `limitations` em todo resultado. Isso é uma
limitação real e documentada do MVP, não um detalhe escondido: a correção de
terreno exige um DEM de alta resolução ao redor de cada estação e um algoritmo
de integração de massa (ex.: templates de Hammer, 1939, ou integração
numérica sobre o DEM) — matéria de uma fase posterior de processamento.

Referência: Moritz, H. (1980). "Geodetic Reference System 1980". Bulletin
Géodésique, 54(3). A fórmula é a mesma usada por praticamente todo software
de redução gravimétrica moderno (ex.: Oasis Montaj, Geosoft).
"""
from __future__ import annotations

import numpy as np

from app.geophysics.stats import method_metadata

DEFAULT_CRUSTAL_DENSITY_KG_M3 = 2670.0  # densidade padrão de Hayford-Bowie (2.67 g/cm3)
_FAC_COEFF_MGAL_PER_M = 0.3086
_BC_COEFF_MGAL_PER_GCM3_M = 0.04193


def normal_gravity_igf80(latitude_deg: float) -> float:
    """Gravidade teórica (normal) ao nível do elipsoide GRS80, pela Fórmula
    Internacional da Gravidade 1980 (IGF80), em mGal."""
    if not (-90.0 <= latitude_deg <= 90.0):
        raise ValueError("latitude_deg deve estar entre -90 e 90 graus")
    lat_rad = np.radians(latitude_deg)
    sin2_lat = np.sin(lat_rad) ** 2
    sin2_2lat = np.sin(2.0 * lat_rad) ** 2
    return float(978032.7 * (1.0 + 0.0053024 * sin2_lat - 0.0000058 * sin2_2lat))


def free_air_correction(elevation_m: float) -> float:
    """Correção ar-livre (mGal) — gradiente vertical padrão de -0.3086 mGal/m
    aplicado à altitude da estação acima do datum de referência (elipsoide)."""
    return float(_FAC_COEFF_MGAL_PER_M * elevation_m)


def simple_bouguer_correction(elevation_m: float, density_kg_m3: float = DEFAULT_CRUSTAL_DENSITY_KG_M3) -> float:
    """Correção Bouguer simples (mGal) — aproxima a massa de rocha entre a
    estação e o datum como uma lâmina plana infinita (placa de Bouguer) de
    densidade `density_kg_m3` (padrão: 2670 kg/m³ = 2.67 g/cm³)."""
    if density_kg_m3 <= 0:
        raise ValueError("density_kg_m3 deve ser positivo")
    density_g_cm3 = density_kg_m3 / 1000.0
    return float(_BC_COEFF_MGAL_PER_GCM3_M * density_g_cm3 * elevation_m)


def calculate_bouguer_anomaly(
    observed_gravity_mgal: float,
    latitude_deg: float,
    elevation_m: float,
    density_kg_m3: float = DEFAULT_CRUSTAL_DENSITY_KG_M3,
) -> dict:
    """Reduz uma leitura gravimétrica bruta (`observed_gravity_mgal`) a uma
    anomalia Bouguer simples, aplicando a gravidade teórica (IGF80), a
    correção ar-livre e a correção Bouguer simples, nessa ordem.

    Args:
        observed_gravity_mgal: leitura gravimétrica observada na estação,
            já calibrada/amarrada a uma base absoluta (mGal).
        latitude_deg: latitude geodésica da estação (graus decimais).
        elevation_m: altitude ortométrica/elipsoidal da estação acima do
            datum de referência (metros) — assumida positiva acima do nível
            do mar (o caso normal em levantamentos terrestres).
        density_kg_m3: densidade crustal assumida para a correção Bouguer
            (padrão: 2670 kg/m³, o valor clássico de Hayford-Bowie).
    """
    if elevation_m < -500.0:
        raise ValueError("elevation_m implausível (< -500 m) — verifique a unidade/sinal da altitude")

    g_theta = normal_gravity_igf80(latitude_deg)
    fac = free_air_correction(elevation_m)
    bc = simple_bouguer_correction(elevation_m, density_kg_m3)
    bouguer_anomaly_mgal = observed_gravity_mgal - g_theta + fac - bc

    return {
        "normal_gravity_mgal": g_theta,
        "free_air_correction_mgal": fac,
        "bouguer_correction_mgal": bc,
        "bouguer_anomaly_mgal": float(bouguer_anomaly_mgal),
        "density_kg_m3": float(density_kg_m3),
        **method_metadata(
            method=(
                "Reducao Bouguer simples: g_teorico = Formula Internacional da Gravidade 1980 (GRS80/"
                "Moritz 1980); FAC = 0.3086*h [mGal/m]; BC = 0.04193*rho[g/cm3]*h [mGal]; "
                "anomalia_bouguer = g_observado - g_teorico + FAC - BC"
            ),
            parameters={
                "latitude_deg": latitude_deg,
                "elevation_m": elevation_m,
                "density_kg_m3": density_kg_m3,
                "observed_gravity_mgal": observed_gravity_mgal,
            },
            uncertainty_note=(
                "A precisão da anomalia Bouguer resultante depende diretamente da precisão do "
                "gravímetro (tipicamente 0.01-0.05 mGal para gravímetros relativos modernos), da "
                "amarração a uma base gravimétrica absoluta, e da precisão da altitude da estação "
                "(um erro de 1 m em elevação produz ~0.2 mGal de erro combinado em FAC-BC, para "
                "densidade padrão) — GPS/GNSS geodésico é recomendado para a altitude, não GPS de "
                "navegação. A densidade assumida (`density_kg_m3`) é uma média regional; a densidade "
                "real da rocha sob cada estação pode diferir e introduzir um viés sistemático "
                "correlacionado com a topografia."
            ),
            limitations=(
                "Correção de terreno (terrain correction) NÃO é calculada neste módulo — a "
                "aproximação de placa de Bouguer assume topografia perfeitamente plana ao redor da "
                "estação, o que subestima a anomalia em terreno com relevo significativo (vales e "
                "morros próximos). Isso é uma limitação real do MVP, documentada explicitamente: uma "
                "correção de terreno completa exige um DEM de alta resolução ao redor de cada estação "
                "e um algoritmo de integração de massa (ex.: templates de Hammer), fora do escopo "
                "desta versão. Também não são aplicadas a correção de maré terrestre (tidal) nem a "
                "deriva instrumental do gravímetro — assume-se que a leitura de entrada já foi "
                "corrigida por essas duas antes de chegar a este módulo."
            ),
        ),
    }
