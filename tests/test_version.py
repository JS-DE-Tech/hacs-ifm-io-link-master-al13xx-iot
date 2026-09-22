import json
from pathlib import Path

from custom_components.ifm_iolink.version import installed_version


def test_installed_version_matches_manifest_file():
    manifest = json.loads(
        (Path(__file__).parents[1] / "custom_components/ifm_iolink/manifest.json").read_text(encoding="utf-8")
    )
    assert installed_version() == manifest["version"]
