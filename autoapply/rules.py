import re

from jobalert.settings import get_settings

AUTO_APPLY_ATS = {"greenhouse", "lever", "ashby"}


def _blocklist_patterns():
    return [re.compile(r"\b" + re.escape(name) + r"\b", re.IGNORECASE) for name in get_settings()["blocklist"]]


def is_blocklisted(company):
    return any(p.search(company or "") for p in _blocklist_patterns())


def combine_grad_restriction(regex_hit, llm_value):
    # The regex can only ever spot a restrictive phrase, it can't prove there
    # is none, so a regex hit always wins over whatever the AI said.
    if regex_hit:
        return "specific"
    return llm_value


def evaluate(job, classification, ats):
    """Decides a job's status. Returns kwargs ready for db.insert_application.

    Checks run in a fixed order: hard rejections first, then "a human should
    look", and only jobs that clear everything become eligible.
    """
    settings = get_settings()
    wanted_domains = settings["auto_apply_domains"]
    reason = classification.get("reason")

    def result(status, status_reason, grad=None):
        return {"status": status, "status_reason": status_reason,
                "fit_reason": reason, "grad_restriction": grad}

    if classification.get("error"):
        return result("needs_review", "AI classification failed or is switched off, needs a manual look")

    grad = combine_grad_restriction(
        regex_flags_grad_restriction(job.get("title"), job.get("description"), settings["grad_year"]),
        classification.get("grad_restriction"),
    )
    # No real posting text means "no grad date found" proves nothing, so the
    # answer can never be better than unclear (a regex hit above still wins).
    no_text = not job.get("has_full_text", True)
    if no_text and grad != "specific":
        grad = "unclear"
    domain = classification.get("domain")

    if domain is None:
        return result("needs_review", "AI did not return a usable role category", grad)
    if domain not in wanted_domains:
        return result("filtered_out", f"Role category is {domain}, not one you asked to auto-apply to", grad)
    if is_blocklisted(job.get("company")):
        return result("filtered_out", f"{job.get('company')} is on the blocklist", grad)
    if grad == "specific":
        return result("filtered_out", "Posting states a grad date or year of study requirement", grad)
    if grad is None or grad == "unclear":
        why = ("Full posting text unavailable, could not check for a grad date or year of study"
               if no_text else "Could not tell whether a grad date or year of study is required")
        return result("needs_review", why, grad or "unclear")
    if ats not in AUTO_APPLY_ATS:
        return result("needs_review", f"ATS is '{ats}', the applier only handles Greenhouse, Lever and Ashby", grad)

    return result("eligible", f"{domain} role on {ats}, not blocklisted, no grad date or year requirement", grad)


# --- Grad restriction regex pass ----------------------------------------------
#
# Cheap first check before trusting the LLM. It only fires on phrasing that
# clearly excludes a student who has not yet reached their final year, and it can only
# say "found one", never "there is none", so a hit always wins. Merely
# mentioning a grad date is fine ("class of 2031", "currently enrolled").


# Phrases that exclude a first-year no matter what year they mention.
_ALWAYS_EXCLUDING = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\b(?:final|last|penultimate)[- ](?:year|semester|term)\b",
        r"\brising (?:senior|junior)s?\b",
        r"\b(?:third|3rd|fourth|4th)[- ]year\b",
        r"\b(?:senior|junior) year\b",
        # Plural "juniors"/"seniors" means students in those years ("Juniors working
        # towards a bachelor's"). Singular "senior engineer" is a job level, so not matched.
        r"\b(?:juniors|seniors)\b",
        r"\bgraduating seniors?\b",
        r"\b(?:recent|new) grad(?:uate)?s?\b",
        r"\b(?:fall|spring|winter|summer)(?: and (?:fall|spring|winter|summer))? graduates?\b",
    ]
]

# Phrases where a year decides it: "class of 2027", "graduating in May 2028",
# "degree obtained by summer 2027", "2027 graduates".
_YEAR_CONTEXTS = [
    re.compile(r"class of[^.;\n]{0,30}", re.IGNORECASE),
    re.compile(r"\bgraduat(?:e|es|ing|ion)\b[^.;\n]{0,40}", re.IGNORECASE),
    re.compile(r"\b20\d{2}\b[^.;\n]{0,25}\bgraduat\w*", re.IGNORECASE),
    re.compile(r"\b(?:obtained|obtain|completed|complete|earned|finished|conferred)\b[^.;\n]{0,30}\b(?:by|before|prior to)\b[^.;\n]{0,25}", re.IGNORECASE),
]
# "graduate students", "graduate degree" are about level of study, not a date.
_NOT_A_DATE = re.compile(r"\bgraduat\w*\s+(?:students?|school|degrees?|programs?|studies|level|courses|candidates?)\b", re.IGNORECASE)
# "graduating after 2027" is a lower bound, which a 2031 graduate satisfies.
_LOWER_BOUND = re.compile(r"\b(?:after|later|beyond|newer|at least|no earlier)\b", re.IGNORECASE)


def regex_flags_grad_restriction(title, description, grad_year):
    text = f"{title or ''} {description or ''}"

    if any(p.search(text) for p in _ALWAYS_EXCLUDING):
        return True

    for pattern in _YEAR_CONTEXTS:
        for match in pattern.finditer(text):
            span = match.group(0)
            if _NOT_A_DATE.search(span) or _LOWER_BOUND.search(span):
                continue
            years = [int(y) for y in re.findall(r"\b(20\d{2})\b", span)]
            # Only excluding if every year named is before the applicant's grad
            # year: "class of 2029, 2030 or 2031" still includes them.
            if years and max(years) < grad_year:
                return True
    return False
