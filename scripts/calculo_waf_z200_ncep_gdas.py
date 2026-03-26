#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Reemplazo de scripts/calculo_waf_z200.py usando el catálogo actual de NOAA PSL
que ya se usó para anom_var_ncep_gdas.py.

Qué hace:
1) Descarga hgt, uwnd y vwnd diarios/anuales del dataset NCEP GDAS en presión.
2) Calcula la media del período solicitado para hgt.
3) Calcula la climatología diaria (por defecto 1991-2020) del mismo rango
   calendario para hgt, uwnd y vwnd.
4) Obtiene la anomalía de altura geopotencial: hgt' = media_período - climatología.
5) Construye la función corriente geostrófica perturbada:
      psi' = g / f * hgt'
6) Calcula los flujos horizontales de actividad de onda (Takaya-Nakamura /
   formulación horizontal usada en el script original) usando como flujo básico
   la climatología de uwnd y vwnd.
7) Genera dos figuras:
      - psi_*.png           (anomalía de función corriente derivada de hgt)
      - Z_plumb_*.png       (anomalía de hgt + vectores de flujo)

Ejemplo de uso:
python calculo_waf_z200_ncep_gdas.py \
    --dateinit 2018-02-01 \
    --dateend 2018-02-28

También se puede cambiar el nivel (por defecto 200 mb):
python calculo_waf_z200_ncep_gdas.py \
    --dateinit 2018-02-01 \
    --dateend 2018-02-28 \
    --level 200mb
