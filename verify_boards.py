"""Checks that every company in config.yaml still returns jobs.

  python verify_boards.py                 check the preset chosen in config.yaml
  python verify_boards.py --preset tech   check a specific preset
  python verify_boards.py --all           check every preset

Prints one line per company. A company that returns 0 jobs or an error is listed at the end.
Run this after adding companies to config.yaml, and now and then to catch career sites that moved.
"""
import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import requests

from jobalert import settings as settings_module
from jobalert.sources import ashby, feed, greenhouse, lever, workday
from jobalert.sources.common import HEADERS, TIMEOUT


def check(item):
    result = _check_once(item)
    if result[2] <= 0:  # one retry: career sites sometimes answer with a brief error
        time.sleep(3)
        result = _check_once(item)
    return result


def _check_once(item):
    kind, c = item
    try:
        if kind == "greenhouse":
            name = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{c['slug']}", timeout=TIMEOUT, headers=HEADERS).json().get("name")
            jobs = list(greenhouse.fetch(c))
            return kind, c["name"], len(jobs), f"board name: {name}"
        if kind == "lever":
            jobs = list(lever.fetch(c))
            return kind, c["name"], len(jobs), jobs[0]["url"] if jobs else ""
        if kind == "ashby":
            jobs = list(ashby.fetch(c))
            return kind, c["name"], len(jobs), jobs[0]["url"] if jobs else ""
        if kind == "workday":
            data = workday.search(c, "", 0)
            return kind, c["name"], int(data.get("total", 0)), f"{c['tenant']}.{c['host']}/{c['site']}"
        if kind == "feeds":
            jobs = list(feed.fetch(c))
            return kind, c["name"], len(jobs), jobs[0]["url"] if jobs else ""
    except Exception as e:
        return kind, c["name"], -1, f"{type(e).__name__}: {str(e)[:80]}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preset")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    import yaml

    with open(settings_module.CONFIG_PATH, encoding="utf-8") as f:
        presets = list(yaml.safe_load(f)["presets"])
    chosen = presets if args.all else [args.preset or None]

    bad = []
    for preset in chosen:
        s = settings_module.load_settings(preset_override=preset)
        items = [(kind, c) for kind in settings_module.COMPANY_KINDS for c in s["companies"][kind]]
        print(f"\n=== preset: {s['preset']} ({len(items)} companies) ===")
        with ThreadPoolExecutor(8) as ex:
            for kind, name, count, note in ex.map(check, items):
                status = "OK " if count > 0 else "BAD"
                print(f"{status} {kind:10} {name:34} {count:6} jobs  {note}")
                if count <= 0:
                    bad.append(f"{s['preset']}: {name} ({kind})")
    if bad:
        print(f"\n{len(bad)} problem(s):")
        for b in bad:
            print("  -", b)
        sys.exit(1)
    print("\nAll boards returned jobs.")


if __name__ == "__main__":
    main()
