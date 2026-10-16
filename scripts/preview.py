"""Local demo of the actual panel; does not connect to Home Assistant or devices."""

import base64
import json
import sys
import types
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
package = types.ModuleType("custom_components.ifm_iolink")
package.__path__ = [str(ROOT / "custom_components/ifm_iolink")]
sys.modules[package.__name__] = package
from custom_components.ifm_iolink.decoder import decode, validate_profile
from custom_components.ifm_iolink.iodd import import_iodd

ASSETS = ROOT / "custom_components/ifm_iolink/frontend"
PROFILES = [json.loads(p.read_text(encoding="utf-8")) for p in (ASSETS.parent / "profiles").glob("*.json")]
masters = []
backups = {}
restore_plans = {}
restore_reports = {}
for model, count, identifier in [("AL1350", 4, "demo4"), ("AL1352", 8, "demo8")]:
    ports = {}
    for port in range(1, count + 1):
        profile_id = "badu_flowsonic_plus" if port == 1 else "pn7096" if port in (2, 4) else "unknown"
        profile = next((p for p in PROFILES if p["id"] == profile_id), None)
        raw = "408D8DEF419E7EE87DB48E52474F27C6474F27B90010" if port == 1 else "4E5C0100" if port == 4 else "08980101"
        ports[str(port)] = {
            "port": port,
            "mode": 2 if port == 5 else 1 if port == 6 else 3,
            "pin4": False,
            "pin2": False,
            "identity": {
                "productname": profile["model"] if profile else "",
                "vendorid": profile["match"][0]["vendorid"] if profile else 0,
                "deviceid": profile["match"][0]["deviceid"] if profile else 0,
                "serial": "DEMO",
            },
            "profile": profile_id,
            "assignment": {
                "profile": profile_id,
                "name": {1: "Pool · Durchfluss", 2: "Poolfilter · Druck", 4: "Heizkreis · Druck"}.get(port, ""),
                "location": "Heizungsraum" if profile else "",
                "purpose": profile.get("purpose", "") if profile else "",
            },
            "raw": raw if profile else None,
            "connected": bool(profile),
            "values": decode(profile, raw) if profile else {},
            "suggested": [profile_id] if profile else [],
            "error": None,
            "updated": datetime.now(timezone.utc).isoformat(),
        }
    masters.append(
        {
            "entry_id": identifier,
            "name": f"Heizungsraum · {model} (Demo)",
            "identity": {"model": model, "ports": count, "serial": "DEMO"},
            "online": True,
            "interval": 2,
            "ports": ports,
        }
    )

HTML = b"""<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ifm IO-Link Command Center - Demo</title><style>body{margin:0}#demo{background:#253546;color:white;text-align:center;padding:7px;font:12px Arial}</style><div id="demo">DEMO - Beispielwerte - keine Verbindung zu Home Assistant oder Hardware</div><ifm-iolink-panel></ifm-iolink-panel><script type="module">import '/ifm_iolink_static/panel.js';document.querySelector('ifm-iolink-panel').hass={callWS:async message=>{const r=await fetch('/api',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(message)});const data=await r.json();if(!r.ok)throw Error(data.error);return data;}};</script></html>"""


