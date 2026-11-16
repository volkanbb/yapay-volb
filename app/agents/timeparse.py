"""Turkish / English natural-language schedule parser.

    "10 dakika sonra bana çayı hatırlat"        → reminder in 10 min
    "yarın saat 9'da YouTube Music'i aç"        → command tomorrow 09:00
    "her gün 08:30'da yapay zekâ haberlerini araştır" → daily command
    "cuma akşam 8'de bana maçı hatırlat"         → reminder next Friday 20:00
    "12 kasım 14:00'te toplantıyı hatırlat"      → reminder on a date
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass

from ..computer.actions import tr_lower

MONTHS = {"ocak": 1, "şubat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "haziran": 6, "temmuz": 7, "ağustos": 8,
          "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12,
          "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7, "august": 8,
          "september": 9, "october": 10, "november": 11, "december": 12}
WEEKDAYS = {"pazartesi": 0, "salı": 1, "çarşamba": 2, "perşembe": 3, "cuma": 4, "cumartesi": 5, "pazar": 6,
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}
UNITS = {"saniye": 1, "sn": 1, "second": 1, "seconds": 1, "dakika": 60, "dk": 60, "minute": 60, "minutes": 60,
         "saat": 3600, "sa": 3600, "hour": 3600, "hours": 3600, "gün": 86400, "day": 86400, "days": 86400}
SFX = r"(?:'|’)?(?:da|de|ta|te|dan|den|tan|ten|ya|ye|a|e)?"   # 9'da, 15:30'da, 10'a …
WD = "|".join(sorted(WEEKDAYS, key=len, reverse=True))
MON = "|".join(sorted(MONTHS, key=len, reverse=True))


@dataclass
class ScheduleSpec:
    run_at: dt.datetime
    repeat: str            # "" | "daily" | "weekdays" | "weekly" | "hourly"
    kind: str              # "reminder" | "command"
    text: str              # reminder message or command to run
    weekday: int | None = None

    def describe(self) -> str:
        when = self.run_at.strftime("%d.%m.%Y %H:%M")
        rep = {"daily": "her gün ", "weekdays": "hafta içi her gün ", "weekly": "her hafta ",
               "hourly": "her saat "}.get(self.repeat, "")
        what = f"hatırlatma: {self.text}" if self.kind == "reminder" else f"komut: {self.text}"
        return f"{rep}{when} — {what}"


class _Text:
    """Lower-cased text for matching + original-case text for the payload, cut in lockstep."""

    def __init__(self, raw: str) -> None:
        self.orig = " " + raw.strip().rstrip(".!?") + " "
        self.low = tr_lower(self.orig)
        assert len(self.low) == len(self.orig)

    def cut(self, m: re.Match, insert: str = " ") -> str:
        self.low = self.low[:m.start()] + insert + self.low[m.end():]
        self.orig = self.orig[:m.start()] + insert + self.orig[m.end():]
        return self.low


def parse_schedule(text: str, now: dt.datetime | None = None) -> ScheduleSpec | None:
    now = now or dt.datetime.now()
    tx = _Text(text)
    t = tx.low
    if re.search(r"\bsaat kaç\b|\bwhat time\b", t):
        return None

    repeat = ""
    weekday: int | None = None
    day: dt.date | None = None
    hour: int | None = None
    minute = 0
    run_at: dt.datetime | None = None
    found = False

    # --- repetition ---------------------------------------------------------
    m = re.search(r"\b(?:hafta ?içi(?: her gün)?|her hafta ?içi|every weekday)\b", t)
    if m:
        repeat, t, found = "weekdays", tx.cut(m), True
    m = re.search(rf"\b(?:her|every)\s+({WD})\w*\b", t)
    if m:
        repeat, weekday, t, found = "weekly", WEEKDAYS[m.group(1)], tx.cut(m), True
    m = re.search(r"\b(?:her gün|hergün|her sabah|her akşam|every day|daily)\b", t)
    if m:
        if "sabah" in m.group(0):
            hour = 9
        if "akşam" in m.group(0):
            hour = 20
        ins = " sabah " if "sabah" in m.group(0) else " akşam " if "akşam" in m.group(0) else " "
        repeat, t, found = "daily", tx.cut(m, ins), True
    m = re.search(r"\b(?:her saat başı|her saat|every hour|hourly)\b", t)
    if m:
        repeat, t, found = "hourly", tx.cut(m), True

    # --- relative: "10 dakika sonra", "in 2 hours" -----------------------------
    m = re.search(r"\b(\d+|bir|yarım)\s*(saniye|sn|dakika|dk|saat|sa|gün)\s*sonra\b", t) or \
        re.search(r"\bin\s+(\d+|an|a)\s+(seconds?|minutes?|hours?|days?)\b", t)
    if m:
        qty_raw = m.group(1)
        qty = 0.5 if qty_raw == "yarım" else 1 if qty_raw in ("bir", "an", "a") else int(qty_raw)
        run_at = now + dt.timedelta(seconds=qty * UNITS[m.group(2)])
        run_at = run_at.replace(microsecond=0)
        t, found = tx.cut(m), True
    m = re.search(r"\b(?:yarım saat|half an hour) sonra\b", t)
    if m and run_at is None:
        run_at, t, found = now.replace(microsecond=0) + dt.timedelta(minutes=30), tx.cut(m), True

    # --- day ------------------------------------------------------------------
    m = re.search(r"\b(yarından sonra|öbür gün|yarın|bugün|bu akşam|bu gece|tomorrow|today|tonight)\w*\b", t)
    if m:
        w = m.group(1)
        offset = 2 if w in ("yarından sonra", "öbür gün") else 1 if w in ("yarın", "tomorrow") else 0
        day = (now + dt.timedelta(days=offset)).date()
        if w in ("bu akşam", "tonight"):
            hour = hour if hour is not None else 20
        if w == "bu gece":
            hour = hour if hour is not None else 22
        t, found = tx.cut(m), True
    m = re.search(rf"\b(\d{{1,2}})\s+({MON})\w*(?:\s+(\d{{4}}))?\b", t)
    if m:
        year = int(m.group(3)) if m.group(3) else now.year
        try:
            day = dt.date(year, MONTHS[m.group(2)], int(m.group(1)))
            if day < now.date() and not m.group(3):
                day = day.replace(year=year + 1)
            t, found = tx.cut(m), True
        except ValueError:
            pass
    m = re.search(r"\b(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?\b(?![:.]\d)", t)
    if m and day is None and not re.search(rf"{re.escape(m.group(0))}\s*(?:'|’)?(?:da|de|te|ta)\b", t):
        try:
            year = int(m.group(3)) if m.group(3) else now.year
            year += 2000 if year < 100 else 0
            day = dt.date(year, int(m.group(2)), int(m.group(1)))
            t, found = tx.cut(m), True
        except ValueError:
            pass
    if weekday is None:
        m = re.search(rf"\b(?:(?:bu|gelecek|önümüzdeki|next|on)\s+)?({WD})\w*\b", t)
        if m:
            weekday, t, found = WEEKDAYS[m.group(1)], tx.cut(m), True

    # --- time of day ------------------------------------------------------------
    part = None
    m = re.search(r"\b(sabah|öğleden sonra|öğlen|öğle|akşam|gece|morning|afternoon|evening|night)\b", t)
    if m:
        part = m.group(1)
        t = tx.cut(m)
    patterns = [rf"\b(?:saat\s*)?(\d{{1,2}})[:.](\d{{2}}){SFX}\b",   # 15:30, saat 9.15'te
                rf"\bsaat\s*(\d{{1,2}}){SFX}\b",                       # saat 9'da
                r"\b(\d{1,2})(?:'|’)(?:da|de|ta|te)\b",                 # 9'da
                r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b"]          # at 9 pm
    if part:
        patterns.append(rf"\b(\d{{1,2}}){SFX}\b")                     # akşam 8
    m = None
    for pat in patterns:
        m = re.search(pat, t)
        if m:
            break
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2)) if (m.lastindex or 0) >= 2 and m.group(2) else 0
        if (m.lastindex or 0) >= 3 and m.group(3) == "pm" and hour < 12:
            hour += 12
        t, found = tx.cut(m), True
    if part:
        found = True
        if hour is None:
            hour = {"sabah": 9, "morning": 9, "öğlen": 12, "öğle": 12, "öğleden sonra": 15, "afternoon": 15,
                    "akşam": 20, "evening": 20, "gece": 22, "night": 22}[part]
        elif part in ("akşam", "evening", "öğleden sonra", "afternoon") and hour < 12:
            hour += 12
        elif part in ("gece", "night") and 6 <= hour < 12:
            hour += 12

    if not found:
        return None
    time_given = run_at is not None or hour is not None or part is not None
    if not time_given and not repeat and day == now.date() and weekday is None:
        return None  # "bugün X'i araştır" means now, not a schedule
    if hour is not None and not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None

    # --- resolve the moment -----------------------------------------------------
    if run_at is None:
        h = hour if hour is not None else (9 if day or weekday is not None else None)
        if h is None and repeat == "hourly":
            run_at = (now + dt.timedelta(hours=1)).replace(minute=minute, second=0, microsecond=0)
        elif h is None:
            return None
        else:
            if day is None and weekday is not None:
                delta = (weekday - now.weekday()) % 7
                day = (now + dt.timedelta(days=delta)).date()
            base_day = day or now.date()
            run_at = dt.datetime.combine(base_day, dt.time(h, minute))
            if run_at <= now:
                if day is not None and weekday is None and not repeat:
                    if run_at < now - dt.timedelta(minutes=1):
                        return None  # explicit date/time already in the past
                else:
                    step = 7 if weekday is not None else 1
                    while run_at <= now:
                        run_at += dt.timedelta(days=step)
            if repeat == "weekdays":
                while run_at.weekday() >= 5:
                    run_at += dt.timedelta(days=1)

    # --- what to do -------------------------------------------------------------
    from .intent import strip_wake_word
    _, orig_rest = strip_wake_word(re.sub(r"\s+", " ", tx.orig).strip(" ,."))
    orig_rest = re.sub(r"^(?:ve|and|o zaman|then)\s+", "", orig_rest, flags=re.I).strip(" ,.")
    rest = tr_lower(orig_rest)
    m = re.match(r"^(?:bana\s+|beni\s+)?(.*?)\s*(?:diye\s+)?(?:hatırlat\w*|uyar\w*|remind me(?: to| about)?)\s*(.*)$", rest)
    if m and ("hatırlat" in rest or "uyar" in rest or "remind" in rest):
        g = 1 if m.group(1).strip() else 2
        msg = orig_rest[m.start(g):m.end(g)].strip()
        msg = re.sub(r"(?:'|’)?(?:yı|yi|yu|yü|ı|i|u|ü)$", "", msg) if msg.endswith(("'ı", "'i", "'u", "'ü")) else msg
        msg = re.sub(r"^(?:bana|beni)\s+", "", msg).strip() or "Hatırlatma"
        return ScheduleSpec(run_at, repeat, "reminder", msg, weekday)
    if not rest:
        return ScheduleSpec(run_at, repeat, "reminder", "Hatırlatma", weekday)
    return ScheduleSpec(run_at, repeat, "command", orig_rest, weekday)


def next_occurrence(run_at: dt.datetime, repeat: str, now: dt.datetime) -> dt.datetime | None:
    if not repeat:
        return None
    step = {"hourly": dt.timedelta(hours=1), "daily": dt.timedelta(days=1), "weekdays": dt.timedelta(days=1),
            "weekly": dt.timedelta(days=7)}[repeat]
    nxt = run_at + step
    while nxt <= now or (repeat == "weekdays" and nxt.weekday() >= 5):
        nxt += step
    return nxt
