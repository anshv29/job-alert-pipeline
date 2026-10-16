import html
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from jobalert.settings import get_settings

TIMEOUT = 20
HEADERS = {"User-Agent": "Mozilla/5.0 (job-alert-pipeline)"}


def get_json(url, **kwargs):
    r = requests.get(url, timeout=TIMEOUT, headers=HEADERS, **kwargs)
    r.raise_for_status()
    return r.json()


def strip_html(raw):
    text = html.unescape(raw or "")
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()


def _fmt(dt):
    return dt.astimezone(ZoneInfo(get_settings()["timezone"])).strftime("%Y-%m-%d")


def fmt_iso(value):
    if not value:
        return "Unknown"
    try:
        return _fmt(datetime.fromisoformat(value.replace("Z", "+00:00")))
    except ValueError:
        return value


def fmt_unix(value, millis=False):
    if not value:
        return "Unknown"
    return _fmt(datetime.fromtimestamp(value / (1000 if millis else 1), tz=ZoneInfo("UTC")))
