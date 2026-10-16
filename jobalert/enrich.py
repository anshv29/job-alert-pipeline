"""Swaps in the real posting text for jobs that only have a one line summary."""
import re

import requests

from jobalert.sources import ashby
from jobalert.sources.common import HEADERS, TIMEOUT, strip_html

_GREENHOUSE = re.compile(r"(?:boards|job-boards)(?:\.\w+)?\.greenhouse\.io/(?P<slug>[^/?#]+)/jobs/(?P<id>\d+)")
_LEVER = re.compile(r"jobs\.lever\.co/(?P<slug>[^/?#]+)/(?P<id>[0-9a-f-]{36})")
_ASHBY = re.compile(r"jobs\.ashbyhq\.com/(?P<slug>[^/?#]+)/(?P<id>[0-9a-f-]{36})")
_WORKDAY = re.compile(
    r"https://(?P<tenant>[^./]+)\.(?P<host>wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?(?P<site>[^/]+)(?P<path>/job/.*?)(?:\?|$)"
)


def _get(url):
    r = requests.get(url, timeout=TIMEOUT, headers=HEADERS)
    r.raise_for_status()
    return r.json()


def fetch_full_text(url):
    m = _GREENHOUSE.search(url)
    if m:
        return strip_html(_get(f"https://boards-api.greenhouse.io/v1/boards/{m['slug']}/jobs/{m['id']}").get("content", ""))
    m = _LEVER.search(url)
    if m:
        data = _get(f"https://api.lever.co/v0/postings/{m['slug']}/{m['id']}")
        return data.get("descriptionPlain", "") + " " + strip_html(" ".join(s.get("content", "") for s in data.get("lists", [])))
    m = _ASHBY.search(url)
    if m:
        for raw in ashby.fetch_board(m["slug"]):
            if raw["id"] == m["id"]:
                return raw.get("descriptionPlain") or ""
        return ""
    m = _WORKDAY.search(url)
    if m:
        api = f"https://{m['tenant']}.{m['host']}.myworkdayjobs.com/wday/cxs/{m['tenant']}/{m['site']}{m['path']}"
        return strip_html(_get(api)["jobPostingInfo"].get("jobDescription", ""))
    return ""


def enrich_job(job):
    try:
        text = fetch_full_text(job.get("url") or "")
    except Exception as e:
        print(f"  could not read full posting for {job.get('url')}: {type(e).__name__}")
        return job
    if text.strip():
        job["description"] = f"{job.get('description', '')} {text}"
        job["has_full_text"] = True
    return job
