"""Preview-bound, sequential restore with device checks and a persisted progress report."""

import asyncio
from copy import deepcopy
from datetime import datetime, timezone

from .api import IfmError
from .parameters import read_identity, read_parameter_value


def hex_value(value, allow_empty=False):
    if not isinstance(value, str) or (not value and not allow_empty) or len(value) > 2048 or len(value) % 2:
        raise ValueError("Ungültiger Hexwert in der Sicherung")
    if any(char not in "0123456789abcdefABCDEF" for char in value):
        raise ValueError("Ungültiger Hexwert in der Sicherung")
    return value.upper()


def profile_for(coordinator, port):
    identifier = coordinator.entry.options.get("ports", {}).get(str(port), {}).get("profile")
    profile = coordinator.library.all.get(identifier)
    if not profile:
        raise ValueError("Zuerst ein passendes Geräteprofil zuweisen")
    return deepcopy(profile)


async def prepare_restore(coordinator, port, backup):
    if (
        not isinstance(backup, dict)
        or backup.get("kind") != "ifm_iolink_parameter_reference"
        or backup.get("schema_version") != 1
    ):
        raise ValueError("Keine unterstützte JSON-Parametersicherung")
    if backup.get("complete") is not True or backup.get("errors"):
        raise ValueError("Die Sicherung ist unvollständig")
    profile = profile_for(coordinator, port)
    identity = await read_identity(coordinator, port)
    if not identity.get("serial"):
        raise ValueError("Ohne lesbare Seriennummer ist keine sichere Geräteprüfung möglich")
    source = backup.get("device")
    if not isinstance(source, dict) or any(identity[k] != source.get(k) for k in ("vendorid", "deviceid")):
        raise ValueError("Hersteller-/Gerätekennung der Sicherung passt nicht zum Sensor")
    if backup.get("profile_id") != profile["id"]:
        raise ValueError("Geräteprofil der Sicherung passt nicht zur Portzuweisung")
    if not any(
        identity["vendorid"] == m["vendorid"] and identity["deviceid"] == m["deviceid"]
        for m in profile.get("match", [])
    ):
        raise ValueError("Das Profil braucht eine passende Hersteller-/Gerätekennung für Restore")
    values = backup.get("values")
    if not isinstance(values, dict) or not values or len(values) > 256:
        raise ValueError("Ungültige Parameterliste")
    parameters = {str(p["index"]): p for p in profile.get("parameters", [])}
    if len(parameters) != len(profile.get("parameters", [])):
        raise ValueError("Doppelte Parameterindizes im Geräteprofil")
    if set(values) != set(parameters):
        raise ValueError("Parameterliste wurde geändert; vollständige passende Sicherung verwenden")
    rows, skipped = [], []
    for key, parameter in parameters.items():
        item = values[key]
        if not isinstance(item, dict) or item.get("subindex", 0) != 0:
            raise ValueError("Ungültiger Parameter/Subindex")
        index = parameter["index"]
        reason = None
        if parameter.get("access") != "rw":
            reason = "Nur lesbar oder kein bestätigtes Schreibrecht"
        elif index < 64 and index not in (24, 25, 26):
            reason = "System-/Befehlsregister wird nicht zurückgeschrieben"
        elif parameter.get("datatype") not in (
            "StringT",
            "UIntegerT",
            "IntegerT",
            "BooleanT",
            "Float32T",
            "RecordT",
            "ArrayT",
        ):
            reason = "Nicht unterstützter Datentyp"
        if reason:
            skipped.append({"index": index, "name": parameter["name"], "reason": reason})
            continue
        is_string = parameter.get("datatype") == "StringT"
        desired = hex_value(item.get("raw"), allow_empty=is_string)
        current = await read_parameter_value(coordinator, port, parameter)
        before = hex_value(current["raw"], allow_empty=is_string)
        if not is_string and len(before) != len(desired):
            raise ValueError(f"Index {index}: Datenlänge passt nicht zum Ersatzgerät")
        # Decoder validates length, numerical encoding and invalid-value sentinels.
        if parameter.get("decoder"):
            from .decoder import decode

            if decode(parameter["decoder"], desired).get("value") is None:
                raise ValueError(f"Index {index}: ungültiger Parameterwert")
        rows.append(
            {
                "index": index,
                "name": parameter["name"],
                "before": before,
                "after": desired,
                "changed": before != desired,
            }
        )
    if not rows:
        raise ValueError("Keine unterstützten schreibbaren Parameter in der Sicherung")
    if await read_identity(coordinator, port) != identity or profile_for(coordinator, port) != profile:
        raise ValueError("Gerät oder Profil wurde während der Vorschau geändert")
    # PN sensor display locks are applied last. Threshold pairs may require a
    # lower reset point first when restoring a lower switch point.
    if identity["vendorid"] == 310 and identity["deviceid"] in (403, 404, 601, 602):
        for high, low in ((583, 584), (593, 594), (556, 555)):
            upper = next((r for r in rows if r["index"] == high), None)
            lower = next((r for r in rows if r["index"] == low), None)
            if upper and lower:
                lower_first = int.from_bytes(bytes.fromhex(upper["after"]), "big", signed=True) <= int.from_bytes(
                    bytes.fromhex(lower["before"]), "big", signed=True
                )
                first, second = (lower, upper) if lower_first else (upper, lower)
                rows.remove(first)
                rows.insert(rows.index(second), first)
        rows.sort(key=lambda row: row["index"] == 550)
    return {
        "target": identity,
        "port": port,
        "profile": profile,
        "source_created_at": backup.get("created_at"),
        "source_device": source,
        "rows": rows,
        "skipped": skipped,
    }


