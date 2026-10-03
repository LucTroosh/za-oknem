"""IMGW observations; semantics/timezone are gated separately from transport (ADR-034)."""

import math
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

PARSER_VERSION = "imgw-weather-1"
# Canonical units only become publishable after the operator verifies the API dictionary.
METEO_FIELDS = {
    "temperatura_powietrza": ("temperature_2m", "°C", -90, 60),
    "wilgotnosc_wzgledna": ("relative_humidity_2m", "%", 0, 100),
    "wiatr_kierunek": ("wind_direction_10m", "°", 0, 360),
    "wiatr_srednia_predkosc": ("wind_mean_ms", "m/s", 0, 120),
    "wiatr_predkosc_maksymalna": ("wind_maximum_ms", "m/s", 0, 150),
    "wiatr_poryw_10min": ("wind_gust_10min_ms", "m/s", 0, 150),
    "opad_10min": ("precip_10min_mm", "mm", 0, 500),
    "temperatura_gruntu": ("ground_temperature", "°C", -90, 80),
}
SYNOP_FIELDS = {
    "temperatura": METEO_FIELDS["temperatura_powietrza"],
    "wilgotnosc_wzgledna": METEO_FIELDS["wilgotnosc_wzgledna"],
    "predkosc_wiatru": ("wind_speed_ms", "m/s", 0, 120),
    "kierunek_wiatru": METEO_FIELDS["wiatr_kierunek"],
    "suma_opadu": ("precip_sum_mm", "mm", 0, 1000),
    "cisnienie": ("pressure_hpa", "hPa", 800, 1100),
}


def number(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError("invalid number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("nonfinite number")
    return result


def source_time(value: object, timezone: str | None) -> datetime:
    if not timezone:
        raise ValueError("source timezone unverified")
    if not isinstance(value, str):
        raise ValueError("missing source timestamp")
    naive = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    zone = ZoneInfo(timezone)
    first, second = naive.replace(tzinfo=zone, fold=0), naive.replace(tzinfo=zone, fold=1)
    if first.utcoffset() != second.utcoffset():
        raise ValueError("ambiguous or nonexistent source time")
    return first.astimezone(UTC)


def normalize(
    row: dict, dataset: str, *, fetched_at: datetime, timezone: str | None
) -> tuple[dict, list[dict], list[str]]:
    if dataset not in ("synop", "meteo") or not isinstance(row, dict):
        raise ValueError("unknown dataset or station shape")
    sid, name = ("id_stacji", "stacja") if dataset == "synop" else ("kod_stacji", "nazwa_stacji")
    if not isinstance(row.get(sid), str) or not row[sid].isdigit() or len(row[sid]) > 50:
        raise ValueError("invalid station id")
    if not isinstance(row.get(name), str) or not row[name].strip():
        raise ValueError("missing station name")
    station = {
        "source_id": "imgw_" + dataset,
        "station_id": row[sid],
        "name": row[name],
        "latitude": None,
        "longitude": None,
        "elevation_m": None,
    }
    if dataset == "meteo":
        lat, lon = number(row.get("lat")), number(row.get("lon"))
        if lat is None or lon is None or not (48 <= lat <= 56 and 13 <= lon <= 25):
            raise ValueError("invalid station coordinates")
        station.update(latitude=lat, longitude=lon, elevation_m=number(row.get("wysokosc_npm")))
    fields = SYNOP_FIELDS if dataset == "synop" else METEO_FIELDS
    values, errors = [], []
    for field, (param, unit, lower, upper) in fields.items():
        try:
            if field not in row:
                raise ValueError("missing field")
            value = number(row[field])
            if value is None:
                continue
            if not lower <= value <= upper:
                raise ValueError("value out of bounds")
            raw_time = row.get(field + "_data")
            if dataset == "synop":
                raw_time = f"{row.get('data_pomiaru')} {int(row['godzina_pomiaru']):02}:00:00"
            observed = source_time(raw_time, timezone)
            if observed > fetched_at + timedelta(minutes=5):
                raise ValueError("future observation")
            if station["latitude"] is None:
                errors.append(f"{field}: station coordinates pending")
                continue
            values.append(
                {
                    "source_id": station["source_id"],
                    "station_id": station["station_id"],
                    "station_name": station["name"],
                    "latitude": station["latitude"],
                    "longitude": station["longitude"],
                    "param_code": param,
                    "value": value,
                    "unit": unit,
                    "observed_at": observed,
                    "fetched_at": fetched_at,
                    "source_record_id": f"{row[sid]}:{param}:{observed.isoformat()}",
                }
            )
        except (ValueError, KeyError, TypeError) as exc:
            errors.append(f"{field}: {exc}")
    return station, values, errors
