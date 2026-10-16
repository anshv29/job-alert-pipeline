"""Auto-apply settings, read from config.yaml and the environment."""
import os

from jobalert.settings import get_settings


def auto_apply_enabled():
    return bool(get_settings()["features"].get("auto_apply"))


def daily_cap():
    return int(get_settings()["auto_apply"].get("daily_cap", 10))


def delay_seconds():
    low, high = get_settings()["auto_apply"].get("delay_seconds", [45, 150])
    return (low, high)


DRY_RUN_DELAY_SECONDS = (2, 5)


def dry_run():
    # Anything except an explicit DRY_RUN=false stays a dry run, so a typo can never turn on real submissions.
    return os.getenv("DRY_RUN", "true").strip().lower() != "false"


def headless():
    return os.getenv("HEADLESS", "false").strip().lower() == "true"
