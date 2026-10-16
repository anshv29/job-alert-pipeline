"""Scan every source, filter, and send one email with everything new."""
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

from jobalert import digest, filters, llm, storage
from jobalert.emailer import EmailConfigError, email_settings, send_email
from jobalert.settings import get_settings
from jobalert.sources import ashby, feed, greenhouse, lever, simplify, workday
from jobalert.storage import (DB_PATH, baseline_done, content_key, has_seen, has_seen_job, init_db, mark_job_seen,
                              mark_seen, set_meta)

WORKERS = 8           # companies scanned at the same time
JOBS_PER_BOARD = 4    # postings downloaded at the same time within one company

CONNECTORS = (
    ("greenhouse", greenhouse),
    ("lever", lever),
    ("ashby", ashby),
    ("workday", workday),
    ("feeds", feed),
)


def evaluate(job, conn, stats):
    """Download the full posting if needed, run the keyword filter, then the optional AI filter.
    Returns the job if it should be emailed, otherwise None."""
    enrich = job.pop("_enrich", None)
    stage = job.pop("_enrich_stage", None)
    try:
        if enrich and stage == "before":
            enrich(job)
        if not filters.is_relevant_job(job) or filters.in_excluded_location(job):
            mark_seen(conn, job, minimal=True)
            return None
        with storage.LOCK:
            stats["keyword_pass"] += 1
        if enrich and stage == "after":
            enrich(job)
        if llm.enabled():
            job["classification"] = llm.classify_job(job)
            if not llm.passes_gate(job["classification"]):
                mark_seen(conn, job, minimal=True)
                return None
    except Exception as e:
        print(f"  skipped one job after an error ({type(e).__name__}: {e})", flush=True)
        return None
    return job


def process(jobs, conn, run_ids, stats, baseline=False):
    """Returns the new jobs that passed every filter. Irrelevant jobs are marked seen
    right away. Jobs that pass are only marked seen after the email goes out."""
    candidates = []
    for job in jobs:
        with storage.LOCK:
            if job["id"] in run_ids or has_seen(conn, job["id"]):
                continue
            run_ids.add(job["id"])
            job["dup_key"] = content_key(job)
            if job["dup_key"] in run_ids or has_seen_job(conn, job):
                continue
            run_ids.add(job["dup_key"])
            stats["scanned"] += 1
        candidates.append(job)

    if baseline:
        # First run: remember everything, download nothing more, call no AI.
        for job in candidates:
            job.pop("_enrich", None)
            mark_job_seen(conn, job, minimal=True)
        return []

    with ThreadPoolExecutor(JOBS_PER_BOARD) as pool:
        results = pool.map(lambda j: evaluate(j, conn, stats), candidates)
        return [j for j in results if j]


def save_for_auto_apply(jobs):
    """Optional. Only runs when features: auto_apply is true in config.yaml."""
    try:
        from autoapply import db
    except ImportError:
        print("auto_apply is on but its extra packages are missing. See docs/AUTO_APPLY.md.")
        return
    no_answer = {"error": True, "reason": None, "domain": None, "grad_restriction": None}
    for job in jobs:
        db.save_job(job, source=job["id"].split("-")[0], classification=job.get("classification") or no_answer)


def _in_memory_copy(real):
    """A dry run reads what was already seen but never writes to jobs.db."""
    import sqlite3

    mem = sqlite3.connect(":memory:", check_same_thread=False)
    real.backup(mem)
    return mem


