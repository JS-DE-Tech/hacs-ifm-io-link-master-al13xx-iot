"""Bounded, declarative process-data decoder. Never executes supplied code."""

from __future__ import annotations

import math
import re
import struct
from urllib.parse import urlsplit

TYPES = {"uint": None, "int": None, "float32": 4, "float64": 8, "bool": None}
PROFILE_KEYS = {
    "id",
    "name",
    "manufacturer",
    "model",
    "description",
    "purpose",
    "image",
    "notes",
    "source",
    "match",
    "fields",
    "length",
    "parameters",
    "conditions",
    "commands",
}
FIELD_KEYS = {
    "key",
    "name",
    "type",
    "offset",
    "length",
    "endian",
    "shift",
    "bits",
    "scale",
    "add",
    "unit",
    "device_class",
    "state_class",
    "invalid_values",
    "invalid_when",
    "precision",
    "mask",
    "min",
    "max",
    "values",
}


def safe_image(value: str) -> bool:
    """Allow local images, HTTPS pictures, or bounded raster uploads."""
    if not isinstance(value, str) or len(value) > 1_500_000:
        return False
    if not value:
        return True
    if value.startswith(("/local/", "/ifm_iolink_static/")):
        return not any(c in value for c in ("..", "\\", "\n", "\r"))
    if re.fullmatch(r"data:image/(?:png|jpeg|webp);base64,[A-Za-z0-9+/=]+", value):
        return True
    url = urlsplit(value)
    return url.scheme == "https" and bool(url.netloc) and not url.username and not url.password


def _integer(value, minimum, maximum, label):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{label}: Ganzzahl zwischen {minimum} und {maximum} erforderlich")


