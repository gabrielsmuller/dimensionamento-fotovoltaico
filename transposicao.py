# -*- coding: utf-8 -*-
"""Transposição da irradiação horizontal para o plano dos módulos (modelo de Perez).

O Atlas Brasileiro de Energia Solar fornece a irradiação global horizontal (GHI)
média diária de cada mês. O modelo de Perez, implementado na biblioteca pvlib,
opera com valores instantâneos. Para cada mês, este módulo:

1. adota o dia representativo do mês (Klein, 1977);
2. distribui a GHI diária ao longo do dia proporcionalmente ao cosseno do ângulo
   zenital (índice de claridade constante ao longo do dia);
3. separa as componentes direta e difusa pelo modelo de Erbs;
4. transpõe para o plano inclinado pelo modelo de Perez (pvlib);
5. integra o dia, obtendo a irradiação média diária no plano dos módulos (POA).
"""
import numpy as np
import pandas as pd
import pvlib

# Dia representativo de cada mês (Klein, 1977), em dia do mês
DIAS_REPRESENTATIVOS = [17, 16, 16, 15, 15, 11, 17, 16, 15, 15, 14, 10]

# Azimute da superfície na convenção da pvlib (graus a partir do Norte, sentido horário)
AZIMUTES = {
    "Norte": 0, "Nordeste": 45, "Leste": 90, "Sudeste": 135,
    "Sul": 180, "Sudoeste": 225, "Oeste": 270, "Noroeste": 315,
}

ALBEDO_PADRAO = 0.2
PASSO_MINUTOS = 5
ANO_REFERENCIA = 2023  # ano não bissexto, usado apenas para montar as datas


def irradiacao_plano_inclinado(latitude, longitude, ghi_mensal, inclinacao, orientacao,
                               albedo=ALBEDO_PADRAO):
    """Irradiação média diária no plano dos módulos, mês a mês.

    ghi_mensal: 12 valores de GHI média diária (Wh/m²·dia), de janeiro a dezembro.
    inclinacao: graus em relação à horizontal (número ou texto como "25°").
    orientacao: nome do ponto cardeal (ver AZIMUTES) ou azimute em graus.
    Retorna uma lista com 12 valores em Wh/m²·dia.
    """
    beta = float(str(inclinacao).replace("°", ""))
    azimute = AZIMUTES[orientacao] if isinstance(orientacao, str) else float(orientacao)
    # fuso horário solar aproximado pela longitude: só a forma do dia importa
    fuso = pd.Timedelta(hours=longitude / 15.0)

    poa_mensal = []
    for mes, ghi_dia in enumerate(ghi_mensal, start=1):
        dia = pd.Timestamp(ANO_REFERENCIA, mes, DIAS_REPRESENTATIVOS[mes - 1])
        tempos_locais = pd.date_range(dia, dia + pd.Timedelta(days=1), freq=f"{PASSO_MINUTOS}min",
                                      inclusive="left")
        tempos = (tempos_locais - fuso).tz_localize("UTC")

        sol = pvlib.solarposition.get_solarposition(tempos, latitude, longitude)
        cos_z = np.clip(np.cos(np.radians(sol["apparent_zenith"].to_numpy())), 0, None)
        dni_extra = pvlib.irradiance.get_extra_radiation(tempos).to_numpy()

        horas_por_passo = PASSO_MINUTOS / 60
        energia_extraterrestre = np.sum(dni_extra * cos_z) * horas_por_passo  # Wh/m²·dia
        if energia_extraterrestre <= 0 or ghi_dia <= 0:
            poa_mensal.append(0.0)
            continue

        # GHI instantânea proporcional à extraterrestre horizontal (Kt constante no dia)
        kt = ghi_dia / energia_extraterrestre
        ghi = kt * dni_extra * cos_z

        erbs = pvlib.irradiance.erbs(ghi, sol["zenith"].to_numpy(), tempos)
        dni = np.nan_to_num(np.asarray(erbs["dni"], dtype=float))
        dhi = np.nan_to_num(np.asarray(erbs["dhi"], dtype=float))

        poa = pvlib.irradiance.get_total_irradiance(
            surface_tilt=beta, surface_azimuth=azimute,
            solar_zenith=sol["apparent_zenith"].to_numpy(), solar_azimuth=sol["azimuth"].to_numpy(),
            dni=dni, ghi=ghi, dhi=dhi, dni_extra=dni_extra,
            airmass=pvlib.atmosphere.get_relative_airmass(sol["apparent_zenith"].to_numpy()),
            albedo=albedo, model="perez",
        )
        poa_global = np.nan_to_num(np.asarray(poa["poa_global"], dtype=float))
        poa_mensal.append(float(np.sum(np.clip(poa_global, 0, None)) * horas_por_passo))

    return poa_mensal
