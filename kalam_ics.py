#!/usr/bin/env python3
"""
kalam_ics.py — generate an .ics calendar of Rahu Kalam, Yamagandam and
Gulika Kalam for a given location.

All three are the same calculation: the daylight span (sunrise -> sunset) is
divided into eight equal parts, and each kalam occupies one of those eighths.
Which eighth depends only on the weekday. Nothing else is location-dependent,
so sunrise/sunset for your coordinates is the sole input that matters.

Usage:
    python3 kalam_ics.py                  # uses CONFIG below
    python3 kalam_ics.py --years 3        # override span
    python3 kalam_ics.py --check 2026-08-05   # print one day, no file
"""

from __future__ import annotations

import argparse
import hashlib
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from solar import sun_times, ZENITH_GEOMETRIC, ZENITH_OBSERVATIONAL

# ---------------------------------------------------------------------------
# CONFIG — edit these to change location. Nothing below needs to change.
# ---------------------------------------------------------------------------

CONFIG = {
    "city": "Kolkata",
    "region": "West Bengal, India",
    "latitude": 22.5726,
    "longitude": 88.3639,
    "timezone": "Asia/Kolkata",
    "years_ahead": 3,
    "output": "kalam.ics",
    # "geometric"     = Sun's centre at horizon, no refraction. What Drik
    #                   Panchang uses. Pick this if you cross-check there.
    # "observational" = upper limb visible, refraction included. What weather
    #                   apps and Google show. ~4 min later sunrise.
    "sunrise_mode": "geometric",
    # Which kalams to emit
    "include": ["Rahu Kalam", "Yamagandam", "Gulika Kalam"],
    # Minutes before start to alert. None = no alarm (recommended for a
    # subscribed feed; you can add reminders per-event if you import instead).
    "alarm_minutes": None,
    # Mark events as free so they never block your availability
    "transparent": True,
}

# Some presets, for convenience when you move or travel.
PRESETS = {
    "Kolkata":   (22.5726, 88.3639, "Asia/Kolkata"),
    "Bhatpara":  (22.8664, 88.4011, "Asia/Kolkata"),
    "Bengaluru": (12.9716, 77.5946, "Asia/Kolkata"),
    "Chennai":   (13.0827, 80.2707, "Asia/Kolkata"),
    "Mumbai":    (19.0760, 72.8777, "Asia/Kolkata"),
    "Delhi":     (28.6139, 77.2090, "Asia/Kolkata"),
    "Hyderabad": (17.3850, 78.4867, "Asia/Kolkata"),
    "London":    (51.5074, -0.1278, "Europe/London"),
    "New York":  (40.7128, -74.0060, "America/New_York"),
}

# ---------------------------------------------------------------------------
# Weekday -> which eighth of the daylight span (1-indexed)
# Python weekday(): Mon=0 ... Sun=6
# ---------------------------------------------------------------------------

SEGMENT = {
    #             Mon Tue Wed Thu Fri Sat Sun
    "Rahu Kalam":  [2,  7,  5,  6,  4,  3,  8],
    "Yamagandam":  [4,  3,  2,  1,  7,  6,  5],
    "Gulika Kalam":[6,  5,  4,  3,  2,  1,  7],
}

NOTE = {
    "Rahu Kalam":   "Period ruled by Rahu. Traditionally avoided for beginning new work.",
    "Yamagandam":   "Period ruled by Yama. Traditionally avoided for auspicious beginnings.",
    "Gulika Kalam": "Period ruled by Gulika (son of Shani). Considered inauspicious for new ventures.",
}


def daylight_segment(d: date, cfg: dict, segment_index: int):
    """Return (start, end, sunrise, sunset) for the nth eighth of daylight."""
    zenith = (ZENITH_GEOMETRIC if cfg.get("sunrise_mode", "geometric") == "geometric"
              else ZENITH_OBSERVATIONAL)
    sunrise, sunset = sun_times(d, cfg["latitude"], cfg["longitude"],
                                cfg["timezone"], zenith)
    eighth = (sunset - sunrise) / 8
    start = sunrise + eighth * (segment_index - 1)
    return start, start + eighth, sunrise, sunset


def ical_escape(text: str) -> str:
    return (text.replace("\\", "\\\\")
                .replace(";", "\\;")
                .replace(",", "\\,")
                .replace("\n", "\\n"))


def fold(line: str) -> str:
    """RFC 5545 requires lines <= 75 octets; continuation lines start with a space."""
    out, raw = [], line.encode("utf-8")
    limit = 73
    while len(raw) > limit:
        cut = limit
        while cut > 0 and (raw[cut] & 0xC0) == 0x80:   # don't split a UTF-8 char
            cut -= 1
        out.append(raw[:cut].decode("utf-8"))
        raw = raw[cut:]
        limit = 72
    out.append(raw.decode("utf-8"))
    return "\r\n ".join(out)


