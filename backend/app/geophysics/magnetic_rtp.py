"""Redução ao polo (RTP) de uma grade de anomalia magnética de campo total,
pelo filtro de fase/amplitude no domínio do número de onda (Blakely, 1995,
"Potential Theory in Gravity and Magnetic Applications", cap. 12) — a mesma
técnica de filtragem 2D via FFT já usada na plataforma em
`radar-ai/app/radar/coregistration.py` (correlação de fase), aqui aplicada a
um operador de reforma espectral em vez de um deslocamento espacial.

Uma anomalia magnética observada com um campo ambiente inclinado (latitudes
não-polares) aparece deslocada/assimétrica em relação à fonte que a produz —
o pico observado não fica sobre a fonte, e o formato tem um lobo positivo e
um negativo adjacentes (a assinatura clássica de dipolo inclinado). RTP
remove essa distorção geométrica, simulando como a mesma fonte apareceria se
o campo magnético ambiente (e a magnetização induzida) fossem verticais (polo
magnético) — nessa condição a anomalia fica simétrica e centrada
exatamente sobre a fonte, facilitando a interpretação geológica direta
(delimitação de corpos, escolha de perfis).

Formulação (Blakely, 1995, eq. 12.5): para magnetização puramente induzida
(mesma direção do campo ambiente — sem remanência), com inclinação `I` e
declinação `D` conhecidas, o filtro de RTP no domínio do número de onda
(kx, ky) é:

    a1 = cos(I)*cos(D), a2 = cos(I)*sin(D), a3 = sin(I)     (cossenos diretores)
    Θ(kx,ky) = a3 + i*(a1*kx + a2*ky)/k,     k = sqrt(kx²+ky²)
    H_rtp(kx,ky) = 1 / Θ(kx,ky)²

Quando a magnetização remanente tem direção distinta do campo ambiente
(`inclination_magnetization_deg`/`declination_magnetization_deg` diferentes
de `inclination_field_deg`/`declination_field_deg`), o operador generaliza
para dois fatores de fase distintos, um por direção — `Θ_f` (campo) e `Θ_m`
(magnetização) — com `H_rtp = 1/(Θ_f * Θ_m)`; por padrão este módulo assume
magnetização puramente induzida (`Θ_f == Θ_m`), a premissa usual quando a
remanência não foi medida em amostras de rocha.

O componente de frequência zero (k=0, a média da grade) não tem direção
definida no filtro — é mantido inalterado (`H_rtp(0,0)=1`), preservando o
nível médio da anomalia.
"""
from __future__ import annotations

import numpy as np

from app.geophysics.stats import method_metadata

_MIN_INCLINATION_DEG_WARNING = 15.0  # abaixo disso, o filtro amplifica ruído perto do equador magnetico


def _rtp_operator(
    kx: np.ndarray,
    ky: np.ndarray,
    inclination_field_deg: float,
    declination_field_deg: float,
    inclination_mag_deg: float,
    declination_mag_deg: float,
) -> np.ndarray:
    """Monta o operador de RTP `H_rtp(kx,ky) = 1/(Theta_f * Theta_m)` (ver
    docstring do módulo). Retorna um array complexo do mesmo shape de kx/ky."""
    k = np.sqrt(kx ** 2 + ky ** 2)
    k_safe = np.where(k == 0, 1.0, k)  # evita divisão por zero em k=0; corrigido abaixo

    i_f, d_f = np.radians(inclination_field_deg), np.radians(declination_field_deg)
    i_m, d_m = np.radians(inclination_mag_deg), np.radians(declination_mag_deg)

    a1, a2, a3 = np.cos(i_m) * np.cos(d_m), np.cos(i_m) * np.sin(d_m), np.sin(i_m)
    b1, b2, b3 = np.cos(i_f) * np.cos(d_f), np.cos(i_f) * np.sin(d_f), np.sin(i_f)

    theta_m = a3 + 1j * (a1 * kx + a2 * ky) / k_safe
    theta_f = b3 + 1j * (b1 * kx + b2 * ky) / k_safe

    denom = theta_m * theta_f
    h_rtp = np.where(k == 0, 1.0 + 0j, 1.0 / denom)
    return h_rtp