class Handler(BaseHTTPRequestHandler):
    def send(self, body, content_type="application/json", status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            return self.send(HTML, "text/html; charset=utf-8")
        relative = unquote(self.path.split("?", 1)[0]).removeprefix("/ifm_iolink_static/")
        path = (ASSETS / relative).resolve()
        if not path.is_relative_to(ASSETS.resolve()) or not path.is_file():
            return self.send(b"not found", status=404)
        mime = {".js": "text/javascript", ".css": "text/css", ".png": "image/png", ".svg": "image/svg+xml"}.get(
            path.suffix, "application/octet-stream"
        )
        self.send(path.read_bytes(), mime)

    def do_POST(self):
        try:
            size = int(self.headers.get("Content-Length", 0))
            if size > 12_000_000:
                raise ValueError("too large")
            msg = json.loads(self.rfile.read(size))
            command = msg["type"].split("/")[-1]
            result = {}
            if command == "snapshot":
                result = {"masters": masters, "profiles": PROFILES}
            elif command == "test_profile":
                result = decode(validate_profile(msg["profile"]), msg["raw"])
            elif command == "import_iodd":
                result = import_iodd(base64.b64decode(msg["content"]), msg["filename"])
            elif command == "save_profile":
                validate_profile(msg["profile"], custom=True)
                PROFILES[:] = [p for p in PROFILES if p["id"] != msg["profile"]["id"]] + [msg["profile"]]
            elif command == "delete_profile":
                PROFILES[:] = [p for p in PROFILES if p["id"] != msg["profile_id"]]
            elif command == "debug":
                result = {"demo": True, "port": msg["port"], "samples": []}
            elif command == "read_parameter":
                result = {"value": "Demo: 0.06", "raw": "003C"}
            elif command == "rename_master":
                master = next(m for m in masters if m["entry_id"] == msg["entry_id"])
                master["name"] = msg["name"]
                result = {"saved": True}
            elif command == "delete_master":
                master = next(m for m in masters if m["entry_id"] == msg["entry_id"])
                if msg["confirm_name"] != master["name"]:
                    raise ValueError("Masternamen bestätigen")
                masters.remove(master)
                result = {"deleted": True}
            elif command == "get_parameter_backup":
                result = {"backup": backups.get((msg["entry_id"], msg["port"]))}
            elif command == "get_restore_report":
                result = {"report": restore_reports.get((msg["entry_id"], msg["port"]))}
            elif command == "preview_restore":
                key = (msg["entry_id"], msg["port"])
                backup = msg.get("backup") or backups.get(key)
                if not backup or not backup.get("demo"):
                    raise ValueError("Demo erwartet eine Demo-Sicherung")
                master = next(m for m in masters if m["entry_id"] == key[0])
                port = master["ports"][str(key[1])]
                profile = next(p for p in PROFILES if p["id"] == port["profile"])
                result = {
                    "token": "demo-only",
                    "target": port["identity"],
                    "port": key[1],
                    "source_created_at": backup["created_at"],
                    "rows": [
                        {
                            "index": p["index"],
                            "name": p["name"],
                            "before": "003C",
                            "after": backup["values"][str(p["index"])]["raw"],
                            "changed": backup["values"][str(p["index"])]["raw"] != "003C",
                        }
                        for p in profile["parameters"]
                        if p.get("access") == "rw"
                    ],
                    "skipped": [],
                }
                restore_plans[key] = result
            elif command == "restore_parameters":
                key = (msg["entry_id"], msg["port"])
                if msg.get("token") != "demo-only" or not msg.get("confirm") or key not in restore_plans:
                    raise ValueError("Demo-Vorschau zuerst bestätigen")
                plan = restore_plans.pop(key)
                result = {
                    **plan,
                    "demo": True,
                    "status": "completed",
                    "verified": [r["index"] for r in plan["rows"] if r["changed"]],
                    "pending": [],
                    "error": None,
                }
                restore_reports[key] = result
            elif command == "read_parameters":
                master = next(m for m in masters if m["entry_id"] == msg["entry_id"])
                profile = next(p for p in PROFILES if p["id"] == master["ports"][str(msg["port"])]["profile"])
                result = {
                    "demo": True,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "profile_id": profile["id"],
                    "values": {str(p["index"]): {"value": "Demo: 0.06", "raw": "003C"} for p in profile["parameters"]},
                    "errors": {},
                    "complete": True,
                    "saved": msg.get("save", False),
                }
                if msg.get("save"):
                    backups[(msg["entry_id"], msg["port"])] = result
            elif command == "assign":
                master = next(m for m in masters if m["entry_id"] == msg["entry_id"])
                port = master["ports"][str(msg["port"])]
                port["assignment"] = {**port["assignment"], **{
                    k: msg[k] for k in ("name", "purpose", "location", "profile", "digital_profile") if k in msg
                }}
                port["profile"] = msg["profile"]
            else:
                raise ValueError("unknown command")
            self.send(json.dumps(result, ensure_ascii=False).encode())
        except Exception as err:
            self.send(json.dumps({"error": str(err)}).encode(), status=400)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print("Demo: http://127.0.0.1:8765", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
