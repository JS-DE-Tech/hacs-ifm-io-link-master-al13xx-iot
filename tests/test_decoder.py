import copy
import json
import struct
from pathlib import Path

import pytest

from custom_components.ifm_iolink.decoder import decode, validate_profile

ROOT = Path(__file__).resolve().parents[1]


def profile(name):
    return json.loads((ROOT / "custom_components/ifm_iolink/profiles" / (name + ".json")).read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", ["pn7094", "pn7096", "pn7094_default", "pn7096_default", "badu_flowsonic_plus"])
def test_shipped_profiles_validate(name):
    validate_profile(profile(name))


def test_live_pn7096_samples_and_switches():
    assert decode(profile("pn7096"), "08980101") == {"pd_1": 0.22, "pd_2": 0, "pd_3": False, "pd_4": True}
    assert decode(profile("pn7096"), "4E5C0100")["pd_1"] == 2.006


def test_live_pn7094_samples():
    p = profile("pn7094")
    assert decode(p, "00000201")["pd_1"] == 0
    assert decode(p, "014F0201")["pd_1"] == 0.335
    assert decode(p, "1BE40200")["pd_1"] == 7.14


def test_signed_default_and_status_bits():
    word = ((-100 & 0x3FFF) << 2) | 3
    result = decode(profile("pn7094_default"), f"{word:04X}")
    assert result == {"pd_1": -1.0, "pd_2": True, "pd_3": True}
    assert decode(profile("pn7094"), "FC180030")["pd_1"] == -1.0
    assert decode(profile("pn7094"), "FC180030")["pd_2"] == 3


@pytest.mark.parametrize("raw", ["7FF80000", "7FFC0000", "80080000"])
def test_iodd_special_values_unavailable(raw):
    assert decode(profile("pn7096"), raw)["pd_1"] is None


def test_badu_layout_and_invalid_flags():
    raw = struct.pack(">fffffH", 4.25, 23.5, 123, 1000, 999, 0).hex()
    result = decode(profile("badu_flowsonic_plus"), raw)
    assert [result[k] for k in ("flow", "temperature", "totalizer1", "totalizer2")] == [4.25, 23.5, 1000, 999]
    bad = raw[:-4] + "030C"
    result = decode(profile("badu_flowsonic_plus"), bad)
    assert result["flow"] is None and result["temperature"] is None
    assert result["batch_error"] and result["configuration_error"]
    assert result["system_error"]


def test_badu_uses_user_confirmed_nodered_status_mapping():
    p = profile("badu_flowsonic_plus")
    for bit, key in [
        (5, "empty_pipe"),
        (6, "air_bubbles"),
        (7, "batch_active"),
        (8, "batch_error"),
        (9, "configuration_error"),
        (10, "calibration_error"),
    ]:
        values = decode(p, "00" * 20 + f"{1 << bit:04X}")
        assert values[key] is True
        assert values["system_error"] is True
    assert decode(p, "00" * 20 + "0010")["system_error"] is False


def test_live_badu_sample():
    result = decode(profile("badu_flowsonic_plus"), "408D8DEF419E7EE87DB48E52474F27C6474F27B90010")
    assert result["flow"] == 4.424
    assert result["temperature"] == 19.812


@pytest.mark.parametrize("raw", ["", "0898", "0898010100", "0898zz01", " 08980101", "0898010"])
def test_reject_corrupt_or_wrong_mode_packets(raw):
    with pytest.raises(ValueError):
        decode(profile("pn7096"), raw)


def test_nan_not_a_sensor_value():
    raw = struct.pack(">fffffH", float("nan"), 20, 0, 1, 2, 0).hex()
    assert decode(profile("badu_flowsonic_plus"), raw)["flow"] is None


@pytest.mark.parametrize(
    "changes",
    [
        {"offset": 32},
        {"length": 99},
        {"scale": float("inf")},
        {"bits": 0},
        {"shift": -1},
        {"key": "bad-id"},
        {"type": "python"},
        {"device_class": "problem"},
        {"precision": -1},
    ],
)
def test_reject_invalid_field_definitions(changes):
    p = copy.deepcopy(profile("pn7096"))
    p["fields"][0].update(changes)
    with pytest.raises(ValueError):
        validate_profile(p)


@pytest.mark.parametrize(
    "image",
    [
        "javascript:alert(1)",
        "data:image/svg+xml,<svg onload='alert(1)'/>",
        "//attacker.example/test",
        "/local/../secrets.yaml",
    ],
)
def test_reject_unsafe_images(image):
    p = profile("pn7096")
    p["image"] = image
    with pytest.raises(ValueError):
        validate_profile(p)
@pytest.mark.parametrize("image", ["", "/local/relay.png", "data:image/png;base64,aGVsbG8="])
def test_digital_device_needs_no_process_layout(image):
    profile = {"id": "custom_relay", "kind": "digital", "name": "Schütz",
               "image": image, "length": 0, "fields": []}
    assert validate_profile(profile, custom=True) == profile


@pytest.mark.parametrize("extra", [{"length": 1}, {"fields": [{"key": "value"}]},
                                  {"parameters": [{}]}, {"conditions": [{}]}, {"match": [{}]},
                                  {"kind": "script"}, {"image": "javascript:alert(1)"}])
def test_digital_device_rejects_process_commands_and_unsafe_images(extra):
    with pytest.raises(ValueError):
        validate_profile({"id": "custom_relay", "kind": "digital", "name": "Schütz",
                          "length": 0, "fields": [], **extra}, custom=True)