def reduce_to_pole(
    grid: np.ndarray,
    pixel_size_m: float,
    inclination_deg: float,
    declination_deg: float,
    inclination_magnetization_deg: float | None = None,
    declination_magnetization_deg: float | None = None,
) -> dict:
    """Aplica a redução ao polo (RTP) a uma grade 2D de anomalia magnética de
    campo total, regularmente amostrada em `pixel_size_m` (metros, mesmo
    espaçamento em X e Y).

    Args:
        grid: array 2D (linhas=Y, colunas=X) da anomalia magnética observada (nT).
        pixel_size_m: tamanho do pixel/célula da grade (metros).
        inclination_deg, declination_deg: inclinação e declinação do campo
            magnético ambiente no local e época do levantamento (graus) —
            obtidas de um modelo geomagnético de referência (ex.: IGRF) para
            a data/local do levantamento.
        inclination_magnetization_deg, declination_magnetization_deg:
            inclinação/declinação da magnetização da fonte, se conhecida e
            distinta do campo ambiente (magnetização remanente). Quando
            omitidas, assume-se magnetização puramente induzida (mesma
            direção do campo ambiente) — a premissa padrão sem dados de
            paleomagnetismo de amostras de rocha.
    """
    arr = np.asarray(grid, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError("grid deve ser um array 2D (ny, nx)")
    ny, nx = arr.shape
    if ny < 4 or nx < 4:
        raise ValueError("grid muito pequena para um filtro espectral confiável (mínimo 4x4 células)")
    if pixel_size_m <= 0:
        raise ValueError("pixel_size_m deve ser positivo")
    if not (-90.0 <= inclination_deg <= 90.0):
        raise ValueError("inclination_deg deve estar entre -90 e 90 graus")

    inc_m = inclination_magnetization_deg if inclination_magnetization_deg is not None else inclination_deg
    dec_m = declination_magnetization_deg if declination_magnetization_deg is not None else declination_deg
    assumed_induced = inclination_magnetization_deg is None and declination_magnetization_deg is None

    kx1d = np.fft.fftfreq(nx, d=pixel_size_m) * 2.0 * np.pi
    ky1d = np.fft.fftfreq(ny, d=pixel_size_m) * 2.0 * np.pi
    kx, ky = np.meshgrid(kx1d, ky1d)

    spectrum = np.fft.fft2(arr)
    h_rtp = _rtp_operator(kx, ky, inclination_deg, declination_deg, inc_m, dec_m)
    rtp_spectrum = spectrum * h_rtp
    rtp_grid = np.real(np.fft.ifft2(rtp_spectrum))

    peak_idx = np.unravel_index(np.argmax(rtp_grid), rtp_grid.shape)
    trough_idx = np.unravel_index(np.argmin(rtp_grid), rtp_grid.shape)

    low_inclination_warning = abs(inclination_deg) < _MIN_INCLINATION_DEG_WARNING

    return {
        "rtp_grid": rtp_grid.tolist(),
        "shape": [int(ny), int(nx)],
        "peak_row": int(peak_idx[0]),
        "peak_col": int(peak_idx[1]),
        "peak_value_nt": float(rtp_grid[peak_idx]),
        "trough_row": int(trough_idx[0]),
        "trough_col": int(trough_idx[1]),
        "trough_value_nt": float(rtp_grid[trough_idx]),
        "assumed_purely_induced_magnetization": assumed_induced,
        "low_inclination_warning": bool(low_inclination_warning),
        **method_metadata(
            method=(
                "Reducao ao polo (RTP) via filtro de fase/amplitude no dominio do numero de onda "
                "(Blakely, 1995, eq. 12.5): H_rtp(kx,ky) = 1/(Theta_f(kx,ky)*Theta_m(kx,ky)), com "
                "Theta = sin(I) + i*cos(I)*cos(D-atan2(ky,kx)) por direcao (campo/magnetizacao); "
                "aplicado via numpy.fft.fft2 / ifft2"
            ),
            parameters={
                "pixel_size_m": pixel_size_m,
                "inclination_deg": inclination_deg,
                "declination_deg": declination_deg,
                "inclination_magnetization_deg": inc_m,
                "declination_magnetization_deg": dec_m,
                "assumed_purely_induced_magnetization": assumed_induced,
            },
            uncertainty_note=(
                "RTP é um filtro determinístico e reversível (sem estimativa estatística/incerteza "
                "formal própria) — a qualidade do resultado depende inteiramente da precisão de "
                "inclinação/declinação de entrada (erros de poucos graus já introduzem distorção "
                "residual visível, sobretudo perto do equador magnético) e da premissa de "
                "magnetização puramente induzida quando a remanência não é conhecida."
            ),
            limitations=(
                "Instável (amplifica ruído de alta frequência) em inclinações magnéticas baixas "
                "(próximo ao equador magnético, |inclinação| < 15° aproximadamente) — o termo sin(I) "
                "do operador se aproxima de zero e a divisão amplifica desproporcionalmente "
                "componentes de número de onda associados à direção leste-oeste; este módulo apenas "
                "sinaliza essa condição (`low_inclination_warning`), não aplica uma correção "
                "estabilizada de baixa latitude (ex.: RTP pseudo-inclinado). Assume grade regular sem "
                "dados faltantes (NaN) e continuidade periódica implícita da FFT — bordas da grade "
                "podem exibir artefatos de borda (wraparound) se a anomalia não decair a zero nas "
                "margens; não aplica preenchimento de borda (padding/tapering)."
            ),
        ),
    }
