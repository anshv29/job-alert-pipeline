import html
from collections import OrderedDict

from jobalert.filters import TAG_EARLY, get_job_tag

_BADGE = {
    TAG_EARLY: "background-color:#fef3c7;color:#92400e;",
    "General Internship": "background-color:#e5e7eb;color:#374151;",
}
MAX_PER_EMAIL = 100  # about 70 KB, safely under the size where Gmail starts cutting emails short


def _row(job):
    tag = get_job_tag(job)
    return (
        '<tr><td style="padding:10px;border-bottom:1px solid #e0e0e0;">'
        f'<a href="{html.escape(job["url"], quote=True)}" style="color:#1a73e8;text-decoration:none;font-weight:600;">'
        f'{html.escape(job["title"])}</a><br>'
        f'<span style="display:inline-block;margin-top:4px;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;{_BADGE[tag]}">{html.escape(tag)}</span></td>'
        f'<td style="padding:10px;border-bottom:1px solid #e0e0e0;">{html.escape(job.get("location") or "")}</td>'
        f'<td style="padding:10px;border-bottom:1px solid #e0e0e0;white-space:nowrap;">{html.escape(job.get("posted") or "")}</td></tr>'
    )


def chunk(jobs, size=MAX_PER_EMAIL):
    return [jobs[i : i + size] for i in range(0, len(jobs), size)]


def build_email(jobs, part=None):
    """One email, jobs grouped by company. Returns (subject, html)."""
    by_company = OrderedDict()
    for job in sorted(jobs, key=lambda j: j["company"].lower()):
        by_company.setdefault(job["company"], []).append(job)

    sections = ""
    for company, items in by_company.items():
        sections += (
            f'<h3 style="margin:24px 0 6px;color:#222;">{html.escape(company)} ({len(items)})</h3>'
            '<table style="width:100%;border-collapse:collapse;font-size:14px;">'
            + "".join(_row(j) for j in items)
            + "</table>"
        )
    count = len(jobs)
    suffix = f" (part {part[0]} of {part[1]})" if part else ""
    subject = f"{count} new job{'s' if count != 1 else ''} matching your alerts{suffix}"
    body = (
        '<html><body style="font-family:Arial,sans-serif;max-width:760px;margin:0 auto;">'
        f'<h2 style="color:#222;">{subject}</h2>{sections}'
        '<p style="color:#888;font-size:12px;margin-top:32px;">Sent by your job-alert-pipeline. '
        "Each job is only emailed once.</p></body></html>"
    )
    return subject, body


def build_setup_email(postings_checked, sources_checked, preset, ai_mode, failed):
    """The one short email sent on the first run, instead of the backlog."""
    problems = ""
    if failed:
        problems = (
            "<p>These sources could not be reached this time: "
            + html.escape(", ".join(failed[:15]))
            + ". They will be tried again on the next run, and anything they list that is already open "
            "may show up as new once.</p>"
        )
    subject = "Job alerts are set up and working"
    body = (
        '<html><body style="font-family:Arial,sans-serif;max-width:640px;margin:0 auto;color:#222;">'
        f"<h2>Setup worked</h2>"
        f"<p>Your job alerts are running with the <b>{html.escape(preset)}</b> preset.</p>"
        f"<p>I looked at {postings_checked:,} postings across {sources_checked} sources and marked them all as "
        "already seen, so you are not flooded with everything that is open today.</p>"
        "<p><b>From now on you will get an email only when a new matching posting appears.</b> "
        "Most runs find nothing new and send no email, which is normal.</p>"
        f'<p style="color:#666;font-size:13px;">{html.escape(ai_mode)}</p>'
        f"{problems}"
        "</body></html>"
    )
    return subject, body
