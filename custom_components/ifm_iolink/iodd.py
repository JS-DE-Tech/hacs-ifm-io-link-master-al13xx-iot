"""Import a bounded subset of IODD 1.1 without extracting ZIPs or executing XML."""

from __future__ import annotations

import base64
import math
import re
import zipfile
from io import BytesIO
from pathlib import PurePosixPath
from xml.etree import ElementTree as ET

from .decoder import validate_profile

NS = {"i": "http://www.io-link.com/IODD/2010/10"}
XSI = "{http://www.w3.org/2001/XMLSchema-instance}type"
# IODD standard unit codes used by the supplied manufacturer files.
UNITS = {
    "1001": ("°C", "temperature"),
    "1036": ("m³", "volume"),
    "1054": ("s", ""),
    "1137": ("bar", "pressure"),
    "1132": ("MPa", "pressure"),
    "1133": ("kPa", "pressure"),
    "1141": ("psi", "pressure"),
}
TYPES = {"IntegerT": "int", "UIntegerT": "uint", "BooleanT": "bool", "Float32T": "float32", "Float64T": "float64"}


def xml_root(raw):
    if len(raw) > 4_000_000:
        raise ValueError("XML-Datei zu groß")
    # Reject declarations even in UTF-16. No DTDs/entities or external resolution.
    text = raw.decode("utf-8-sig", errors="strict")
    if re.search(r"<!\s*(DOCTYPE|ENTITY)", text, re.I):
        raise ValueError("XML mit DTD/Entities wird nicht importiert")
    return ET.fromstring(text)


def datatype(node, datatypes):
    for tag in ("Datatype", "SimpleDatatype"):
        result = node.find(f"i:{tag}", NS)
        if result is not None:
            return result
    for tag in ("DatatypeRef", "SimpleDatatypeRef"):
        ref = node.find(f"i:{tag}", NS)
        if ref is not None:
            return datatypes.get(ref.get("datatypeId"))
    return None


