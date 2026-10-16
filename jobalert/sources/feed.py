"""Company career sites that publish a public RSS feed or XML sitemap of their jobs
(Scotiabank, Canada Life, National Bank)."""
import html
import re
import time
from urllib.parse import unquote, urlparse

import requests

from jobalert.sources.common import HEADERS, strip_html

TIMEOUT = 45


def _get(url):
    # Some career sites answer a few requests in a row with a brief 406 or 429, so try again.
    headers = {**HEADERS, "Accept": "application/rss+xml, application/xml, text/xml, */*"}
    for attempt in range(3):
        r = requests.get(url, timeout=TIMEOUT, headers=headers)
        if r.status_code in (406, 429, 500, 502, 503) and attempt < 2:
            time.sleep(3 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.text


def _tag(block, name):
    m = re.search(rf"<{name}>(.*?)</{name}>", block, re.S)
    if not m:
        return ""
    value = m.group(1).strip()
    cdata = re.match(r"<!\[CDATA\[(.*)\]\]>$", value, re.S)
    return (cdata.group(1) if cdata else html.unescape(value)).strip()


def parse_rss(text, company):
    for block in re.findall(r"<item>(.*?)</item>", text, re.S):
        link = _tag(block, "link")
        title = strip_html(_tag(block, "title"))
        if not link or not title:
            continue
        yield {
            "id": f"feed-{company['name']}-{link}",
            "title": title,
            "company": company["name"],
            "location": "See posting",
            "url": link,
            "description": strip_html(_tag(block, "description")),
            "posted": "Unknown",
        }


def title_from_slug(url):
    """Job pages end in a numeric id, so the title is the last non-numeric path piece."""
    parts = [p for p in urlparse(url).path.split("/") if p and not p.isdigit()]
    return unquote(parts[-1]).replace("-", " ").strip() if parts else ""


def parse_sitemap(text, company):
    for loc in re.findall(r"<loc>(.*?)</loc>", text, re.S):
        loc = html.unescape(loc.strip())
        if "/job/" not in loc.lower():
            continue
        yield {
            "id": f"feed-{company['name']}-{loc}",
            "title": title_from_slug(loc),
            "company": company["name"],
            "location": "See posting",
            "url": loc,
            "description": "",
            "posted": "Unknown",
        }


def fetch(company):
    seen = set()
    for url in company["urls"]:
        text = _get(url)
        parser = parse_sitemap if company.get("format") == "sitemap" else parse_rss
        for job in parser(text, company):
            if job["id"] not in seen:
                seen.add(job["id"])
                yield job
