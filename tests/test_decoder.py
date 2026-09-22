import copy
import json
import struct
from pathlib import Path

import pytest

from custom_components.ifm_iolink.decoder import (
    decode,
    encode_command,
    encode_parameter,
    numeric_range,
    parameter_entity_kind,
    select_values,
    validate_profile,
)

ROOT = Path(__file__).resolve().parents[1]


def profile(name):
    return json.loads((ROOT / "custom_components/ifm_iolink/profiles" / (name + ".json")).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "path", sorted((ROOT / "custom_components/ifm_iolink/profiles").glob("*.json")), ids=lambda p: p.stem
)
def test_shipped_profiles_validate(path):
    validate_profile(json.loads(path.read_text(encoding="utf-8")))


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


def parameter(name, index):
    return next(p for p in profile(name)["parameters"] if p["index"] == index)


def test_parameter_entity_kind_writable_full_byte_int_is_number():
    p = parameter("pn7096_default", 500)  # rw UIntegerT, 1 full byte
    assert parameter_entity_kind(p) == "number"
    p = parameter("pn7096_default", 583)  # rw IntegerT, 2 full bytes, scaled
    assert parameter_entity_kind(p) == "number"


def test_parameter_entity_kind_read_only_is_sensor():
    assert parameter_entity_kind(parameter("pn7096_default", 560)) == "sensor"  # ro


def test_parameter_entity_kind_without_trivial_decoder_is_sensor():
    assert parameter_entity_kind(parameter("pn7096_default", 552)) == "sensor"  # RecordT, no decoder
    p = copy.deepcopy(parameter("pn7096_default", 500))
    p["decoder"]["fields"][0]["shift"] = 1  # partial-byte field
    p["decoder"]["fields"][0]["bits"] = 7
    assert parameter_entity_kind(p) == "sensor"


def test_encode_parameter_round_trips_and_matches_numeric_range():
    p = parameter("pn7096_default", 583)  # scale 0.01, signed 16 bit
    lo, hi = numeric_range(p["decoder"]["fields"][0])
    assert (lo, hi) == (-327.68, 327.67)
    raw = encode_parameter(p, 1.23)
    assert decode(p["decoder"], raw)["value"] == 1.23


def test_encode_parameter_rejects_out_of_range_and_non_writable():
    p = parameter("pn7096_default", 500)  # 0..255
    with pytest.raises(ValueError):
        encode_parameter(p, 256)
    with pytest.raises(ValueError):
        encode_parameter(parameter("pn7096_default", 560), 1)  # read-only


def test_min_max_narrows_the_writable_range_below_the_bit_width():
    p = copy.deepcopy(parameter("pn7096_default", 500))  # rw uint8, otherwise 0..255
    p["decoder"]["fields"][0].update(min=10, max=20)
    assert numeric_range(p["decoder"]["fields"][0]) == (10, 20)
    assert encode_parameter(p, 20) == "14"
    with pytest.raises(ValueError):
        encode_parameter(p, 21)
    with pytest.raises(ValueError):
        encode_parameter(p, 9)


def test_values_enum_is_a_select_not_a_number():
    # PG1406 index 802 (display brightness) is a uint8 but the device only accepts the fixed
    # steps 0/25/50/75/100, not a continuous range; writing e.g. 51 fails on real hardware with
    # ifm error code 531 even though it is well within the bit width.
    p = parameter("ifm_pg1406", 802)
    field = p["decoder"]["fields"][0]
    assert parameter_entity_kind(p) == "select"
    assert field["values"] == [0, 25, 50, 75, 100]
    assert select_values(field) == [0, 25, 50, 75, 100]
    assert encode_parameter(p, 75) == "4B"
    with pytest.raises(ValueError):
        encode_parameter(p, 51)


def test_values_are_scaled_like_a_number_field():
    p = copy.deepcopy(parameter("pn7096_default", 583))  # scale 0.01, signed 16 bit
    p["decoder"]["fields"][0]["values"] = [0, 50, 100]
    field = p["decoder"]["fields"][0]
    assert select_values(field) == [0, 0.5, 1.0]
    assert encode_parameter(p, 0.5) == "0032"
    with pytest.raises(ValueError):
        encode_parameter(p, 0.75)