def utc_stamp(dt: datetime) -> str:
    return dt.astimezone(ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%SZ")


def build_calendar(cfg: dict) -> str:
    tz = ZoneInfo(cfg["timezone"])
    today = datetime.now(tz).date()
    end_date = today + timedelta(days=365 * cfg["years_ahead"])
    now = datetime.now(ZoneInfo("UTC"))

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//kalam_ics//Panchang Kalam Timings//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:Kalam Timings — {cfg['city']}",
        f"X-WR-CALDESC:Rahu Kalam\\, Yamagandam and Gulika Kalam for {cfg['city']}",
        f"X-WR-TIMEZONE:{cfg['timezone']}",
        "REFRESH-INTERVAL;VALUE=DURATION:P1D",
        "X-PUBLISHED-TTL:P1D",
    ]

    d = today
    count = 0
    while d <= end_date:
        wd = d.weekday()
        for name in cfg["include"]:
            idx = SEGMENT[name][wd]
            start, finish, sunrise, sunset = daylight_segment(d, cfg, idx)

            uid_seed = f"{name}|{d.isoformat()}|{cfg['city']}"
            uid = hashlib.sha1(uid_seed.encode()).hexdigest()[:20] + "@kalam-ics"

            desc = (
                f"{NOTE[name]}\n\n"
                f"{start.strftime('%I:%M %p').lstrip('0')} – "
                f"{finish.strftime('%I:%M %p').lstrip('0')} "
                f"({int((finish - start).total_seconds() // 60)} min)\n"
                f"Sunrise {sunrise.strftime('%I:%M %p').lstrip('0')} · "
                f"Sunset {sunset.strftime('%I:%M %p').lstrip('0')}\n"
                f"Segment {idx} of 8 · {cfg['city']}"
            )

            ev = [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{utc_stamp(now)}",
                f"DTSTART:{utc_stamp(start)}",
                f"DTEND:{utc_stamp(finish)}",
                f"SUMMARY:{ical_escape(name)}",
                f"DESCRIPTION:{ical_escape(desc)}",
                f"LOCATION:{ical_escape(cfg['city'])}",
                "CATEGORIES:Panchang",
            ]
            if cfg["transparent"]:
                ev.append("TRANSP:TRANSPARENT")
            if cfg["alarm_minutes"] is not None:
                ev += [
                    "BEGIN:VALARM",
                    "ACTION:DISPLAY",
                    f"DESCRIPTION:{ical_escape(name)} starts soon",
                    f"TRIGGER:-PT{cfg['alarm_minutes']}M",
                    "END:VALARM",
                ]
            ev.append("END:VEVENT")
            lines += ev
            count += 1
        d += timedelta(days=1)

    lines.append("END:VCALENDAR")
    print(f"  {count} events · {today} → {end_date}")
    return "\r\n".join(fold(l) for l in lines) + "\r\n"


def check_day(day: str, cfg: dict) -> None:
    d = date.fromisoformat(day)
    print(f"\n{d.strftime('%A, %d %B %Y')} — {cfg['city']}")
    _, _, sunrise, sunset = daylight_segment(d, cfg, 1)
    span = sunset - sunrise
    print(f"  Sunrise {sunrise.strftime('%I:%M %p')} · Sunset {sunset.strftime('%I:%M %p')} "
          f"· daylight {span.seconds // 3600}h{(span.seconds % 3600) // 60:02d}m "
          f"· eighth = {span.seconds // 8 // 60} min\n")
    for name in SEGMENT:
        idx = SEGMENT[name][d.weekday()]
        s, e, _, _ = daylight_segment(d, cfg, idx)
        print(f"  {name:<14} seg {idx}   "
              f"{s.strftime('%I:%M %p').lstrip('0'):>9} – {e.strftime('%I:%M %p').lstrip('0')}")
    print()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--city", help=f"preset: {', '.join(PRESETS)}")
    p.add_argument("--years", type=int)
    p.add_argument("--out")
    p.add_argument("--check", metavar="YYYY-MM-DD",
                   help="print one day's timings and exit")
    p.add_argument("--alarm", type=int, help="minutes before start to alert")
    p.add_argument("--sunrise", choices=["geometric", "observational"])
    args = p.parse_args()

    cfg = dict(CONFIG)
    if args.city:
        if args.city not in PRESETS:
            raise SystemExit(f"Unknown preset. Choose from: {', '.join(PRESETS)}")
        lat, lon, tzname = PRESETS[args.city]
        cfg.update(city=args.city, latitude=lat, longitude=lon, timezone=tzname)
    if args.years:
        cfg["years_ahead"] = args.years
    if args.out:
        cfg["output"] = args.out
    if args.alarm is not None:
        cfg["alarm_minutes"] = args.alarm
    if args.sunrise:
        cfg["sunrise_mode"] = args.sunrise

    if args.check:
        check_day(args.check, cfg)
    else:
        print(f"Generating for {cfg['city']} ({cfg['latitude']}, {cfg['longitude']})")
        with open(cfg["output"], "w", encoding="utf-8", newline="") as f:
            f.write(build_calendar(cfg))
        print(f"  wrote {cfg['output']}")
