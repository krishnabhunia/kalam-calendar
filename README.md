# Kalam Calendar

Generates an `.ics` feed of **Rahu Kalam**, **Yamagandam** and **Gulika Kalam**
for any location, for subscription in Google Calendar (or Apple Calendar,
Outlook, anything that speaks iCalendar).

Currently configured for **Kolkata**.

---

## How it works

All three periods are the same calculation. The daylight span — sunrise to
sunset — is divided into eight equal parts, and each kalam occupies one of
those eighths. Which eighth depends only on the weekday.

Sunrise and sunset are therefore the *only* location-dependent inputs. Get
those right and the output matches any panchang site to within a minute or two.

| Weekday | Rahu Kalam | Yamagandam | Gulika Kalam |
|---|---|---|---|
| Sunday | 8th | 5th | 7th |
| Monday | 2nd | 4th | 6th |
| Tuesday | 7th | 3rd | 5th |
| Wednesday | 5th | 2nd | 4th |
| Thursday | 6th | 1st | 3rd |
| Friday | 4th | 7th | 2nd |
| Saturday | 3rd | 6th | 1st |

Because the eighth is a fraction of daylight rather than a fixed 90 minutes,
duration varies through the year — about 79 minutes at the winter solstice in
Kolkata and 100 minutes at the summer solstice.

---

## Changing location

Edit `CONFIG` at the top of `kalam_ics.py`:

```python
CONFIG = {
    "city": "Kolkata",
    "latitude": 22.5726,
    "longitude": 88.3639,
    "timezone": "Asia/Kolkata",
    ...
}
```

Or use a preset without editing anything:

```bash
python3 kalam_ics.py --city Bengaluru
```

Presets: Kolkata, Bhatpara, Bengaluru, Chennai, Mumbai, Delhi, Hyderabad,
London, New York.

---

## Sunrise convention — read this before comparing against a website

There are two definitions of sunrise, and they differ by about 4 minutes:

| Mode | Definition | Used by |
|---|---|---|
| `geometric` | Sun's **centre** at the horizon, refraction ignored | Drik Panchang, most panchang sites |
| `observational` | Sun's **upper limb** visible, refraction included | Google, weather apps, `astral` |

The default is `geometric`, so timings agree with Drik Panchang. If your
numbers look ~4 minutes off from some other source, this is why.

```bash
python3 kalam_ics.py --sunrise observational
```

---

## Usage

```bash
python3 kalam_ics.py                      # build kalam.ics from CONFIG
python3 kalam_ics.py --check 2026-08-05   # print one day, write nothing
python3 kalam_ics.py --years 5            # longer span
python3 kalam_ics.py --alarm 15           # 15-minute reminder on each event
python3 kalam_ics.py --city Chennai --out docs/chennai.ics
```

No third-party dependencies. Standard library only.

---

## Publishing and subscribing

1. Put `kalam_ics.py` and `solar.py` in a repo; output to `docs/kalam.ics`.
2. Settings → Pages → serve from `/docs` on `main`.
3. Copy `refresh-kalam.yml` into `.github/workflows/` so it rebuilds monthly.
4. Google Calendar → **Other calendars** → **+** → **From URL** →
   `https://<user>.github.io/<repo>/kalam.ics`

### Things to expect

- Google refreshes external feeds on its own schedule — often 12–48 hours,
  sometimes longer, and there is no way to force it. Irrelevant here, since
  the feed is published three years ahead.
- A subscribed calendar is **read-only**. You cannot edit individual events.
  If you want editable events, import the file instead of subscribing — use a
  dedicated calendar so cleanup is just deleting that calendar.
- Events are marked `TRANSP:TRANSPARENT`, so they never make you look busy.

---

## Accuracy

Sunrise/sunset use the NOAA solar position algorithm, implemented directly in
`solar.py`. Validated against the `astral` library across 728 consecutive days
at Kolkata: maximum deviation **27 seconds**.

`astral` is deliberately not used at runtime. Its date handling resolves
against the *UTC* date, which is ambiguous at longitudes where sunrise falls
near 00:00 UTC — all of India. It returns the wrong day's sunrise for some
dates and raises outright on others (e.g. 2027-04-05 at Kolkata). The NOAA
implementation works in local civil date and has no such failure mode.
