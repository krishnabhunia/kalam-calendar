"""
solar.py — sunrise/sunset via the NOAA solar position algorithm.

Self-contained and deterministic. Works directly in LOCAL civil date, so
there is none of the UTC-date-boundary ambiguity that bites at longitudes
where sunrise falls near 00:00 UTC (all of India, for instance).

zenith 90.000  -> geometric   (Sun's centre at horizon, no refraction)
zenith 90.833  -> observational (upper limb, standard refraction)
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

ZENITH_GEOMETRIC = 90.0
ZENITH_OBSERVATIONAL = 90.833


def _julian_day(d: date) -> float:
    y, m, day = d.year, d.month, d.day
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return (math.floor(365.25 * (y + 4716))
            + math.floor(30.6001 * (m + 1))
            + day + b - 1524.5)


def _solar_terms(jc: float):
    """Return (declination_deg, equation_of_time_minutes) for Julian century jc."""
    geom_mean_long = (280.46646 + jc * (36000.76983 + jc * 0.0003032)) % 360
    geom_mean_anom = 357.52911 + jc * (35999.05029 - 0.0001537 * jc)
    eccent = 0.016708634 - jc * (0.000042037 + 0.0000001267 * jc)

    m_rad = math.radians(geom_mean_anom)
    sun_eq_ctr = (math.sin(m_rad) * (1.914602 - jc * (0.004817 + 0.000014 * jc))
                  + math.sin(2 * m_rad) * (0.019993 - 0.000101 * jc)
                  + math.sin(3 * m_rad) * 0.000289)

    true_long = geom_mean_long + sun_eq_ctr
    omega = 125.04 - 1934.136 * jc
    app_long = true_long - 0.00569 - 0.00478 * math.sin(math.radians(omega))

    mean_obliq = (23 + (26 + ((21.448 - jc * (46.815 + jc * (0.00059 - jc * 0.001813)))) / 60) / 60)
    obliq_corr = mean_obliq + 0.00256 * math.cos(math.radians(omega))

    declination = math.degrees(math.asin(
        math.sin(math.radians(obliq_corr)) * math.sin(math.radians(app_long))))

    var_y = math.tan(math.radians(obliq_corr / 2)) ** 2
    eq_time = 4 * math.degrees(
        var_y * math.sin(2 * math.radians(geom_mean_long))
        - 2 * eccent * math.sin(m_rad)
        + 4 * eccent * var_y * math.sin(m_rad) * math.cos(2 * math.radians(geom_mean_long))
        - 0.5 * var_y * var_y * math.sin(4 * math.radians(geom_mean_long))
        - 1.25 * eccent * eccent * math.sin(2 * m_rad))

    return declination, eq_time


def sun_times(d: date, latitude: float, longitude: float, tzname: str,
              zenith: float = ZENITH_GEOMETRIC):
    """Return (sunrise, sunset) as tz-aware datetimes on local civil date d."""
    tz = ZoneInfo(tzname)
    # UTC offset in hours for this location on this date
    offset_hours = (datetime(d.year, d.month, d.day, 12, tzinfo=tz)
                    .utcoffset().total_seconds() / 3600)

    # Iterate twice: solar terms depend slightly on the time of day
    noon_frac = 0.5
    for _ in range(2):
        jd = _julian_day(d) + (noon_frac - offset_hours / 24)
        jc = (jd - 2451545.0) / 36525.0
        decl, eq_time = _solar_terms(jc)
        # Local solar noon, in minutes after local midnight
        noon_min = 720 - 4 * longitude - eq_time + offset_hours * 60
        noon_frac = noon_min / 1440

    lat_r, decl_r = math.radians(latitude), math.radians(decl)
    cos_ha = ((math.cos(math.radians(zenith)) - math.sin(lat_r) * math.sin(decl_r))
              / (math.cos(lat_r) * math.cos(decl_r)))
    if cos_ha > 1:
        raise ValueError(f"Sun never rises on {d} at latitude {latitude}")
    if cos_ha < -1:
        raise ValueError(f"Sun never sets on {d} at latitude {latitude}")

    ha_min = 4 * math.degrees(math.acos(cos_ha))   # half-day arc, minutes

    midnight = datetime(d.year, d.month, d.day, tzinfo=tz)
    sunrise = midnight + timedelta(minutes=noon_min - ha_min)
    sunset = midnight + timedelta(minutes=noon_min + ha_min)
    return sunrise, sunset