def validate_profile(profile: dict, *, custom: bool = False) -> dict:
    """Reject malformed layouts at the boundary, before persisting them."""
    if not isinstance(profile, dict) or set(profile) - PROFILE_KEYS:
        raise ValueError("Unbekannte Profilfelder")
    identifier = profile.get("id", "")
    if not isinstance(identifier, str) or not re.fullmatch(r"[a-z][a-z0-9_]{1,63}", identifier):
        raise ValueError("Profil-ID: 2–64 Kleinbuchstaben, Ziffern oder Unterstriche")
    if custom and not identifier.startswith("custom_"):
        raise ValueError("Eigene Profil-IDs müssen mit custom_ beginnen")
    for key in ("name", "manufacturer", "model", "description", "purpose", "notes", "source"):
        value = profile.get(key, "")
        if not isinstance(value, str) or len(value) > 4000:
            raise ValueError(f"{key}: Text mit höchstens 4000 Zeichen erforderlich")
    if not profile.get("name", "").strip():
        raise ValueError("Gerätename fehlt")
    if not safe_image(profile.get("image", "")):
        raise ValueError("Bild: /local/-Pfad, HTTPS-URL oder PNG/JPEG/WebP-Upload erforderlich")
    _integer(profile.get("length"), 1, 32, "Prozessdatenlänge")
    matches = profile.get("match", [])
    if not isinstance(matches, list) or len(matches) > 32:
        raise ValueError("match muss eine Liste sein")
    for match in matches:
        if not isinstance(match, dict) or set(match) != {"vendorid", "deviceid"}:
            raise ValueError("match benötigt vendorid und deviceid")
        _integer(match["vendorid"], 0, 65535, "vendorid")
        _integer(match["deviceid"], 0, 16777215, "deviceid")
    fields = profile.get("fields")
    if not isinstance(fields, list) or not 1 <= len(fields) <= 64:
        raise ValueError("1–64 Parameter erforderlich")
    seen = set()
    for field in fields:
        if not isinstance(field, dict) or set(field) - FIELD_KEYS:
            raise ValueError("Unbekannte Parameterfelder")
        key = field.get("key", "")
        if not isinstance(key, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", key) or key in seen:
            raise ValueError("Parameter-IDs müssen gültig und eindeutig sein")
        seen.add(key)
        if field.get("type") not in TYPES:
            raise ValueError("Typ muss uint, int, float32, float64 oder bool sein")
        for label in ("name", "unit", "device_class", "state_class"):
            if not isinstance(field.get(label, ""), str) or len(field.get(label, "")) > 128:
                raise ValueError(f"{key}: ungültiges Feld {label}")
        if field.get("device_class", "") not in {
            "",
            "pressure",
            "temperature",
            "volume",
            "volume_flow_rate",
            "voltage",
            "current",
            "power",
            "energy",
            "humidity",
            "distance",
            "problem",
            "running",
            "connectivity",
        }:
            raise ValueError(f"{key}: unbekannte Geräteklasse")
        if field.get("state_class", "") not in {"", "measurement", "total", "total_increasing"}:
            raise ValueError(f"{key}: unbekannte Zustandsklasse")
        binary_classes = {"problem", "running", "connectivity"}
        if (
            field["type"] == "bool"
            and (
                field.get("device_class", "") not in binary_classes | {""}
                or field.get("unit")
                or field.get("state_class")
            )
        ) or (field["type"] != "bool" and field.get("device_class") in binary_classes):
            raise ValueError(f"{key}: Geräteklasse passt nicht zum Datentyp")
        size = field.get("length", TYPES[field["type"]] or 1)
        _integer(size, 1, 8, f"{key}.length")
        _integer(field.get("offset"), 0, 31, f"{key}.offset")
        if field["offset"] + size > profile["length"]:
            raise ValueError(f"{key}: Parameter liegt außerhalb der Prozessdaten")
        if TYPES[field["type"]] and size != TYPES[field["type"]]:
            raise ValueError(f"{key}: falsche Float-Länge")
        if field.get("endian", "big") not in ("big", "little"):
            raise ValueError(f"{key}: endian muss big oder little sein")
        shift = field.get("shift", 0)
        _integer(shift, 0, size * 8 - 1, f"{key}.shift")
        _integer(field.get("bits", size * 8 - shift), 1, size * 8 - shift, f"{key}.bits")
        if TYPES[field["type"]] and (shift or field.get("bits", size * 8) != size * 8):
            raise ValueError(f"{key}: Float benötigt vollständige Bytes")
        for number in ("scale", "add"):
            value = field.get(number, 1 if number == "scale" else 0)
            if type(value) not in (float, int) or not math.isfinite(value):
                raise ValueError(f"{key}.{number}: endliche Zahl erforderlich")
        _integer(field.get("precision", 3), 0, 8, f"{key}.precision")
        if "mask" in field:
            if field["type"] != "bool":
                raise ValueError("mask wird nur für binäre Sammelmeldungen unterstützt")
            _integer(field["mask"], 1, (1 << (size * 8 - shift)) - 1, f"{key}.mask")
        if "min" in field or "max" in field:
            # Raw-value bounds narrower than the bit width, e.g. a device accepting only 0-100 of a uint8.
            if field["type"] not in ("uint", "int"):
                raise ValueError(f"{key}: min/max nur für uint oder int erlaubt")
            bits = field.get("bits", size * 8 - shift)
            bit_lo, bit_hi = (-(1 << (bits - 1)), (1 << (bits - 1)) - 1) if field["type"] == "int" else (0, (1 << bits) - 1)
            lo, hi = field.get("min", bit_lo), field.get("max", bit_hi)
            if type(lo) is not int or type(hi) is not int or not bit_lo <= lo <= hi <= bit_hi:
                raise ValueError(f"{key}: min/max müssen ganzzahlig sein, im Wertebereich liegen und min <= max erfüllen")
        if "values" in field:
            # A fixed set of accepted raw values, e.g. a 0/25/50/75/100 brightness enum rather than a range.
            if field["type"] not in ("uint", "int"):
                raise ValueError(f"{key}: values nur für uint oder int erlaubt")
            bits = field.get("bits", size * 8 - shift)
            bit_lo, bit_hi = (-(1 << (bits - 1)), (1 << (bits - 1)) - 1) if field["type"] == "int" else (0, (1 << bits) - 1)
            values = field["values"]
            if (
                not isinstance(values, list)
                or not 1 <= len(values) <= 64
                or len(set(values)) != len(values)
                or any(type(v) is not int or not bit_lo <= v <= bit_hi for v in values)
            ):
                raise ValueError(f"{key}: values muss eine Liste eindeutiger Ganzzahlen im Wertebereich sein")
        invalid = field.get("invalid_values", [])
        if (
            not isinstance(invalid, list)
            or len(invalid) > 32
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in invalid)
        ):
            raise ValueError(f"{key}: ungültige Fehlerwerte")
        condition = field.get("invalid_when")
        if condition is not None:
            if not isinstance(condition, dict) or set(condition) != {"offset", "mask"}:
                raise ValueError(f"{key}: invalid_when benötigt offset und mask")
            _integer(condition["offset"], 0, profile["length"] - 1, "invalid_when.offset")
            _integer(condition["mask"], 1, 255, "invalid_when.mask")
    conditions = profile.get("conditions", [])
    if not isinstance(conditions, list) or len(conditions) > 8:
        raise ValueError("Maximal 8 Profilbedingungen")
    for condition in conditions:
        if not isinstance(condition, dict) or set(condition) != {"index", "value"}:
            raise ValueError("Profilbedingung benötigt index und value")
        _integer(condition["index"], 0, 65535, "Bedingungsindex")
        _integer(condition["value"], 0, 4294967295, "Bedingungswert")
    parameters = profile.get("parameters", [])
    if not isinstance(parameters, list) or len(parameters) > 256:
        raise ValueError("Maximal 256 Parameterdefinitionen erlaubt")
    for parameter in parameters:
        if not isinstance(parameter, dict) or set(parameter) - {
            "index",
            "name",
            "description",
            "access",
            "datatype",
            "default",
            "decoder",
        }:
            raise ValueError("Ungültige Parameterdefinition")
        _integer(parameter.get("index"), 0, 65535, "Parameterindex")
        for key in ("name", "description", "access", "datatype", "default"):
            if not isinstance(parameter.get(key, ""), str) or len(parameter.get(key, "")) > 4000:
                raise ValueError("Ungültiger Parametertext")
        if "decoder" in parameter:
            if not isinstance(parameter["decoder"], dict) or "parameters" in parameter["decoder"]:
                raise ValueError("Verschachtelte Parameter sind nicht erlaubt")
            validate_profile(parameter["decoder"])
    commands = profile.get("commands", [])
    if not isinstance(commands, list) or len(commands) > 64:
        raise ValueError("Maximal 64 Kommandos erlaubt")
    seen_commands = set()
    for command in commands:
        if not isinstance(command, dict) or set(command) - {"index", "name", "description", "value"}:
            raise ValueError("Ungültige Kommandodefinition")
        _integer(command.get("index"), 0, 65535, "Kommandoindex")
        _integer(command.get("value"), 0, 255, "Kommandowert")
        # Several named commands commonly share one "system command" index with distinct
        # values (e.g. calibrate-empty/calibrate-full) - only the (index, value) pair must
        # be unique, not the index alone.
        key = (command["index"], command["value"])
        if key in seen_commands:
            raise ValueError("Kommando (Index + Wert) muss innerhalb des Profils eindeutig sein")
        seen_commands.add(key)
        for label in ("name", "description"):
            if not isinstance(command.get(label, ""), str) or len(command.get(label, "")) > 4000:
                raise ValueError("Ungültiger Kommandotext")
    return profile


