"""Manifest version, adapted from 100prznt's version helper.

Loaded during module import, not synchronously from each WebSocket request.
"""

import json
from pathlib import Path

_VERSION = json.loads((Path(__file__).parent / "manifest.json").read_text(encoding="utf-8"))["version"]


def installed_version():
    return _VERSION
