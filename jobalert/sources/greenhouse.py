from jobalert.sources.common import fmt_iso, get_json, strip_html


def fetch(company):
    data = get_json(f"https://boards-api.greenhouse.io/v1/boards/{company['slug']}/jobs", params={"content": "true"})
    for raw in data.get("jobs", []):
        yield {
            "id": f"greenhouse-{raw['id']}",
            "title": raw["title"],
            "company": company["name"],
            "location": (raw.get("location") or {}).get("name", "Unknown"),
            "url": raw["absolute_url"],
            "description": strip_html(raw.get("content", "")),
            "posted": fmt_iso(raw.get("updated_at")),
        }
