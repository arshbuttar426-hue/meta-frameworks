#!/usr/bin/env python3
"""Fetch real-time planetary data with exact coordinates."""

import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

PLANET_COMMANDS = {
    "mercury": "199",
    "venus": "299",
    "earth": "399",
    "mars": "499",
    "jupiter": "599",
    "saturn": "699",
    "uranus": "799",
    "neptune": "899",
    "pluto": "999",
}


def _http_get(url: str, params: dict[str, str]) -> str:
    query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    full_url = f"{url}?{query}"
    with urllib.request.urlopen(full_url, timeout=30) as response:
        return response.read().decode("utf-8")


def _normalize_body(body: str) -> str:
    normalized = body.strip().lower()
    return PLANET_COMMANDS.get(normalized, body)


def fetch_planetary_data(
    body: str,
    latitude: float,
    longitude: float,
    elevation: float = 0.0,
    when: datetime | None = None,
) -> dict[str, Any]:
    """Fetch planetary coordinates for a real observer location.

    Uses the JPL Horizons web API to request an observer ephemeris for the target body.
    Returns the raw Horizons JSON payload.
    """
    when = when or datetime.now(timezone.utc)
    target = _normalize_body(body)

    start_time = when.strftime("%Y-%m-%d %H:%M")
    stop_time = (when.replace(hour=when.hour + 1) if when.hour < 23 else when.replace(hour=0, day=when.day + 1)).strftime("%Y-%m-%d %H:%M")

    params = {
        "format": "json",
        "COMMAND": f"'{target}'",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "OBSERVER",
        "CENTER": "coord@399",
        "COORD_TYPE": "GEODETIC",
        "SITE_COORD": f"'{longitude},{latitude},{elevation}'",
        "START_TIME": f"'{start_time}'",
        "STOP_TIME": f"'{stop_time}'",
        "STEP_SIZE": "'1h'",
        "REF_PLANE": "ECLIPTIC",
        "ANG_FORMAT": "HMS",
        "APPARENT": "AIRLESS",
    }

    raw = _http_get("https://ssd.jpl.nasa.gov/api/horizons.api", params)
    return json.loads(raw)


def parse_coordinates(result: dict[str, Any]) -> dict[str, Any]:
    """Parse the text result from Horizons into a structured record."""
    text = result.get("result", "")
    lines = text.splitlines()
    data_lines: list[str] = []
    in_data_section = False

    for line in lines:
        if "$$SOE" in line:
            in_data_section = True
            continue
        if "$$EOE" in line:
            in_data_section = False
            break
        if in_data_section and line.strip():
            data_lines.append(line)

    if not data_lines:
        return {"raw": text[:500], "error": "No data section found"}

    # Parse the last data line
    last_line = data_lines[-1]
    parts = last_line.split()

    if len(parts) < 20:
        return {"raw": last_line, "error": f"Not enough fields: {len(parts)}"}

    return {
        "datetime_utc": parts[0] + " " + parts[1],
        "right_ascension": f"{parts[3]}h {parts[4]}m {parts[5]}s",
        "declination": f"{parts[6]} {parts[7]}° {parts[8]}'",
        "azimuth_deg": float(parts[15]),
        "elevation_deg": float(parts[16]),
        "distance_km": float(parts[17]),
    }


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if len(argv) < 3:
        print(
            "Usage: python fetch.py <planet> <latitude> <longitude> [elevation_meters]",
            file=sys.stderr,
        )
        return 1

    body = argv[0]
    latitude = float(argv[1])
    longitude = float(argv[2])
    elevation = float(argv[3]) if len(argv) > 3 else 0.0

    result = fetch_planetary_data(body, latitude, longitude, elevation)
    parsed = parse_coordinates(result)

    output: dict[str, Any] = {
        "body": body,
        "observer": {
            "latitude": latitude,
            "longitude": longitude,
            "elevation_m": elevation,
        },
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "result": parsed,
    }

    with open("fetch_dump.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"Data saved to fetch_dump.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