def run(dry_run=False, only=None, limit_companies=None):
    s = get_settings()
    partial_run = bool(only or limit_companies)
    print(f"Preset: {s['preset']}")
    print(llm.describe_mode())

    if not dry_run:
        try:
            email_settings()
        except EmailConfigError as e:
            raise SystemExit(f"Cannot start: {e}")

    conn = init_db(DB_PATH)
    if dry_run:
        conn = _in_memory_copy(conn)
    first_run = not baseline_done(conn)
    send_backlog = bool(s["alerts"].get("send_backlog_on_first_run", False))
    # A dry run is a preview, so it always shows the matches. A real first run only records them.
    baseline = first_run and not send_backlog and not dry_run
    if first_run and dry_run and not send_backlog:
        print("Note: this is the first run. A real first run will NOT email these matches. It will remember "
              "them and send one short setup email instead.")
    stats = {"scanned": 0, "keyword_pass": 0, "boards": 0, "board_errors": 0}
    run_ids, pending, failed = set(), [], []
    lock = threading.Lock()

    def scan(task):
        label, fetcher, company = task
        for attempt in (1, 2):
            try:
                found = process(fetcher(company), conn, run_ids, stats, baseline)
                with storage.LOCK:
                    conn.commit()
                with lock:
                    pending.extend(found)
                print(f"  {label}: {len(found)} new", flush=True)
                return
            except Exception as e:
                # Career sites sometimes answer with a brief server error, so try once more.
                if attempt == 1:
                    time.sleep(5)
                    continue
                with lock:
                    stats["board_errors"] += 1
                    failed.append(label)
                print(f"  {label}: ERROR {type(e).__name__}: {str(e)[:120]}", flush=True)

    tasks = []
    for kind, module in CONNECTORS:
        if only and kind not in only:
            continue
        if not s["sources"].get(kind, True):
            continue
        companies = s["companies"][kind]
        if limit_companies:
            companies = companies[:limit_companies]
        print(f"{kind}: {len(companies)} companies", flush=True)
        tasks += [(c["name"], module.fetch, c) for c in companies]
    if s["sources"].get("simplify", True) and (not only or "simplify" in only):
        print("simplify: the public SimplifyJobs list", flush=True)
        tasks.append(("SimplifyJobs", simplify.fetch, None))

    stats["boards"] = len(tasks)
    with ThreadPoolExecutor(WORKERS) as pool:
        list(pool.map(scan, tasks))
    pending.sort(key=lambda j: (j["company"].lower(), j["title"].lower()))

    print(
        f"\nScanned {stats['scanned']} unseen postings from {stats['boards']} sources; "
        f"{stats['keyword_pass']} matched keywords; {len(pending)} to email."
    )
    if stats["boards"] and stats["board_errors"] == stats["boards"]:
        raise SystemExit("Every source failed, so nothing was checked. Check your internet connection.")
    if failed:
        print(f"{len(failed)} source(s) had errors this run (they are retried next run): {', '.join(failed[:15])}")

    if baseline:
        subject, body = digest.build_setup_email(stats["scanned"], stats["boards"] - stats["board_errors"],
                                                  s["preset"], llm.describe_mode(), failed)
        to = send_email(subject, body)
        conn.commit()
        if not partial_run:
            set_meta(conn, "baseline_done", "yes")
        print(f"First run: remembered {stats['scanned']} current postings and sent the setup email -> {to}")
        return {"sent": 0, "jobs": [], "failed": failed, "setup_email": True}

    if not pending:
        if first_run and not dry_run and not partial_run:
            set_meta(conn, "baseline_done", "yes")
        print("Nothing new, no email sent.")
        return {"sent": 0, "jobs": pending, "failed": failed}

    parts = digest.chunk(pending)
    if dry_run:
        for i, part in enumerate(parts, 1):
            subject, _ = digest.build_email(part, (i, len(parts)) if len(parts) > 1 else None)
            print(f"[dry run] would email: {subject}")
        for job in pending[:25]:
            print(f"   - {job['company']}: {job['title']}  ({job['url']})")
        return {"sent": 0, "jobs": pending, "failed": failed}

    for i, part in enumerate(parts, 1):
        subject, body = digest.build_email(part, (i, len(parts)) if len(parts) > 1 else None)
        to = send_email(subject, body)
        for job in part:
            mark_job_seen(conn, job)
        conn.commit()
        print(f"Sent: {subject} -> {to}")
        if s["features"].get("auto_apply"):
            save_for_auto_apply(part)
    if first_run and not dry_run and not partial_run:
        set_meta(conn, "baseline_done", "yes")
    return {"sent": len(pending), "jobs": pending, "failed": failed}