def decode(profile: dict, hex_data: str) -> dict:
    """Decode exact-length PDIN; invalid individual measurements become None."""
    if (
        not isinstance(hex_data, str)
        or not re.fullmatch(r"[0-9a-fA-F]+", hex_data)
        or len(hex_data) != profile["length"] * 2
    ):
        raise ValueError(f"Erwartet: {profile['length']} Byte Hex-Prozessdaten")
    payload = bytes.fromhex(hex_data)
    result = {}
    for field in profile["fields"]:
        kind = field["type"]
        size = field.get("length", TYPES[kind] or 1)
        chunk = payload[field["offset"] : field["offset"] + size]
        endian = field.get("endian", "big")
        if kind.startswith("float"):
            raw = struct.unpack((">" if endian == "big" else "<") + ("f" if kind == "float32" else "d"), chunk)[0]
        else:
            shift = field.get("shift", 0)
            bits = field.get("bits", size * 8 - shift)
            raw = (int.from_bytes(chunk, endian) >> shift) & ((1 << bits) - 1)
            if kind == "int" and raw & (1 << (bits - 1)):
                raw -= 1 << bits
        condition = field.get("invalid_when")
        if (
            not math.isfinite(raw)
            or raw in field.get("invalid_values", [])
            or (condition and payload[condition["offset"]] & condition["mask"])
        ):
            value = None
        elif kind == "bool":
            value = bool(raw & field.get("mask", (1 << (size * 8)) - 1))
        else:
            value = raw * field.get("scale", 1) + field.get("add", 0)
            value = round(value, field.get("precision", 3)) if math.isfinite(value) else None
        result[field["key"]] = value
    return result