def import_iodd(raw: bytes, filename: str = "device.zip") -> list[dict]:
    """Return editable profile candidates, including variant pictures and warnings."""
    if len(raw) > 8_000_000:
        raise ValueError("IODD-Upload darf höchstens 8 MB enthalten")
    files = {}
    if zipfile.is_zipfile(BytesIO(raw)):
        with zipfile.ZipFile(BytesIO(raw)) as archive:
            entries = archive.infolist()
            if len(entries) > 200 or sum(item.file_size for item in entries) > 24_000_000:
                raise ValueError("Zu viele oder zu große Dateien im ZIP")
            for item in entries:
                path = PurePosixPath(item.filename)
                if path.is_absolute() or ".." in path.parts or "\\" in item.filename or item.flag_bits & 1:
                    raise ValueError("Ungültiger ZIP-Pfad oder verschlüsseltes ZIP")
                if path.suffix.lower() in (".xml", ".png", ".jpg", ".jpeg", ".webp"):
                    if item.file_size > 4_000_000:
                        raise ValueError("Einzeldatei zu groß")
                    files[item.filename] = archive.read(item)
    else:
        files[PurePosixPath(filename).name] = raw
    xmls = {name: xml_root(content) for name, content in files.items() if name.lower().endswith(".xml")}
    roots = {name: root for name, root in xmls.items() if root.tag == f"{{{NS['i']}}}IODevice"}
    if not roots:
        raise ValueError("Keine unterstützte IODD 1.1 gefunden (XML oder Hersteller-ZIP hochladen)")
    candidates = []
    for name, root in roots.items():
        identity = root.find(".//i:DeviceIdentity", NS)
        if identity is None:
            raise ValueError("Gerätekennung fehlt")
        vendor, device = int(identity.get("vendorId")), int(identity.get("deviceId"))
        texts = {n.get("id"): n.get("value", "") for n in root.findall(".//i:Text", NS)}
        localized = xmls.get(name[:-4] + "-de.xml")
        if localized is not None:
            texts.update({n.get("id"): n.get("value", "") for n in localized.findall(".//i:Text", NS)})

        def label(node, tag="Name", texts=texts):
            child = node.find(f"i:{tag}", NS)
            return texts.get(child.get("textId"), "") if child is not None else ""

        datatypes = {n.get("id"): n for n in root.findall(".//i:DatatypeCollection/i:Datatype", NS)}
        refs = root.findall(".//i:RecordItemRef", NS) + root.findall(".//i:VariableRef", NS)
        dynamic_menus = bool(root.findall(".//i:MenuRef/i:Condition", NS))

        def presentation(variable, subindex=None, refs=refs, dynamic_menus=dynamic_menus):
            available = [
                r.attrib
                for r in refs
                if r.get("variableId") == variable
                and r.get("subindex") == subindex
                and any(key in r.attrib for key in ("gradient", "unitCode", "offset"))
            ]
            # Explicitly prefer bar where the IODD offers alternate pressure units.
            available.sort(key=lambda r: (r.get("unitCode") != "1137", r.get("unitCode") not in UNITS))
            if dynamic_menus and len({r.get("unitCode") for r in available}) > 1:
                to_bar = {"1137": 1, "1132": 10, "1133": 0.01, "1141": 0.0689475729}
                if any(r.get("unitCode") not in to_bar for r in available):
                    return {}
                scales = [float(r.get("gradient", 1)) * to_bar[r["unitCode"]] for r in available]
                offsets = [float(r.get("offset", 0)) * to_bar[r["unitCode"]] for r in available]
                if any(not math.isclose(s, scales[0], rel_tol=0.005, abs_tol=1e-10) for s in scales) or any(
                    not math.isclose(o, offsets[0], rel_tol=0.005, abs_tol=1e-10) for o in offsets
                ):
                    return {}
            return available[0] if available else {}

        def field_from(node, dtype, total_bits, offset, key, display, warnings, is_parameter=False):
            kind = dtype.get(XSI, "").split(":")[-1] if dtype is not None else ""
            if kind not in TYPES:
                warnings.append(f"{label(node) or key}: Datentyp {kind or 'unbekannt'} nicht unterstützt")
                return None
            bits = int(dtype.get("bitLength", {"BooleanT": "1", "Float32T": "32", "Float64T": "64"}.get(kind, "0")))
            start = total_bits - offset - bits
            if bits < 1 or bits > 64 or start < 0 or (kind.startswith("Float") and (start % 8 or bits % 8)):
                warnings.append(f"{key}: nicht unterstützte Bitanordnung")
                return None
            size = math.ceil((start % 8 + bits) / 8)
            field = {
                "key": key,
                "name": label(node) or key,
                "type": TYPES[kind],
                "offset": start // 8,
                "length": size,
                "shift": size * 8 - start % 8 - bits,
                "bits": bits,
                "precision": 3 if kind.startswith("Float") else 0,
            }
            if display:
                field["scale"] = float(display.get("gradient", 1))
                field["add"] = float(display.get("offset", 0))
                unit = display.get("unitCode")
                if unit in UNITS:
                    field["unit"], field["device_class"] = UNITS[unit]
                    field["state_class"] = "total" if field["device_class"] == "volume" else "measurement"
                elif unit:
                    warnings.append(f"{key}: Einheitencode {unit} noch nicht übersetzt; Einheit im Profil ergänzen")
                # Preserve actual resolution even if the IODD display rounds it.
                scale = abs(field["scale"])
                precision = min(8, max(0, -math.floor(math.log10(scale)))) if scale else 3
                field["precision"] = max(field["precision"], precision)
            elif kind not in ("BooleanT", "UIntegerT"):
                warnings.append(f"{key}: keine Skalierung/Einheit in der IODD-Darstellung gefunden; Rohwert prüfen")
            ranges = dtype.findall("i:ValueRange", NS)
            if ranges and kind != "BooleanT":
                exceptions = [float(n.get("value")) for n in dtype.findall("i:SingleValue", NS)]
                field["invalid_values"] = [
                    v
                    for v in exceptions
                    if not any(float(r.get("lowerValue")) <= v <= float(r.get("upperValue")) for r in ranges)
                ]
                if is_parameter and kind in ("UIntegerT", "IntegerT"):
                    # Raw-domain bounds, e.g. a device only accepting 0-100 of a wider uint field.
                    # Parameter fields are always the full, unshifted type width, unlike packed PDIN sub-fields,
                    # so the IODD's range always fits the field's own bit width here.
                    field["min"] = int(round(min(float(r.get("lowerValue")) for r in ranges)))
                    field["max"] = int(round(max(float(r.get("upperValue")) for r in ranges)))
            else:
                singles = dtype.findall("i:SingleValue", NS)
                if is_parameter and singles and kind in ("UIntegerT", "IntegerT"):
                    # No ValueRange at all: the SingleValues are the complete, fixed set of accepted
                    # values (e.g. a 0/25/50/75/100 percentage enum), not exceptions within a range.
                    field["values"] = sorted({int(round(float(n.get("value")))) for n in singles})
            return field

        parameters = []
        for variable in root.findall(".//i:VariableCollection/i:Variable", NS):
            if variable.get("accessRights") == "wo":
                continue
            param = {
                "index": int(variable.get("index")),
                "name": label(variable) or variable.get("id"),
                "description": label(variable, "Description"),
                "access": variable.get("accessRights", "ro"),
            }
            dtype = datatype(variable, datatypes)
            param["datatype"] = dtype.get(XSI, "").split(":")[-1] if dtype is not None else "unknown"
            param["default"] = variable.get("defaultValue", "")
            display = presentation(variable.get("id"))
            if dtype is not None and param["datatype"] in TYPES:
                bits = int(dtype.get("bitLength", "1" if param["datatype"] == "BooleanT" else "32"))
                total = math.ceil(bits / 8) * 8
                field = field_from(variable, dtype, total, 0, "value", display, [], is_parameter=True)
                if field:
                    param["decoder"] = {
                        "id": "parameter_value",
                        "name": param["name"],
                        "length": total // 8,
                        "fields": [field],
                    }
            parameters.append(param)

        layouts = root.findall(".//i:ProcessDataCollection/i:ProcessData", NS)
        for layout_index, layout in enumerate(layouts):
            pdin = layout.find("i:ProcessDataIn", NS)
            if pdin is None:
                continue
            total_bits = int(pdin.get("bitLength"))
            if not 1 <= total_bits <= 256 or total_bits % 8:
                raise ValueError("Prozessdatenlänge wird nicht unterstützt")
            dtype = datatype(pdin, datatypes)
            if dtype is None:
                raise ValueError("Prozessdatentyp fehlt")
            warnings, fields = [], []
            conditions = []
            condition = layout.find("i:Condition", NS)
            if condition is not None:
                variable = root.find(f".//i:Variable[@id='{condition.get('variableId')}']", NS)
                if variable is None or not condition.get("value", "").isdigit():
                    raise ValueError("Bedingtes Layout mit nicht unterstützter Bedingung")
                conditions.append({"index": int(variable.get("index")), "value": int(condition.get("value"))})
            if len(layouts) > 1 or layout.find("i:Condition", NS) is not None:
                warnings.append("Bedingtes Prozessdatenlayout: aktiven Gerätemodus vor Zuweisung prüfen")
            direct_ref = root.find(f".//i:ProcessDataRef[@processDataId='{pdin.get('id')}']", NS)
            items = dtype.findall("i:RecordItem", NS)
            if not items:
                items = [pdin]
            for number, item in enumerate(items, 1):
                simple = datatype(item, datatypes) if item is not pdin else dtype
                subindex = item.get("subindex")
                display = {}
                if direct_ref is not None:
                    info = (
                        direct_ref.find(f"i:ProcessDataRecordItemInfo[@subindex='{subindex}']", NS)
                        if subindex
                        else direct_ref
                    )
                    if info is not None:
                        display = dict(info.attrib)
                else:
                    display = presentation("V_ProcessDataInput", subindex) or presentation(pdin.get("id"), subindex)
                if (
                    dynamic_menus
                    and not display.get("unitCode")
                    and simple is not None
                    and simple.get(XSI) in ("Float32T", "Float64T", "IntegerT")
                ):
                    warnings.append(
                        f"pd_{subindex or number}: Einheit hängt von Geräteeinstellungen ab. Unbeschrifteter Rohwert; Einheit und passende Index-Bedingung ergänzen."
                    )
                field = field_from(
                    item,
                    simple,
                    total_bits,
                    int(item.get("bitOffset", "0")),
                    f"pd_{subindex or number}",
                    display,
                    warnings,
                )
                if field:
                    fields.append(field)
            if not fields:
                raise ValueError("Keine unterstützten Prozessdatenfelder; Debug-Export und eigenes Profil verwenden")
            variants = identity.findall("i:DeviceVariantCollection/i:DeviceVariant", NS)
            for variant in variants or [identity]:
                product = variant.get("productId") or label(identity, "DeviceName") or f"Device {device}"
                slug = re.sub(r"[^a-z0-9]+", "_", product.lower()).strip("_")[:24]
                image = ""
                image_name = variant.get("deviceSymbol", "")
                image_content = files.get(str(PurePosixPath(name).parent / image_name))
                if image_content and len(image_content) <= 1_000_000:
                    if image_content.startswith(b"\x89PNG\r\n\x1a\n"):
                        image = "data:image/png;base64," + base64.b64encode(image_content).decode()
                    elif image_content.startswith(b"\xff\xd8\xff"):
                        image = "data:image/jpeg;base64," + base64.b64encode(image_content).decode()
                profile = {
                    "id": f"custom_{vendor}_{device}_{slug}_{layout_index}",
                    "name": product,
                    "manufacturer": identity.get("vendorName", ""),
                    "model": product,
                    "description": label(variant, "Description"),
                    "purpose": "",
                    "image": image,
                    "source": PurePosixPath(name).name,
                    "notes": "\n".join(warnings)
                    or "Aus Hersteller-IODD importiert. Zuordnung über Vendor-ID und aktive Device-ID; Prozesswerte vor Nutzung mit Display vergleichen.",
                    "match": [{"vendorid": vendor, "deviceid": device}],
                    "length": total_bits // 8,
                    "fields": fields,
                    "parameters": parameters,
                    "conditions": conditions,
                }
                validate_profile(profile, custom=True)
                candidates.append(
                    {"profile": profile, "warnings": warnings, "layout": layout.get("id", str(layout_index))}
                )
                if len(candidates) > 64:
                    raise ValueError("Zu viele Gerätevarianten im ZIP")
    return candidates