"""

from __future__ import annotations

import argparse
import datetime as dt
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import urlretrieve

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import netCDF4
import numpy as np
from cartopy.mpl.ticker import LatitudeFormatter, LongitudeFormatter
from matplotlib import pyplot as plt
from numpy import ma

BASE_URL = "https://downloads.psl.noaa.gov/Datasets/ncep"
DEFAULT_CLIMO_PERIOD = "1991-2020"
EARTH_RADIUS = 6_371_000.0  # m
OMEGA = 7.292115e-5         # rad s^-1
GRAVITY = 9.80665           # m s^-2
HGT_VAR = "hgt"
UWND_VAR = "uwnd"
VWND_VAR = "vwnd"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Calcula flujos de actividad de onda usando la base NCEP GDAS de PSL. "
            "La función corriente perturbada se obtiene a partir de hgt y del "
            "parámetro de Coriolis."
        )
    )
    parser.add_argument("--dateinit", required=True, help='Fecha inicial en formato "YYYY-MM-DD"')
    parser.add_argument("--dateend", required=True, help='Fecha final en formato "YYYY-MM-DD"')
    parser.add_argument(
        "--level",
        default="200mb",
        help='Nivel en hPa/mb. Ejemplos: 200, 200mb, 200hPa. Por defecto: 200mb',
    )
    parser.add_argument(
        "--latmin",
        type=float,
        default=-88.0,
        help="Latitud mínima del mapa. Por defecto: -88",
    )
    parser.add_argument(
        "--latmax",
        type=float,
        default=10.0,
        help="Latitud máxima del mapa. Por defecto: 10",
    )
    parser.add_argument(
        "--lonmin",
        type=float,
        default=0.0,
        help="Longitud mínima del mapa (0-360). Por defecto: 0",
    )
    parser.add_argument(
        "--lonmax",
        type=float,
        default=359.0,
        help="Longitud máxima del mapa (0-360). Por defecto: 359",
    )
    parser.add_argument(
        "--levcont",
        type=float,
        default=150.0,
        help="Máximo valor absoluto para los contornos/sombreado de hgt anomalía. Por defecto: 150",
    )
    parser.add_argument(
        "--levint",
        type=float,
        default=15.0,
        help="Intervalo para los contornos/sombreado de hgt anomalía. Por defecto: 15",
    )
    parser.add_argument(
        "--psi-levcont",
        type=float,
        default=None,
        help="Máximo valor absoluto para los contornos de psi'. Si no se pasa, se calcula automático.",
    )
    parser.add_argument(
        "--psi-levint",
        type=float,
        default=None,
        help="Intervalo de contorno para psi'. Si no se pasa, se calcula automático.",
    )
    parser.add_argument(
        "--quiver-percentile",
        type=float,
        default=60.0,
        help=(
            "Percentil mínimo del módulo del flujo para mostrar flechas. "
            "60 reproduce el criterio original (muestra el 40%% más intenso)."
        ),
    )
    parser.add_argument(
        "--quiver-stride",
        type=int,
        default=2,
        help="Paso espacial de las flechas. Por defecto: 2",
    )
    parser.add_argument(
        "--f-min",
        type=float,
        default=1.0e-5,
        help=(
            "Valor mínimo de |f| para construir psi'=g/f*hgt'. "
            "Sirve para evitar singularidades cerca del ecuador. Por defecto: 1e-5 s^-1"
        ),
    )
    parser.add_argument(
        "--wind-min",
        type=float,
        default=1.0,
        help="Módulo mínimo del flujo básico para calcular WAF. Por defecto: 1 m/s",
    )
    parser.add_argument(
        "--climo-period",
        default=DEFAULT_CLIMO_PERIOD,
        help=(
            "Período climatológico del archivo day.ltm. Por defecto 1991-2020. "
            "Ejemplo: 1991-2020"
        ),
    )
    parser.add_argument(
        "--cache-dir",
        default="./tmp/ncep_cache",
        help="Directorio donde se cachean los NetCDF descargados",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Fuerza la re-descarga de archivos aunque ya existan en caché",
    )
    return parser.parse_args()


def parse_level(level_text: str) -> float:
    match = re.search(r"-?\d+(?:\.\d+)?", str(level_text))
    if not match:
        raise ValueError(f'No pude interpretar el nivel "{level_text}"')
    return float(match.group(0))


def normalize_date(value: str) -> dt.date:
    return dt.datetime.strptime(value, "%Y-%m-%d").date()


def daterange(start_date: dt.date, end_date: dt.date) -> Iterable[dt.date]:
    current = start_date
    while current <= end_date:
        yield current
        current += dt.timedelta(days=1)


def ensure_cache_dir(cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)


def download_if_needed(filename: str, cache_dir: Path, force_download: bool = False) -> Path:
    ensure_cache_dir(cache_dir)
    local_path = cache_dir / filename
    if local_path.exists() and not force_download:
        return local_path

    url = f"{BASE_URL}/{filename}"
    print(f"Descargando {url}")
    try:
        urlretrieve(url, local_path)
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"No pude descargar {url}: {exc}") from exc

    return local_path


def safe_num2date(time_var: netCDF4.Variable) -> List[dt.date]:
    calendar = getattr(time_var, "calendar", "standard")
    decoded = netCDF4.num2date(time_var[:], units=time_var.units, calendar=calendar)
    out: List[dt.date] = []
    for item in decoded:
        out.append(dt.date(int(item.year), int(item.month), int(item.day)))
    return out


def masked_to_nan(arr: np.ndarray) -> np.ndarray:
    return np.ma.filled(np.ma.asarray(arr, dtype=np.float64), np.nan)


def get_level_index(ds: netCDF4.Dataset, requested_level: float) -> int:
    if "level" not in ds.variables:
        raise ValueError("El archivo no tiene dimensión 'level'; este script está pensado para variables en presión.")

    levels = np.asarray(ds.variables["level"][:], dtype=np.float64)
    matches = np.where(np.isclose(levels, requested_level, atol=1.0e-6))[0]
    if matches.size == 0:
        levels_text = ", ".join(str(int(x)) if float(x).is_integer() else str(x) for x in levels)
        raise ValueError(
            f"Nivel {requested_level:g} mb no disponible. Niveles disponibles: {levels_text}"
        )
    return int(matches[0])


def compute_period_mean(
    dataset_id: str,
    start_date: dt.date,
    end_date: dt.date,
    level_mb: float,
    cache_dir: Path,
    force_download: bool = False,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    sum_field: np.ndarray | None = None
    count_field: np.ndarray | None = None
    lat: np.ndarray | None = None
    lon: np.ndarray | None = None

    for year in range(start_date.year, end_date.year + 1):
        filename = f"{dataset_id}.{year}.nc"
        local_file = download_if_needed(filename, cache_dir, force_download=force_download)

        with netCDF4.Dataset(local_file, "r") as ds:
            lev_idx = get_level_index(ds, level_mb)
            dates = safe_num2date(ds.variables["time"])
            time_idx = [i for i, day in enumerate(dates) if start_date <= day <= end_date]

            if not time_idx:
                continue

            var_obj = ds.variables[dataset_id]
            try:
                var_obj.set_auto_maskandscale(True)
            except AttributeError:
                pass

            data = masked_to_nan(var_obj[time_idx, lev_idx, :, :])
            if data.ndim == 2:
                data = data[np.newaxis, :, :]

            partial_sum = np.nansum(data, axis=0)
            partial_count = np.sum(~np.isnan(data), axis=0).astype(np.float64)

            if sum_field is None:
                sum_field = np.zeros_like(partial_sum, dtype=np.float64)
                count_field = np.zeros_like(partial_count, dtype=np.float64)
                lat = np.asarray(ds.variables["lat"][:], dtype=np.float64)
                lon = np.asarray(ds.variables["lon"][:], dtype=np.float64)

            sum_field += partial_sum
            count_field += partial_count

    if sum_field is None or count_field is None or lat is None or lon is None:
        raise ValueError(
            f"No encontré datos para {dataset_id} entre {start_date.isoformat()} y {end_date.isoformat()}"
        )

    mean_field = np.divide(
        sum_field,
        count_field,
        out=np.full_like(sum_field, np.nan, dtype=np.float64),
        where=count_field > 0,
    )
    return mean_field, lat, lon


def build_climo_day_index(ds: netCDF4.Dataset) -> Dict[str, int]:
    """
    Arma un índice mes-día -> posición dentro del archivo climatológico.

    Los archivos day.ltm de este dataset tienen 365 días, no 366.
    """
    try:
        dates = safe_num2date(ds.variables["time"])
        mapping = {f"{day.month:02d}-{day.day:02d}": idx for idx, day in enumerate(dates)}
    except Exception:
        base = dt.date(2001, 1, 1)  # año no bisiesto
        ntime = len(ds.variables["time"])
        mapping = {
            f"{(base + dt.timedelta(days=i)).month:02d}-{(base + dt.timedelta(days=i)).day:02d}": i
            for i in range(ntime)
        }

    if len(mapping) < 365:
        raise ValueError("El archivo climatológico no tiene suficientes días para construir el índice mes-día")

    return mapping


def build_requested_calendar_weights(start_date: dt.date, end_date: dt.date) -> Counter:
    """
    Devuelve pesos por mes-día para promediar la climatología diaria sobre el
    mismo rango calendario del período pedido.

    Para 29 de febrero, como el archivo day.ltm tiene 365 días, se reparte el
    peso 50/50 entre 28-feb y 01-mar.
    """
    weights: Counter = Counter()
    for day in daterange(start_date, end_date):
        if day.month == 2 and day.day == 29:
            weights["02-28"] += 0.5
            weights["03-01"] += 0.5
        else:
            weights[f"{day.month:02d}-{day.day:02d}"] += 1.0
    return weights


def compute_climatology_mean(
    dataset_id: str,
    start_date: dt.date,
    end_date: dt.date,
    level_mb: float,
    cache_dir: Path,
    climo_period: str = DEFAULT_CLIMO_PERIOD,
    force_download: bool = False,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    candidates = [f"{dataset_id}.day.ltm.{climo_period}.nc"]
    if climo_period == DEFAULT_CLIMO_PERIOD:
        candidates.append(f"{dataset_id}.day.ltm.nc")

    local_file: Path | None = None
    last_error: Exception | None = None
    for filename in candidates:
        try:
            local_file = download_if_needed(filename, cache_dir, force_download=force_download)
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    if local_file is None:
        raise RuntimeError(
            f"No pude descargar la climatología para {dataset_id} ({climo_period}). Último error: {last_error}"
        )

    weights = build_requested_calendar_weights(start_date, end_date)

    with netCDF4.Dataset(local_file, "r") as ds:
        lev_idx = get_level_index(ds, level_mb)
        md_to_idx = build_climo_day_index(ds)

        var_obj = ds.variables[dataset_id]
        try:
            var_obj.set_auto_maskandscale(True)
        except AttributeError:
            pass

        lat = np.asarray(ds.variables["lat"][:], dtype=np.float64)
        lon = np.asarray(ds.variables["lon"][:], dtype=np.float64)
        sum_field: np.ndarray | None = None
        weight_field: np.ndarray | None = None

        for month_day, weight in sorted(weights.items()):
            if month_day not in md_to_idx:
                raise ValueError(
                    f"El día calendario {month_day} no existe en el archivo climatológico {local_file.name}"
                )
            idx = md_to_idx[month_day]
            field = masked_to_nan(var_obj[idx, lev_idx, :, :])
            valid = ~np.isnan(field)

            if sum_field is None:
                sum_field = np.zeros_like(field, dtype=np.float64)
                weight_field = np.zeros_like(field, dtype=np.float64)

            sum_field[valid] += weight * field[valid]
            weight_field[valid] += weight

    if sum_field is None or weight_field is None:
        raise ValueError("No pude construir la media climatológica")

    climo_mean = np.divide(
        sum_field,
        weight_field,
        out=np.full_like(sum_field, np.nan, dtype=np.float64),
        where=weight_field > 0,
    )
    return climo_mean, lat, lon


def check_grids(lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray, label: str) -> None:
    if lat1.shape != lat2.shape or lon1.shape != lon2.shape:
        raise ValueError(f"Las grillas de {label} no coinciden")
    if not np.allclose(lat1, lat2) or not np.allclose(lon1, lon2):
        raise ValueError(f"Las coordenadas lat/lon de {label} difieren")


def coriolis(lat_deg: np.ndarray) -> np.ndarray:
    return 2.0 * OMEGA * np.sin(np.deg2rad(lat_deg))


def _check_regular_spacing(values: np.ndarray, name: str) -> float:
    diffs = np.diff(values)
    if diffs.size == 0:
        raise ValueError(f"No hay suficientes puntos en {name} para derivar")
    mean_diff = float(np.mean(diffs))
    if not np.allclose(diffs, mean_diff, atol=1.0e-10, rtol=1.0e-6):
        raise ValueError(f"La grilla de {name} no es regular; este script asume grilla regular")
    return mean_diff


def first_derivative(field: np.ndarray, coords: np.ndarray, axis: int, cyclic: bool = False) -> np.ndarray:
    arr = np.asarray(field, dtype=np.float64)
    x = np.asarray(coords, dtype=np.float64)

    if cyclic:
        dx = _check_regular_spacing(x, "longitud")
        return (np.roll(arr, -1, axis=axis) - np.roll(arr, 1, axis=axis)) / (2.0 * dx)

    return np.gradient(arr, x, axis=axis, edge_order=2)


def second_derivative(field: np.ndarray, coords: np.ndarray, axis: int, cyclic: bool = False) -> np.ndarray:
    arr = np.asarray(field, dtype=np.float64)
    x = np.asarray(coords, dtype=np.float64)

    if cyclic:
        dx = _check_regular_spacing(x, "longitud")
        return (np.roll(arr, -1, axis=axis) - 2.0 * arr + np.roll(arr, 1, axis=axis)) / (dx * dx)

    first = np.gradient(arr, x, axis=axis, edge_order=2)
    return np.gradient(first, x, axis=axis, edge_order=2)


def compute_wave_activity_flux(
    hgt_anom: np.ndarray,
    u_mean: np.ndarray,
    v_mean: np.ndarray,
    lat: np.ndarray,
    lon: np.ndarray,
    level_mb: float,
    f_min: float,
    wind_min: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    latrad = np.deg2rad(np.asarray(lat, dtype=np.float64))
    lonrad = np.deg2rad(np.asarray(lon, dtype=np.float64))

    f = coriolis(lat)[:, np.newaxis]
    coslat = np.cos(latrad)[:, np.newaxis]

    with np.errstate(divide="ignore", invalid="ignore"):
        psi = np.where(np.abs(f) >= f_min, GRAVITY * hgt_anom / f, np.nan)

    psi_dx = first_derivative(psi, lonrad, axis=1, cyclic=True)
    psi_dxx = second_derivative(psi, lonrad, axis=1, cyclic=True)
    psi_dy = first_derivative(psi, latrad, axis=0, cyclic=False)
    psi_dyy = second_derivative(psi, latrad, axis=0, cyclic=False)
    psi_dxy = first_derivative(psi_dx, latrad, axis=0, cyclic=False)

    xu = psi_dx * psi_dx - psi * psi_dxx
    xv = psi_dx * psi_dy - psi * psi_dxy
    yv = psi_dy * psi_dy - psi * psi_dyy

    wind = np.sqrt(u_mean * u_mean + v_mean * v_mean)
    coeff = (level_mb / 1000.0) / (2.0 * wind * EARTH_RADIUS * EARTH_RADIUS)

    with np.errstate(divide="ignore", invalid="ignore"):
        px = coeff * ((u_mean / coslat) * xu + v_mean * xv)
        py = coeff * (u_mean * xv + v_mean * coslat * yv)

    valid = (
        np.isfinite(psi)
        & np.isfinite(u_mean)
        & np.isfinite(v_mean)
        & np.isfinite(px)
        & np.isfinite(py)
        & (wind > wind_min)
        & (np.abs(f) >= f_min)
        & (np.abs(coslat) > 1.0e-6)
    )
    px = np.where(valid, px, np.nan)
    py = np.where(valid, py, np.nan)
    return psi, px, py


def nice_number(value: float) -> float:
    if not np.isfinite(value) or value <= 0:
        return 1.0
    exponent = math.floor(math.log10(value))
    fraction = value / 10.0**exponent
    if fraction <= 1.0:
        nice_fraction = 1.0
    elif fraction <= 2.0:
        nice_fraction = 2.0
    elif fraction <= 2.5:
        nice_fraction = 2.5
    elif fraction <= 5.0:
        nice_fraction = 5.0
    else:
        nice_fraction = 10.0
    return nice_fraction * 10.0**exponent


def build_symmetric_levels(
    field: np.ndarray,
    levcont: float | None = None,
    levint: float | None = None,
    approx_intervals: int = 20,
) -> np.ndarray:
    if levcont is not None and levint is not None:
        if levcont <= 0 or levint <= 0:
            raise ValueError("Los niveles de contorno deben ser mayores que 0")
        return np.arange(-levcont, levcont + levint, levint)

    finite = np.abs(field[np.isfinite(field)])
    if finite.size == 0:
        levcont_auto = 1.0
    else:
        levcont_auto = float(np.nanpercentile(finite, 98.0))
        if not np.isfinite(levcont_auto) or levcont_auto <= 0:
            levcont_auto = float(np.nanmax(finite)) if finite.size else 1.0
        if not np.isfinite(levcont_auto) or levcont_auto <= 0:
            levcont_auto = 1.0

    if levint is None:
        step_guess = 2.0 * levcont_auto / max(approx_intervals, 2)
        levint_auto = nice_number(step_guess)
    else:
        levint_auto = levint

    if levcont is None:
        levcont_final = levint_auto * math.ceil(levcont_auto / levint_auto)
    else:
        levcont_final = levcont

    if levcont_final <= 0 or levint_auto <= 0:
        raise ValueError("No pude construir niveles de contorno válidos")
    return np.arange(-levcont_final, levcont_final + levint_auto, levint_auto)


def region_mask(lat: np.ndarray, lon: np.ndarray, latmin: float, latmax: float, lonmin: float, lonmax: float) -> np.ndarray:
    lat_low = min(latmin, latmax)
    lat_high = max(latmin, latmax)
    lat_ok = (lat >= lat_low) & (lat <= lat_high)

    if lonmin <= lonmax:
        lon_ok = (lon >= lonmin) & (lon <= lonmax)
    else:
        lon_ok = (lon >= lonmin) | (lon <= lonmax)

    return lat_ok[:, np.newaxis] & lon_ok[np.newaxis, :]


def apply_map_decorations(ax: plt.Axes, crs_latlon: ccrs.CRS) -> None:
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS, linestyle="-", alpha=0.5)
    ax.gridlines(crs=crs_latlon, linewidth=0.3, linestyle="-")
    ax.set_xticks(np.linspace(0, 360, 7), crs=crs_latlon)
    ax.set_yticks(np.linspace(-80, 10, 10), crs=crs_latlon)
    ax.xaxis.set_major_formatter(LongitudeFormatter(zero_direction_label=True))
    ax.yaxis.set_major_formatter(LatitudeFormatter())


def build_output_name(prefix: str, level_text: str, start_date: dt.date, end_date: dt.date) -> str:
    level_suffix = "" if level_text.lower() == "200mb" else f"_{level_text}"
    return f"{prefix}{level_suffix}_{start_date:%d%m%Y}-{end_date:%d%m%Y}.png"


def plot_psi_anomaly(
    psi_anom: np.ndarray,
    lat: np.ndarray,
    lon: np.ndarray,
    start_date: dt.date,
    end_date: dt.date,
    level_text: str,
    latmin: float,
    latmax: float,
    lonmin: float,
    lonmax: float,
    levcont: float | None,
    levint: float | None,
) -> str:
    clevs = build_symmetric_levels(psi_anom, levcont=levcont, levint=levint)
    lons, lats = np.meshgrid(lon, lat)

    fig = plt.figure(figsize=(16, 11))
    ax = plt.subplot(projection=ccrs.PlateCarree(central_longitude=180))
    crs_latlon = ccrs.PlateCarree()

    ax.set_extent([lonmin, lonmax, min(latmin, latmax), max(latmin, latmax)], crs=crs_latlon)
    im = ax.contourf(
        lons,
        lats,
        np.squeeze(psi_anom),
        clevs,
        transform=crs_latlon,
        cmap="RdBu_r",
        extend="both",
    )
    ax.contour(
        lons,
        lats,
        np.squeeze(psi_anom),
        clevs,
        colors="k",
        linewidths=0.5,
        transform=crs_latlon,
    )

    cbar = plt.colorbar(im, fraction=0.052, pad=0.04, shrink=0.3, aspect=12)
    cbar.set_label(r"m$^2$ s$^{-1}$")

    apply_map_decorations(ax, crs_latlon)
    ax.set_title(
        "Anomalías de función corriente geostrófica "
        f"{level_text} {start_date:%d/%m/%Y}-{end_date:%d/%m/%Y}"
    )

    output_name = build_output_name("psi", level_text, start_date, end_date)
    plt.savefig(output_name, dpi=300, bbox_inches="tight", orientation="landscape")
    plt.close(fig)
    return output_name


def plot_hgt_and_waf(
    hgt_anom: np.ndarray,
    px: np.ndarray,
    py: np.ndarray,
    lat: np.ndarray,
    lon: np.ndarray,
    start_date: dt.date,
    end_date: dt.date,
    level_text: str,
    latmin: float,
    latmax: float,
    lonmin: float,
    lonmax: float,
    levcont: float,
    levint: float,
    quiver_percentile: float,
    quiver_stride: int,
) -> str:
    if levcont <= 0 or levint <= 0:
        raise ValueError("--levcont y --levint deben ser mayores que 0")
    if quiver_stride <= 0:
        raise ValueError("--quiver-stride debe ser mayor que 0")
    if not (0.0 <= quiver_percentile <= 100.0):
        raise ValueError("--quiver-percentile debe estar entre 0 y 100")

    clevs = np.arange(-levcont, levcont + levint, levint)
    lons, lats = np.meshgrid(lon, lat)

    fig = plt.figure(figsize=(16, 11))
    ax = plt.subplot(projection=ccrs.PlateCarree(central_longitude=180))
    crs_latlon = ccrs.PlateCarree()

    ax.set_extent([lonmin, lonmax, min(latmin, latmax), max(latmin, latmax)], crs=crs_latlon)
    im = ax.contourf(
        lons,
        lats,
        np.squeeze(hgt_anom),
        clevs,
        transform=crs_latlon,
        cmap="RdBu_r",
        extend="both",
    )
    ax.contour(
        lons,
        lats,
        np.squeeze(hgt_anom),
        clevs,
        colors="k",
        linewidths=0.5,
        transform=crs_latlon,
    )

    cbar = plt.colorbar(im, fraction=0.052, pad=0.04, shrink=0.3, aspect=12)
    cbar.set_label("m")

    magnitude = np.sqrt(px * px + py * py)
    mask_box = region_mask(lat, lon, latmin, latmax, lonmin, lonmax)
    finite_mag = magnitude[np.isfinite(magnitude) & mask_box]
    if finite_mag.size:
        threshold = float(np.nanpercentile(finite_mag, quiver_percentile))
    else:
        threshold = np.nan

    if np.isfinite(threshold):
        flux_mask = ~np.isfinite(magnitude) | (magnitude < threshold)
    else:
        flux_mask = ~np.isfinite(magnitude)

    px_mask = ma.array(px, mask=flux_mask)
    py_mask = ma.array(py, mask=flux_mask)

    row_slice = slice(2, -1, quiver_stride)
    col_slice = slice(2, -1, quiver_stride)
    ax.quiver(
        lons[row_slice, col_slice],
        lats[row_slice, col_slice],
        px_mask[row_slice, col_slice],
        py_mask[row_slice, col_slice],
        width=1.0e-3,
        headwidth=3.0,
        headlength=2.2,
        transform=crs_latlon,
    )

    apply_map_decorations(ax, crs_latlon)
    ax.set_title(
        f"Anomalías hgt {level_text} y flujos de actividad de onda "
        f"{start_date:%d/%m/%Y}-{end_date:%d/%m/%Y}"
    )

    output_name = build_output_name("Z_plumb", level_text, start_date, end_date)
    plt.savefig(output_name, dpi=300, bbox_inches="tight", orientation="landscape")
    plt.close(fig)
    return output_name


def main() -> int:
    args = parse_args()

    start_date = normalize_date(args.dateinit)
    end_date = normalize_date(args.dateend)
    if end_date < start_date:
        raise ValueError("--dateend no puede ser anterior a --dateinit")

    level_mb = parse_level(args.level)
    level_text = f"{int(level_mb)}mb" if float(level_mb).is_integer() else f"{level_mb:g}mb"
    cache_dir = Path(args.cache_dir)

    print(
        f"Calculando WAF en {level_text} para {start_date.isoformat()} -> {end_date.isoformat()} "
        f"usando {HGT_VAR}, {UWND_VAR} y {VWND_VAR}"
    )

    hgt_period, lat_hgt_p, lon_hgt_p = compute_period_mean(
        dataset_id=HGT_VAR,
        start_date=start_date,
        end_date=end_date,
        level_mb=level_mb,
        cache_dir=cache_dir,
        force_download=args.force_download,
    )
    hgt_clim, lat_hgt_c, lon_hgt_c = compute_climatology_mean(
        dataset_id=HGT_VAR,
        start_date=start_date,
        end_date=end_date,
        level_mb=level_mb,
        cache_dir=cache_dir,
        climo_period=args.climo_period,
        force_download=args.force_download,
    )
    check_grids(lat_hgt_p, lon_hgt_p, lat_hgt_c, lon_hgt_c, label="hgt")
    hgt_anom = hgt_period - hgt_clim

    u_clim, lat_u, lon_u = compute_climatology_mean(
        dataset_id=UWND_VAR,
        start_date=start_date,
        end_date=end_date,
        level_mb=level_mb,
        cache_dir=cache_dir,
        climo_period=args.climo_period,
        force_download=args.force_download,
    )
    v_clim, lat_v, lon_v = compute_climatology_mean(
        dataset_id=VWND_VAR,
        start_date=start_date,
        end_date=end_date,
        level_mb=level_mb,
        cache_dir=cache_dir,
        climo_period=args.climo_period,
        force_download=args.force_download,
    )

    check_grids(lat_hgt_p, lon_hgt_p, lat_u, lon_u, label="hgt y uwnd")
    check_grids(lat_hgt_p, lon_hgt_p, lat_v, lon_v, label="hgt y vwnd")

    psi_anom, px, py = compute_wave_activity_flux(
        hgt_anom=hgt_anom,
        u_mean=u_clim,
        v_mean=v_clim,
        lat=lat_hgt_p,
        lon=lon_hgt_p,
        level_mb=level_mb,
        f_min=args.f_min,
        wind_min=args.wind_min,
    )

    psi_file = plot_psi_anomaly(
        psi_anom=psi_anom,
        lat=lat_hgt_p,
        lon=lon_hgt_p,
        start_date=start_date,
        end_date=end_date,
        level_text=level_text,
        latmin=args.latmin,
        latmax=args.latmax,
        lonmin=args.lonmin,
        lonmax=args.lonmax,
        levcont=args.psi_levcont,
        levint=args.psi_levint,
    )

    waf_file = plot_hgt_and_waf(
        hgt_anom=hgt_anom,
        px=px,
        py=py,
        lat=lat_hgt_p,
        lon=lon_hgt_p,
        start_date=start_date,
        end_date=end_date,
        level_text=level_text,
        latmin=args.latmin,
        latmax=args.latmax,
        lonmin=args.lonmin,
        lonmax=args.lonmax,
        levcont=args.levcont,
        levint=args.levint,
        quiver_percentile=args.quiver_percentile,
        quiver_stride=args.quiver_stride,
    )

    print(f"Figura psi guardada en: {psi_file}")
    print(f"Figura hgt+WAF guardada en: {waf_file}")
    print(f"Archivos cacheados en: {cache_dir.resolve()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
