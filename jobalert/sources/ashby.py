from jobalert.sources.common import fmt_iso, get_json


def fetch_board(slug):
    return get_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}").get("jobs", [])


def fetch(company):
    for raw in fetch_board(company["slug"]):
        if not raw.get("isListed", True):
            continue
        yield {
            "id": f"ashby-{raw['id']}",
            "title": (raw.get("title") or "").strip(),
            "company": company["name"],
            "location": raw.get("location") or "Unknown",
            "url": raw["jobUrl"],
            "description": raw.get("descriptionPlain") or "",
            "posted": fmt_iso(raw.get("publishedAt")),
        }
