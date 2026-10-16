"""Free keyword prefilter. Runs before any paid AI call."""
import re

from jobalert.settings import get_settings


def _compile(terms):
    # Word-boundary matching, so "intern" does not match inside "international".
    return [re.compile(r"(?<!\w)" + re.escape(t) + r"(?!\w)") for t in terms]


class Matcher:
    def __init__(self, settings):
        years = settings["years"]
        year_terms = list(years) + [f"summer {y}" for y in years] + [f"class of {y}" for y in years]
        self.year = _compile(year_terms)
        self.roles = _compile(settings["roles"])
        self.level = _compile(settings["level_terms"])
        self.title_level = _compile(settings["title_only_level_terms"])
        self.exclude = _compile(settings["exclude_title_terms"])
        self.early = _compile(settings["early_program_terms"])


_matcher = None


def matcher():
    global _matcher
    if _matcher is None:
        _matcher = Matcher(get_settings())
    return _matcher


def _any(text, patterns):
    return any(p.search(text) for p in patterns)


def title_looks_like_student_role(title):
    """Cheap check used to decide whether a full posting is worth downloading."""
    m = matcher()
    t = (title or "").lower()
    return (_any(t, m.level) or _any(t, m.title_level)) and not _any(t, m.exclude)


def is_relevant(title, description=""):
    m = matcher()
    title_l = (title or "").lower()
    text = f"{title_l} {(description or '').lower()}"

    if not _any(text, m.year):
        return False
    if not _any(text, m.roles):
        return False
    if not (_any(text, m.level) or _any(title_l, m.title_level)):
        return False
    # Exclusions only look at the title: descriptions often say things like
    # "reports to the Director of Engineering" even for genuine internships.
    if _any(title_l, m.exclude):
        return False
    return True


def is_relevant_job(job):
    return is_relevant(job.get("title", ""), job.get("description", ""))


TAG_EARLY = "Freshman/Sophomore Program"
TAG_GENERAL = "General Internship"


def get_job_tag(job):
    text = f"{job.get('title') or ''} {job.get('description') or ''}".lower()
    return TAG_EARLY if _any(text, matcher().early) else TAG_GENERAL


def in_excluded_location(job):
    """True if the job's location contains any word from target.exclude_locations."""
    location = (job.get("location") or "").lower()
    return any(term in location for term in get_settings()["exclude_locations"])
