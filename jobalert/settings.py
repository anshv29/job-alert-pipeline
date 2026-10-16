"""Reads config.yaml and merges the chosen preset into one flat settings dict."""
import os
from pathlib import Path

import yaml

CONFIG_PATH = Path(os.getenv("JOB_ALERT_CONFIG", Path(__file__).resolve().parent.parent / "config.yaml"))

COMPANY_KINDS = ("greenhouse", "lever", "ashby", "workday", "feeds")


class ConfigError(Exception):
    """Raised with a plain-language message a non-technical person can act on."""


def load_settings(path=CONFIG_PATH, preset_override=None):
    try:
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(
            f"config.yaml has a typing mistake and could not be read. "
            f"Check spaces and colons near the line mentioned here: {e}"
        )
    except FileNotFoundError:
        raise ConfigError(f"Could not find {path}")

    presets = raw.get("presets") or {}
    name = str(preset_override or raw.get("preset", "")).strip().lower()
    if name not in presets:
        raise ConfigError(
            f'config.yaml says preset: "{raw.get("preset")}" but the choices are: '
            + ", ".join(sorted(presets))
        )
    preset = presets[name]

    keywords = raw.get("keywords") or {}
    settings = {
        "preset": name,
        "years": [str(y) for y in (raw.get("target") or {}).get("years", [])],
        "exclude_locations": _clean((raw.get("target") or {}).get("exclude_locations")),
        "grad_year": int((raw.get("target") or {}).get("grad_year", 0)) or None,
        "timezone": raw.get("timezone", "America/New_York"),
        "sources": raw.get("sources") or {},
        "llm": raw.get("llm") or {},
        "email": raw.get("email") or {},
        "alerts": raw.get("alerts") or {},
        "workday": raw.get("workday") or {},
        "features": raw.get("features") or {},
        "auto_apply": raw.get("auto_apply") or {},
        "roles": _clean(preset.get("roles")),
        "level_terms": _clean(keywords.get("level_terms")) + _clean(preset.get("extra_level_terms")),
        "title_only_level_terms": _clean(preset.get("title_only_level_terms")),
        "exclude_title_terms": _clean(keywords.get("exclude_title_terms")),
        "early_program_terms": _clean(keywords.get("early_program_terms")),
        "llm_focus": (preset.get("llm_focus") or "").strip(),
        "blocklist": [str(b) for b in (preset.get("blocklist") or [])],
        "auto_apply_domains": [str(d) for d in (preset.get("auto_apply_domains") or [])],
        "domains": preset.get("domains") or {},
        "companies": {kind: (preset.get("companies") or {}).get(kind) or [] for kind in COMPANY_KINDS},
    }
    if not settings["years"]:
        raise ConfigError("config.yaml: target.years is empty. Add the year you want, for example [2027].")
    if not settings["roles"]:
        raise ConfigError(f'config.yaml: the "{name}" preset has no roles listed.')
    return settings


def _clean(items):
    return [str(i).strip().lower() for i in (items or []) if str(i).strip()]


_settings = None


def get_settings():
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings
