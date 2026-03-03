"""Configuration for the Bitwise Cloud client."""

import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "bitwise-cloud"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_API_URL = "https://bitwise.mikeayles.com"


def _load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def _save_config(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2) + "\n")


def get_api_key() -> str:
    key = os.environ.get("BITWISE_API_KEY")
    if key:
        return key
    cfg = _load_config()
    key = cfg.get("api_key")
    if key:
        return key
    raise RuntimeError(
        "No API key configured. Set BITWISE_API_KEY or run the set_api_key tool."
    )


def get_api_url() -> str:
    url = os.environ.get("BITWISE_API_URL")
    if url:
        return url
    cfg = _load_config()
    return cfg.get("api_url", DEFAULT_API_URL)


def save_api_key(key: str) -> None:
    cfg = _load_config()
    cfg["api_key"] = key
    _save_config(cfg)


def save_api_url(url: str) -> None:
    cfg = _load_config()
    cfg["api_url"] = url
    _save_config(cfg)
