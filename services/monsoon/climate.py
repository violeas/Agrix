"""Attributable global climate index feeds. Index signals are context, not local rainfall forecasts."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from functools import lru_cache
import re
from urllib.request import Request, urlopen

from services.monsoon.providers import APP_USER_AGENT, TIMEOUT_SECONDS


def _read_text(url):
    request = Request(url, headers={"User-Agent": APP_USER_AGENT})
    with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.read().decode("utf-8", errors="replace")


def _period_end(season, year):
    months = {"DJF": 2, "JFM": 3, "FMA": 4, "MAM": 5, "AMJ": 6,
              "MJJ": 7, "JJA": 8, "JAS": 9, "ASO": 10, "SON": 11,
              "OND": 12, "NDJ": 1}
    month = months.get(season, 1)
    if season == "NDJ":
        year += 1
    return date(year, month, 1)


@lru_cache(maxsize=32)
def _enso(cache_day=None):
    url = "https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt"
    lines = _read_text(url).splitlines()
    rows = []
    for line in lines:
        match = re.match(r"\s*(DJF|JFM|FMA|MAM|AMJ|MJJ|JJA|JAS|ASO|SON|OND|NDJ)\s+(\d{4})\s+(-?\d+(?:\.\d+)?)", line)
        if match:
            season, year, raw = match.groups()
            rows.append((date(*(_period_end(season, int(year)).timetuple()[:3])), float(raw), season, int(year)))
    if not rows:
        raise ValueError("NOAA CPC RONI feed had no usable rows")
    observed, value, season, year = rows[-1]
    freshness = (date.today() - observed).days
    state = "El Niño-like" if value >= .5 else "La Niña-like" if value <= -.5 else "Near neutral"
    return {"name": "ENSO", "value": value, "unit": "°C", "signal": state,
            "phase": f"RONI {season} {year}", "observed_date": observed.isoformat(),
            "status": "Current index feed" if freshness <= 70 else "Latest available index is dated",
            "freshness_days": freshness, "source": "NOAA CPC Relative Oceanic Niño Index (RONI)",
            "source_url": url, "impact": "Global Pacific background signal only; this app does not convert it into a local rainfall adjustment.",
            "confidence": "Index observation; local impact not calibrated"}


@lru_cache(maxsize=32)
def _iod(cache_day=None):
    url = "https://psl.noaa.gov/data/timeseries/month/data/dmi.had.long.csv"
    lines = _read_text(url).splitlines()
    rows = []
    for line in lines[1:]:
        match = re.match(r"\s*(\d{4})-(\d{2})-\d{2}\s*,\s*(-?\d+(?:\.\d+)?)", line)
        if match:
            year, month, raw = match.groups()
            value = float(raw)
            if value > -9000:
                rows.append((date(int(year), int(month), 1), value))
    if not rows:
        raise ValueError("NOAA PSL DMI feed had no recent usable value")
    observed, value = rows[-1]
    age = (date.today() - observed).days
    return {"name": "IOD", "value": value, "unit": "°C", "signal": "Positive" if value >= .4 else "Negative" if value <= -.4 else "Near neutral",
            "phase": "Dipole Mode Index", "observed_date": observed.isoformat(),
            "status": "Current monthly index" if age <= 75 else "Latest available index is dated",
            "freshness_days": age, "source": "NOAA PSL Dipole Mode Index (HadISST)",
            "source_url": url, "impact": "Indian Ocean SST-gradient signal; this app does not convert it into a local rainfall adjustment.",
            "confidence": "Index observation; local impact not calibrated"}


@lru_cache(maxsize=32)
def _mjo(cache_day=None):
    url = "https://www.bom.gov.au/clim_data/IDCKGEM000/rmm.74toRealtime.txt"
    lines = _read_text(url).splitlines()
    rows = []
    for line in lines:
        match = re.match(r"\s*(\d{4})\s+(\d{1,2})\s+(\d{1,2})\s+(-?\d+(?:\.\d+)?(?:E[+-]?\d+)?)\s+(-?\d+(?:\.\d+)?(?:E[+-]?\d+)?)\s+(\d+)\s+(-?\d+(?:\.\d+)?(?:E[+-]?\d+)?)", line, re.I)
        if match:
            year, month, day, rmm1, rmm2, phase, amplitude = match.groups()
            amplitude = float(amplitude)
            if amplitude < 1e30:
                rows.append((date(int(year), int(month), int(day)), int(phase), amplitude, float(rmm1), float(rmm2)))
    if not rows:
        raise ValueError("BOM MJO feed had no usable rows")
    observed, phase, amplitude, rmm1, rmm2 = rows[-1]
    age = (date.today() - observed).days
    return {"name": "MJO", "value": phase, "unit": "phase", "signal": f"Phase {phase} · {'active' if amplitude >= 1 else 'weak'} amplitude",
            "phase": phase, "amplitude": round(amplitude, 2), "rmm1": round(rmm1, 2), "rmm2": round(rmm2, 2),
            "observed_date": observed.isoformat(), "status": "Recent daily index" if age <= 5 else "Latest available index is dated",
            "freshness_days": age, "source": "Australian Bureau of Meteorology RMM index",
            "source_url": url, "impact": "Tropical intraseasonal signal; location-specific rainfall influence is not estimated here.",
            "confidence": "Index observation; local impact not calibrated"}


def _safe(fetch, name, source):
    try:
        return fetch()
    except Exception as error:
        return {"name": name, "value": None, "signal": "Data unavailable",
                "status": "Data unavailable", "observed_date": None, "source": source,
                "confidence": "Unavailable", "error": str(error)[:160]}


def current_climate_drivers():
    cache_day = date.today().isoformat()
    jobs = [(lambda: _enso(cache_day), "ENSO", "NOAA CPC RONI"),
            (lambda: _iod(cache_day), "IOD", "NOAA PSL DMI"),
            (lambda: _mjo(cache_day), "MJO", "Australian Bureau of Meteorology RMM")]
    with ThreadPoolExecutor(max_workers=3) as pool:
        drivers = list(pool.map(lambda job: _safe(*job), jobs))
    return {"available": any(item.get("value") is not None for item in drivers),
            "status": "Real climate indices; no local rainfall relationship has been applied.",
            "drivers": drivers}
