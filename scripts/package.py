"""Build an installation archive without private samples or developer dependencies."""

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
version = json.loads((ROOT / "custom_components/ifm_iolink/manifest.json").read_text(encoding="utf-8"))["version"]
target = ROOT / f"dist/ifm-iolink-{version}.zip"
target.parent.mkdir(exist_ok=True)
with ZipFile(target, "w", ZIP_DEFLATED) as archive:
    paths = list((ROOT / "custom_components/ifm_iolink").rglob("*"))
    paths += [ROOT / "README.md", ROOT / "README.en.md", ROOT / "CHANGELOG.md", ROOT / "hacs.json", ROOT / "LICENSE", *list((ROOT / "docs").rglob("*"))]
    for path in sorted(paths):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            archive.write(path, path.relative_to(ROOT))
print(target)
