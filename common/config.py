from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paths import ensure_runtime_dirs


def config_file() -> Path:
    return ensure_runtime_dirs()["config"] / "settings.json"


def load_settings() -> dict[str, Any]:
    path = config_file()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_settings(settings: dict[str, Any]) -> None:
    path = config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def get_setting(key: str, default: Any = None) -> Any:
    return load_settings().get(key, default)


def set_setting(key: str, value: Any) -> None:
    settings = load_settings()
    if value in (None, ""):
        settings.pop(key, None)
    else:
        settings[key] = value
    save_settings(settings)
