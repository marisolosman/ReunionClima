#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Reemplazo de scripts/anom_var.py usando el catálogo actual de NOAA PSL:
https://psl.noaa.gov/data/gridded/data.ncep.html

Qué hace:
1) Descarga los archivos diarios anuales del dataset NCEP GDAS.
2) Calcula el campo medio del período pedido.
3) Descarga la climatología diaria (por defecto 1991-2020) de la misma variable.
4) Calcula la media climatológica para los mismos días calendario.
5) Obtiene la anomalía = media_del_período - media_climatológica.
6) Genera un mapa JPG parecido al script original.

Ejemplo de uso:
python anom_var_ncep_gdas.py \
    --dateinit 2018-02-01 \
    --dateend 2018-02-28 \
    --variable Zg \
    --level 200mb \
    --latmin -60 \
    --latmax -20 \
    --lonmin 250 \
    --lonmax 340 \
    --levcont 200 \
    --levint 20
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from collections import Counter
from dataclasses import dataclass
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

BASE_URL = "https://downloads.psl.noaa.gov/Datasets/ncep"
DEFAULT_CLIMO_PERIOD = "1991-2020"
MIN_AVAILABLE_YEAR = 1979


@dataclass(frozen=True)
class VariableSpec:
    dataset_id: str
    plot_name: str
    units: str


# Mantiene compatibilidad con el script viejo (U, V, Zg)
# y permite pasar directamente el ID nuevo del catálogo.
VARIABLES: Dict[str, VariableSpec] = {
    "u": VariableSpec("uwnd", "u-wind", "m/s"),
    "uwnd": VariableSpec("uwnd", "u-wind", "m/s"),
    "v": VariableSpec("vwnd", "v-wind", "m/s"),
    "vwnd": VariableSpec("vwnd", "v-wind", "m/s"),
    "zg": VariableSpec("hgt", "Geopotential height", "m"),
    "hgt": VariableSpec("hgt", "Geopotential height", "m"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Calcula anomalías de variables NCEP GDAS a partir del campo medio "
            "del período y de la climatología diaria a largo plazo."
        )
    )
    parser.add_argument("--dateinit", required=True, help='Fecha inicial en formato "YYYY-MM-DD"')
    parser.add_argument("--dateend", required=True, help='Fecha final en formato "YYYY-MM-DD"')
    parser.add_argument(
        "--variable",
        required=True,
        help='Variable: U, V, Zg o directamente el ID nuevo del catálogo (uwnd, vwnd, hgt)',
    )
    parser.add_argument(
        "--level",
        required=True,
        help='Nivel en hPa/mb. Ejemplos: 200, 200mb, 200hPa',
    )
    parser.add_argument("--latmin", required=True, type=float, help="Latitud mínima")
    parser.add_argument("--latmax", required=True, type=float, help="Latitud máxima")
    parser.add_argument("--lonmin", required=True, type=float, help="Longitud mínima")
    parser.add_argument("--lonmax", required=True, type=float, help="Longitud máxima")
    parser.add_argument("--levcont", required=True, type=float, help="Máximo valor absoluto para contornos")
    parser.add_argument("--levint", required=True, type=float, help="Intervalo entre contornos")
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


def resolve_variable(user_value: str) -> VariableSpec:
    key = user_value.strip().lower()
    if key not in VARIABLES:
        valid = ", ".join(sorted({k for k in VARIABLES.keys()}))
        raise ValueError(f'Variable no soportada: "{user_value}". Opciones: {valid}')
    return VARIABLES[key]


def parse_level(level_text: str) -> float:
    match = re.search(r"-?\d+(?:\.\d+)?", str(level_text))
    if not match:
        raise ValueError(f'No pude interpretar el nivel "{level_text}"')
    return float(match.group(0))


def daterange(start_date: dt.date, end_date: dt.date) -> Iterable[dt.date]:
    current = start_date
    while current <= end_date:
        yield current
        current += dt.timedelta(days=1)


def normalize_date(value: str) -> dt.date:
    return dt.datetime.strptime(value, "%Y-%m-%d").date()


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
    matches = np.where(np.isclose(levels, requested_level, atol=1e-6))[0]
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
        # Fallback robusto si hubiera problemas al decodificar tiempo.
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

    Para 29 de febrero, como el archivo day.ltm de este dataset tiene 365 días,
    se reparte el peso 50/50 entre 28-feb y 01-mar.
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
    # Alias útil si NOAA mantiene además un archivo day.ltm.nc que apunta al mismo período.
    if climo_period == DEFAULT_CLIMO_PERIOD:
        candidates.append(f"{dataset_id}.day.ltm.nc")

    local_file: Path | None = None
    last_error: Exception | None = None
    for filename in candidates:
        try:
            local_file = download_if_needed(filename, cache_dir, force_download=force_download)
            break
        except Exception as exc:  # noqa: BLE001 - queremos probar el alias fallback
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


def check_grids(lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray) -> None:
    if lat1.shape != lat2.shape or lon1.shape != lon2.shape:
        raise ValueError("Las grillas del campo del período y de la climatología no coinciden")
    if not np.allclose(lat1, lat2) or not np.allclose(lon1, lon2):
        raise ValueError("Las coordenadas lat/lon del campo del período y la climatología difieren")


