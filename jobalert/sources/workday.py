"""Workday career sites. The search list has no description, so the full posting is
downloaded only for jobs whose title already looks like a student role."""
import time

import requests

from jobalert.filters import title_looks_like_student_role
from jobalert.settings import get_settings
from jobalert.sources.common import HEADERS, TIMEOUT, strip_html

PAGE_SIZE = 20


def base(company):
    return f"https://{company['tenant']}.{company['host']}.myworkdayjobs.com"


def search(company, term, offset):
    url = f"{base(company)}/wday/cxs/{company['tenant']}/{company['site']}/jobs"
    r = requests.post(
        url,
        json={"appliedFacets": {}, "limit": PAGE_SIZE, "offset": offset, "searchText": term},
        timeout=TIMEOUT,
        headers=HEADERS,
    )
    r.raise_for_status()
    return r.json()


def fetch_detail(company, external_path):
    r = requests.get(
        f"{base(company)}/wday/cxs/{company['tenant']}/{company['site']}{external_path}",
        timeout=TIMEOUT,
        headers=HEADERS,
    )
    r.raise_for_status()
    return r.json()["jobPostingInfo"]


def make_enricher(company, external_path):
    def enrich(job):
        info = fetch_detail(company, external_path)
        job["description"] = strip_html(info.get("jobDescription", ""))
        job["location"] = info.get("location") or job["location"]
        job["has_full_text"] = True
        return job

    return enrich


def fetch(company):
    cfg = get_settings()["workday"]
    terms = cfg.get("search_terms") or [""]
    max_pages = int(cfg.get("max_pages", 3))
    seen_paths = set()

    for term in terms:
        for page in range(max_pages):
            data = search(company, term, page * PAGE_SIZE)
            postings = data.get("jobPostings", [])
            for raw in postings:
                path = raw.get("externalPath")
                if not path or path in seen_paths:
                    continue
                seen_paths.add(path)
                job = {
                    "id": f"workday-{company['tenant']}-{company['site']}-{path}",
                    "title": raw["title"],
                    "company": company["name"],
                    "location": raw.get("locationsText", "Unknown"),
                    "url": f"{base(company)}/en-US/{company['site']}{path}",
                    "description": "",
                    "posted": raw.get("postedOn", "Unknown"),
                    "has_full_text": False,
                }
                if title_looks_like_student_role(raw["title"]):
                    job["_enrich"] = make_enricher(company, path)
                    job["_enrich_stage"] = "before"
                yield job
            if len(postings) < PAGE_SIZE:
                break
            time.sleep(0.2)
