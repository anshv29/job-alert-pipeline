"""SimplifyJobs public internship list on GitHub (mostly tech and quant roles)."""
from jobalert.enrich import enrich_job
from jobalert.settings import get_settings
from jobalert.sources.common import fmt_unix, get_json

DEFAULT_URL = "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/.github/scripts/listings.json"


def fetch(_company=None):
    url = get_settings()["sources"].get("simplify_url") or DEFAULT_URL
    for raw in get_json(url):
        if not raw.get("active"):
            continue
        terms = raw.get("terms") or []
        # The recruiting term (for example Summer 2027) is not in the title, so it is
        # copied into the description or the year filter would reject nearly everything.
        description = f"{raw.get('category', '')}. Terms: {', '.join(terms)}."
        job = {
            "id": f"simplify-{raw['id']}",
            "title": raw["title"],
            "company": (raw.get("company_name") or "Unknown").strip(),
            "location": ", ".join(raw.get("locations") or []) or "Unknown",
            "url": raw["url"],
            "description": description,
            "posted": fmt_unix(raw.get("date_posted")),
            "has_full_text": False,
            "_enrich": enrich_job,
            "_enrich_stage": "after",
        }
        yield job