def build_output_name(
    dataset_id: str,
    level_text: str,
    start_date: dt.date,
    end_date: dt.date,
    latmin: float,
    latmax: float,
    lonmin: float,
    lonmax: float,
) -> str:
    return (
        f"Anom{dataset_id}_{level_text}_"
        f"{start_date:%d%m%Y}_{end_date:%d%m%Y}_"
        f"{latmin:g}_{latmax:g}_{lonmin:g}_{lonmax:g}.jpg"
    )


def plot_anomaly(
    anomaly: np.ndarray,
    lat: np.ndarray,
    lon: np.ndarray,
    dataset_id: str,
    plot_name: str,
    units: str,
    level_text: str,
    start_date: dt.date,
    end_date: dt.date,
    latmin: float,
    latmax: float,
    lonmin: float,
    lonmax: float,
    levcont: float,
    levint: float,
) -> str:
    if levint <= 0:
        raise ValueError("--levint debe ser mayor que 0")
    if levcont <= 0:
        raise ValueError("--levcont debe ser mayor que 0")

    clevs = np.arange(-levcont, levcont + levint, levint)
    if clevs.size < 2:
        raise ValueError("No pude construir los niveles de contorno. Revisar --levcont y --levint")

    lons, lats = np.meshgrid(lon, lat)

    fig = plt.figure(figsize=(16, 11))
    ax = plt.subplot(projection=ccrs.PlateCarree(central_longitude=180))

    data_crs = ccrs.PlateCarree()
    ax.set_extent([lonmin, lonmax, latmin, latmax], crs=data_crs)

    im = ax.contourf(
        lons,
        lats,
        np.squeeze(anomaly),
        clevs,
        transform=data_crs,
        cmap="RdBu_r",
        extend="both",
    )
    ax.contour(
        lons,
        lats,
        np.squeeze(anomaly),
        clevs,
        colors="k",
        linewidths=0.5,
        transform=data_crs,
    )

    cbar = plt.colorbar(im, fraction=0.052, pad=0.04, shrink=0.3, aspect=12)
    cbar.set_label(units)

    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS, linestyle="-", alpha=0.5)
    ax.gridlines(crs=data_crs, linewidth=0.3, linestyle="-")
    ax.set_xticks(np.linspace(0, 360, 7), crs=data_crs)
    ax.set_yticks(np.linspace(-80, 10, 10), crs=data_crs)
    ax.xaxis.set_major_formatter(LongitudeFormatter(zero_direction_label=True))
    ax.yaxis.set_major_formatter(LatitudeFormatter())
    ax.set_title(
        f"Anomalías {plot_name} ({dataset_id}) {level_text} "
        f"{start_date:%d/%m/%Y}-{end_date:%d/%m/%Y}"
    )

    output_name = build_output_name(
        dataset_id=dataset_id,
        level_text=level_text,
        start_date=start_date,
        end_date=end_date,
        latmin=latmin,
        latmax=latmax,
        lonmin=lonmin,
        lonmax=lonmax,
    )
    plt.savefig(output_name, dpi=300, bbox_inches="tight", orientation="landscape")
    plt.close(fig)
    return output_name


def main() -> int:
    args = parse_args()

    start_date = normalize_date(args.dateinit)
    end_date = normalize_date(args.dateend)
    if end_date < start_date:
        raise ValueError("--dateend no puede ser anterior a --dateinit")
    if start_date.year < MIN_AVAILABLE_YEAR:
        raise ValueError(
            f"Este dataset empieza en {MIN_AVAILABLE_YEAR} para las variables de presión usadas acá."
        )

    spec = resolve_variable(args.variable)
    level_mb = parse_level(args.level)
    level_text = f"{int(level_mb)}mb" if float(level_mb).is_integer() else f"{level_mb:g}mb"
    cache_dir = Path(args.cache_dir)

    print(
        f"Calculando anomalía de {spec.dataset_id} ({spec.plot_name}) en {level_text} "
        f"para {start_date.isoformat()} -> {end_date.isoformat()}"
    )

    period_mean, lat_p, lon_p = compute_period_mean(
        dataset_id=spec.dataset_id,
        start_date=start_date,
        end_date=end_date,
        level_mb=level_mb,
        cache_dir=cache_dir,
        force_download=args.force_download,
    )

    climo_mean, lat_c, lon_c = compute_climatology_mean(
        dataset_id=spec.dataset_id,
        start_date=start_date,
        end_date=end_date,
        level_mb=level_mb,
        cache_dir=cache_dir,
        climo_period=args.climo_period,
        force_download=args.force_download,
    )

    check_grids(lat_p, lon_p, lat_c, lon_c)
    anomaly = period_mean - climo_mean

    output = plot_anomaly(
        anomaly=anomaly,
        lat=lat_p,
        lon=lon_p,
        dataset_id=spec.dataset_id,
        plot_name=spec.plot_name,
        units=spec.units,
        level_text=level_text,
        start_date=start_date,
        end_date=end_date,
        latmin=args.latmin,
        latmax=args.latmax,
        lonmin=args.lonmin,
        lonmax=args.lonmax,
        levcont=args.levcont,
        levint=args.levint,
    )

    print(f"Figura guardada en: {output}")
    print(f"Archivos cacheados en: {cache_dir.resolve()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - CLI simple y mensaje claro
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
