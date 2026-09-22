"""Reads the installed version from manifest.json, so it only has to be bumped in one place."""

import json
from pathlib import Path


def installed_version():
    manifest = json.loads((Path(__file__).parent / "manifest.json").read_text(encoding="utf-8"))
    return manifest["version"]
