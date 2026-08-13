#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gate.py — Mum tarama işini SADECE gerektiği günlerde tetiklemek için kontrol.

Mevcut tarama scriptlerine (xutum_tarama_*.py, mum_tarama_*.py) HİÇBİR
DOKUNUŞ YAPILMAZ. Bu dosya sadece "bugün BIST'in haftanın/ayın son işlem
günü mü?" sorusuna XIST resmi takvimiyle (exchange_calendars) cevap verir.

GitHub Actions içinde şöyle kullanılır:
    python gate.py >> "$GITHUB_OUTPUT"

Çıktı satırları:
    today_is_session=true/false
    week_end=true/false
    month_end=true/false
"""
import sys
import subprocess
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def _ensure(pkg, import_name=None):
    import_name = import_name or pkg
    try:
        __import__(import_name)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])


_ensure("pandas")
_ensure("exchange_calendars")

import pandas as pd
import exchange_calendars as xcals

IST = ZoneInfo("Europe/Istanbul")


def xist_takvim():
    bugun = datetime.now(IST).date()
    basla = bugun - timedelta(days=30)
    bitir = bugun + timedelta(days=30)
    return xcals.get_calendar("XIST", start=str(basla), end=str(bitir))


def main():
    cal = xist_takvim()
    bugun = pd.Timestamp(datetime.now(IST).date())

    if not cal.is_session(bugun):
        print("today_is_session=false")
        print("week_end=false")
        print("month_end=false")
        return

    sessions = pd.DatetimeIndex(cal.sessions).tz_localize(None)

    week_key = bugun.to_period("W-FRI")
    week_sessions = sessions[sessions.to_period("W-FRI") == week_key]
    week_end = bool(bugun == week_sessions.max())

    month_key = bugun.to_period("M")
    month_sessions = sessions[sessions.to_period("M") == month_key]
    month_end = bool(bugun == month_sessions.max())

    print("today_is_session=true")
    print(f"week_end={'true' if week_end else 'false'}")
    print(f"month_end={'true' if month_end else 'false'}")


if __name__ == "__main__":
    main()
