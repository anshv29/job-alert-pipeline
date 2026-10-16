"""Optional second filter using Claude Haiku. With no API key everything still works
using the keyword filter alone."""
import os
import re

from jobalert.settings import get_settings

DEFAULT_MODEL = "claude-haiku-4-5"

_client = None
_announced = False


def api_key_present():
    return bool(os.getenv("ANTHROPIC_API_KEY", "").strip())


def enabled():
    return bool(get_settings()["llm"].get("enabled", True)) and api_key_present()


def model_name():
    return get_settings()["llm"].get("model") or DEFAULT_MODEL


def describe_mode():
    s = get_settings()["llm"]
    if not s.get("enabled", True):
        return "AI filter: off in config.yaml (keyword filter only)"
    if not api_key_present():
        return "AI filter: off because no ANTHROPIC_API_KEY is set (keyword filter only, this is fine)"
    return f"AI filter: on ({model_name()})"


def _get_client():
    global _client
    if _client is None:
        import anthropic

        _client = anthropic.Anthropic()
    return _client


def build_prompt(job):
    s = get_settings()
    years = " or ".join(s["years"])
    domain_lines = "\n".join(f"   - {name}: {desc}" for name, desc in s["domains"].items())
    domain_names = " or ".join(list(s["domains"]) + ["None"])
    grad = s["grad_year"]
    max_chars = int(s["llm"].get("max_description_chars", 6000))
    grad_rule = (
        f"The applicant graduates in {grad}. Answer specific only if the posting states a graduation date or class year "
        f"before {grad}, requires a year of study the applicant is not in (for example final year, rising senior), or a "
        f"degree completed before {grad}. Wording such as currently enrolled, pursuing a degree, or open to all years is none. "
        "Answer unclear only if you cannot tell."
        if grad
        else "Answer none."
    )
    return f"""You are screening a job posting for a college student looking for {years} internships, co-ops or early-talent programs in: {s['llm_focus']}.

Answer YES only if ALL of these hold:
1. TIMING: the role is for {years}, or an internship or co-op that clearly lands in that period.
2. LEVEL: it is an internship, co-op, or student or early-talent program. Not full-time, not senior, no prior full-time experience required.
3. DOMAIN: the actual day-to-day work fits the focus above. Judge the work itself, not just words in the title.

Also report:
4. DOMAIN CATEGORY, the single best match:
{domain_lines}
5. GRAD_RESTRICTION: {grad_rule}

Respond in EXACTLY this four-line format and nothing else:
ANSWER: YES or NO
REASON: <one short sentence>
DOMAIN: {domain_names}
GRAD_RESTRICTION: none or specific or unclear

Job title: {job.get('title') or ''}
Job description: {(job.get('description') or '')[:max_chars]}"""


def _field(text, name):
    m = re.search(rf"^\s*{name}\s*:\s*(.+?)\s*$", text, re.IGNORECASE | re.MULTILINE)
    return m.group(1) if m else None


def classify_job(job):
    """Returns a dict and never raises. error=True means the answer must not be trusted."""
    result = {"answer": None, "reason": None, "domain": None, "grad_restriction": None, "error": True}
    if not enabled():
        return result
    try:
        response = _get_client().messages.create(
            model=model_name(), max_tokens=256, messages=[{"role": "user", "content": build_prompt(job)}]
        )
        text = next((b.text for b in response.content if b.type == "text"), "")
    except Exception as e:
        print(f"  AI filter skipped for one job ({type(e).__name__}); keeping it based on keywords")
        return result

    answer = _field(text, "ANSWER")
    if answer is None:
        return result
    result["error"] = False
    result["answer"] = "YES" in answer.upper()
    result["reason"] = _field(text, "REASON")
    valid = {d.upper(): d for d in list(get_settings()["domains"]) + ["None"]}
    domain = (_field(text, "DOMAIN") or "").strip().upper()
    result["domain"] = valid.get(domain)
    grad = (_field(text, "GRAD_RESTRICTION") or "").strip().lower()
    if grad in ("none", "specific", "unclear"):
        result["grad_restriction"] = grad
    return result


def passes_gate(classification):
    """Keep the job unless the AI clearly said NO. A failed call never drops a job."""
    if classification["error"]:
        return True
    return classification["answer"]
