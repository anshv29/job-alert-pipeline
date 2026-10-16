"""Remembers which jobs were already seen, so each job is emailed once."""
import hashlib
import sqlite3
import threading

DB_PATH = "jobs.db"

# The scan runs several companies at once, so every database call takes this lock.
LOCK = threading.RLock()


def init_db(path=DB_PATH):
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS seen_jobs (
            id TEXT PRIMARY KEY, title TEXT, company TEXT, url TEXT, first_seen TEXT)"""
    )
    conn.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    return conn


def get_meta(conn, key):
    with LOCK:
        row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def set_meta(conn, key, value):
    with LOCK:
        conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value))
        conn.commit()


def baseline_done(conn):
    return get_meta(conn, "baseline_done") is not None


def _short(job_id):
    """Some job ids are long web addresses. Storing a short fingerprint keeps the saved file small."""
    return hashlib.sha1(job_id.encode("utf-8")).hexdigest()[:20]


def has_seen(conn, job_id):
    with LOCK:
        return conn.execute("SELECT 1 FROM seen_jobs WHERE id = ?", (_short(job_id),)).fetchone() is not None


def mark_seen(conn, job, minimal=False):
    """minimal=True stores only the id. Used for the thousands of jobs that do not match,
    so the saved memory file stays small."""
    row = (_short(job["id"]), None, None, None) if minimal else (_short(job["id"]), job.get("title"), job.get("company"), job.get("url"))
    with LOCK:
        conn.execute(
            "INSERT OR IGNORE INTO seen_jobs (id, title, company, url, first_seen) VALUES (?, ?, ?, ?, datetime('now'))",
            row,
        )


def content_key(job):
    """Same company, title and place means the same job, even on a company's second career site."""
    if job.get("dup_key"):
        return job["dup_key"]
    return "dup:" + "|".join((job.get(k) or "").strip().lower() for k in ("company", "title", "location"))


def has_seen_job(conn, job):
    return has_seen(conn, job["id"]) or has_seen(conn, content_key(job))


def mark_job_seen(conn, job, minimal=False):
    mark_seen(conn, job, minimal)
    mark_seen(conn, {"id": content_key(job), "title": job.get("title"), "company": job.get("company"), "url": job.get("url")}, minimal)