async def execute_restore(coordinator, port, plan, record, still_current=lambda: True):
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "checking",
        "target": plan["target"],
        "port": port,
        "source_created_at": plan["source_created_at"],
        "rows": deepcopy(plan["rows"]),
        "skipped": plan["skipped"],
        "verified": [],
        "pending": [r["index"] for r in plan["rows"] if r["changed"]],
        "error": None,
    }
    parameters = {p["index"]: p for p in plan["profile"]["parameters"]}

    async def check_target():
        if (
            not still_current()
            or profile_for(coordinator, port) != plan["profile"]
            or await read_identity(coordinator, port) != plan["target"]
        ):
            raise ValueError("Gerät, Master oder Profil hat sich seit der Vorschau geändert")

    try:
        await check_target()
        # Abort before any write if the preview no longer reflects live settings.
        for row in plan["rows"]:
            current = await read_parameter_value(coordinator, port, parameters[row["index"]])
            if hex_value(current["raw"], allow_empty=True) != row["before"]:
                raise ValueError(f"Index {row['index']}: Wert seit Vorschau geändert; neue Vorschau erstellen")
        report["status"] = "running"
        await record(deepcopy(report))  # Persist original values before sending any write.
        deadline = asyncio.get_running_loop().time() + 90
        for row in plan["rows"]:
            if not row["changed"]:
                continue
            if asyncio.get_running_loop().time() > deadline:
                raise ValueError("Zeitlimit erreicht; keine weiteren Parameter geschrieben")
            await check_target()
            index = row["index"]
            current = await read_parameter_value(coordinator, port, parameters[index])
            if hex_value(current["raw"], allow_empty=True) != row["before"]:
                raise ValueError(f"Index {index}: Wert zwischenzeitlich geändert")
            report["in_flight"] = index
            await record(deepcopy(report))
            await coordinator.client.write_parameter(port, index, row["after"])
            await check_target()
            actual = await read_parameter_value(coordinator, port, parameters[index])
            if hex_value(actual["raw"], allow_empty=True) != row["after"]:
                raise ValueError(f"Index {index}: Rücklesewert stimmt nicht überein")
            report["verified"].append(index)
            report["pending"].remove(index)
            report.pop("in_flight", None)
            await record(deepcopy(report))
        await check_target()
        for row in plan["rows"]:
            actual = await read_parameter_value(coordinator, port, parameters[row["index"]])
            if hex_value(actual["raw"], allow_empty=True) != row["after"]:
                raise ValueError(f"Index {row['index']}: Abschlussprüfung fehlgeschlagen")
        report["status"] = "completed"
    except (ValueError, IfmError, OSError) as err:
        report["status"] = "stopped"
        report["error"] = str(err)
    await record(deepcopy(report))
    coordinator.condition_values.clear()
    coordinator.metadata_at = None
    return report
