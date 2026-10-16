from jobalert.sources.common import fmt_unix, get_json, strip_html


def normalize(raw, company_name):
    parts = [raw.get("descriptionPlain") or ""]
    for section in raw.get("lists") or []:
        parts.append(section.get("text") or "")
        parts.append(strip_html(section.get("content") or ""))
    parts.append(raw.get("additionalPlain") or "")
    return {
        "id": f"lever-{raw['id']}",
        "title": raw["text"],
        "company": company_name,
        "location": (raw.get("categories") or {}).get("location") or "Unknown",
        "url": raw["hostedUrl"],
        "description": " ".join(parts),
        "posted": fmt_unix(raw.get("createdAt"), millis=True),
    }


def fetch(company):
    for raw in get_json(f"https://api.lever.co/v0/postings/{company['slug']}", params={"mode": "json"}):
        yield normalize(raw, company["name"])