def parameter_entity_kind(parameter: dict) -> str:
    """'select' for a fixed set of accepted values, 'number' for a writable range, else 'sensor'."""
    decoder = parameter.get("decoder")
    if not decoder or len(decoder.get("fields", [])) != 1:
        return "sensor"
    field = decoder["fields"][0]
    if field["type"] not in ("uint", "int") or parameter.get("access") != "rw":
        return "sensor"
    size = field.get("length", TYPES[field["type"]] or 1)
    trivial = field.get("offset", 0) == 0 and field.get("shift", 0) == 0 and field.get("bits", size * 8) == size * 8
    if not trivial:
        return "sensor"
    return "select" if "values" in field else "number"


def _raw_bounds(field: dict) -> tuple[int, int]:
    """Raw-value bounds: the field's explicit min/max if given, else the full bit width."""
    size = field.get("length", TYPES[field["type"]] or 1)
    bits = field.get("bits", size * 8)
    bit_lo, bit_hi = (-(1 << (bits - 1)), (1 << (bits - 1)) - 1) if field["type"] == "int" else (0, (1 << bits) - 1)
    return field.get("min", bit_lo), field.get("max", bit_hi)


def numeric_range(field: dict) -> tuple[float, float]:
    """Value bounds for a full-byte int/uint field, after scale and add."""
    scale = field.get("scale", 1)
    add = field.get("add", 0)
    lo, hi = _raw_bounds(field)
    bounds = (lo * scale + add, hi * scale + add)
    return min(bounds), max(bounds)


def encode_parameter(parameter: dict, value) -> str:
    """Encode a number into the raw hex for a writable full-byte int/uint parameter."""
    if parameter_entity_kind(parameter) not in ("number", "select"):
        raise ValueError("Parameter unterstützt keine Zahlenkodierung")
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("Ungültiger Zahlenwert")
    field = parameter["decoder"]["fields"][0]
    size = field.get("length", TYPES[field["type"]] or 1)
    scale = field.get("scale", 1)
    add = field.get("add", 0)
    raw = round((value - add) / scale) if scale else int(value)
    if "values" in field:
        if raw not in field["values"]:
            raise ValueError("Wert ist keine gültige Auswahl für diesen Parameter")
    else:
        lo, hi = _raw_bounds(field)
        if not lo <= raw <= hi:
            raise ValueError("Wert außerhalb des zulässigen Bereichs")
    return raw.to_bytes(size, field.get("endian", "big"), signed=(field["type"] == "int")).hex().upper()


def encode_command(command: dict) -> str:
    """Encode a command's fixed value as the single raw byte IO-Link expects (uint8, subindex 0)."""
    return command["value"].to_bytes(1, "big").hex().upper()


def select_values(field: dict) -> list[float]:
    """The field's fixed accepted values, scaled to the exposed value domain."""
    scale = field.get("scale", 1)
    add = field.get("add", 0)
    return [raw * scale + add for raw in field["values"]]
