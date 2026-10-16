"""Manufacturer reference vectors, not real-hardware acceptance tests."""

import json
from pathlib import Path

import pytest

from custom_components.ifm_iolink.decoder import decode, validate_profile
from custom_components.ifm_iolink.version import installed_version

ROOT = Path(__file__).parents[1] / "custom_components/ifm_iolink"


@pytest.mark.parametrize("path", sorted((ROOT / "profiles").glob("*.json")), ids=lambda p: p.stem)
def test_all_bundled_profiles_are_valid(path):
    validate_profile(json.loads(path.read_text(encoding="utf-8")))


@pytest.mark.parametrize("flow,temperature,flags", [(10, 200, 0), (200, -100, 3), (123, 257, 1)])
def test_sv4200_reference_vectors(flow, temperature, flags):
    # ifm-0001E4-20231005-IODD1.1, pp. 3–4: big endian,
    # unsigned 16-bit flow x0.1; signed 14-bit temperature x0.1, two status bits.
    profile = json.loads((ROOT / "profiles/sv4200.json").read_text(encoding="utf-8"))
    raw = flow.to_bytes(2, "big") + (((temperature & 0x3FFF) << 2) | flags).to_bytes(2, "big")
    values = decode(profile, raw.hex())
    assert values["pd_1"] == pytest.approx(flow / 10)
    assert values["pd_2"] == pytest.approx(temperature / 10)
    assert values["pd_3"] == bool(flags & 2)
    assert values["pd_4"] == bool(flags & 1)
    assert profile["match"] == [{"vendorid": 310, "deviceid": 484}]
    assert not profile.get("parameters")
    assert not profile.get("commands")


@pytest.mark.parametrize("flow,temperature", [(241, 1200), (260, 1105), (241, -305), (260, -400)])
def test_sv4200_invalid_values_are_not_measurements(flow, temperature):
    profile = json.loads((ROOT / "profiles/sv4200.json").read_text(encoding="utf-8"))
    raw = flow.to_bytes(2, "big") + ((temperature & 0x3FFF) << 2).to_bytes(2, "big")
    values = decode(profile, raw.hex())
    assert values["pd_1"] is None
    assert values["pd_2"] is None


def test_installed_version_matches_manifest():
    assert installed_version() == json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))["version"]