@pytest.mark.parametrize(
    "changes",
    [
        {"min": 0, "max": 300},  # above the uint8 bit width
        {"min": 50, "max": 10},  # min > max
        {"min": 1.5, "max": 10},  # not an integer
        {"max": 100, "type": "bool"},  # min/max only allowed for uint/int
    ],
)
def test_reject_invalid_min_max_definitions(changes):
    p = copy.deepcopy(parameter("pn7096_default", 500))  # plain rw uint8, no min/max/values
    p["decoder"]["fields"][0].update(changes)
    with pytest.raises(ValueError):
        validate_profile(p["decoder"])


@pytest.mark.parametrize(
    "values",
    [
        [0, 25, 50, 75, 300],  # above the uint8 bit width
        [0, 25, 25, 75],  # duplicate
        [0, 25.5, 75],  # not an integer
        [],  # empty
    ],
)
def test_reject_invalid_values_definitions(values):
    p = copy.deepcopy(parameter("pn7096_default", 500))  # plain rw uint8, no min/max/values
    p["decoder"]["fields"][0]["values"] = values
    with pytest.raises(ValueError):
        validate_profile(p["decoder"])


def test_reject_values_on_non_integer_type():
    p = copy.deepcopy(parameter("pn7096_default", 500))
    p["decoder"]["fields"][0]["type"] = "bool"
    p["decoder"]["fields"][0]["values"] = [0, 1]
    with pytest.raises(ValueError):
        validate_profile(p["decoder"])


def test_commands_are_optional_and_default_to_empty():
    p = copy.deepcopy(profile("pn7096"))
    assert "commands" not in p
    validate_profile(p)  # no commands key at all is fine


def test_valid_command_round_trips():
    p = copy.deepcopy(profile("pn7096"))
    p["commands"] = [{"index": 2, "value": 1, "name": "Kalibrierung starten", "description": "Nullpunkt"}]
    validate_profile(p)
    assert encode_command(p["commands"][0]) == "01"
    assert encode_command({"value": 255}) == "FF"
    assert encode_command({"value": 0}) == "00"


@pytest.mark.parametrize(
    "changes",
    [
        {"index": -1},
        {"index": 65536},
        {"index": 1.5},
        {"value": -1},
        {"value": 256},
        {"value": 1.5},
        {"name": "x" * 4001},
        {"description": "x" * 4001},
        {"unexpected": "field"},
    ],
)
def test_reject_invalid_command_definitions(changes):
    p = copy.deepcopy(profile("pn7096"))
    command = {"index": 2, "value": 1, "name": "Kalibrierung starten", "description": "Nullpunkt"}
    command.update(changes)
    p["commands"] = [command]
    with pytest.raises(ValueError):
        validate_profile(p)


def test_allow_multiple_commands_sharing_one_index_with_different_values():
    # A single "system command" index commonly carries several named commands,
    # distinguished only by the value written to it (e.g. calibrate empty/full tank).
    p = copy.deepcopy(profile("pn7096"))
    p["commands"] = [
        {"index": 2, "value": 208, "name": "Leeren Tank abgleichen", "description": ""},
        {"index": 2, "value": 209, "name": "Vollen Tank abgleichen", "description": ""},
    ]
    validate_profile(p)


def test_reject_duplicate_command_index_and_value():
    p = copy.deepcopy(profile("pn7096"))
    p["commands"] = [
        {"index": 2, "value": 1, "name": "A", "description": ""},
        {"index": 2, "value": 1, "name": "B", "description": ""},
    ]
    with pytest.raises(ValueError):
        validate_profile(p)


def test_reject_too_many_commands():
    p = copy.deepcopy(profile("pn7096"))
    p["commands"] = [{"index": i, "value": 1, "name": str(i), "description": ""} for i in range(65)]
    with pytest.raises(ValueError):
        validate_profile(p)
