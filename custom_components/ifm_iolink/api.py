"""ifm IoT JSON client with separate, explicit parameter-write entry point."""

from __future__ import annotations

import asyncio
import base64
import ipaddress
import json
from urllib.parse import urlsplit

import aiohttp

from .const import MODELS


class IfmError(Exception):
    """A network or protocol error."""


class IfmAuthError(IfmError):
    """Authentication required or rejected."""


def normalize_url(value: str) -> str:
    value = value.strip()
    if "://" not in value:
        value = "http://" + value
    parsed = urlsplit(value)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Ungültige IoT-Adresse")
    if any(c.isspace() for c in value):
        raise ValueError("Leerzeichen in IoT-Adresse")
    return value.rstrip("/") + "/"


def data_value(data: dict, path: str):
    item = data.get(path)
    return item.get("data") if isinstance(item, dict) and item.get("code") == 200 else None


class IfmClient:
    def __init__(self, session, url, username="", password="", verify_ssl=True, timeout=4):
        self.session = session
        self.url = normalize_url(url)
        self.username, self.password = username, password
        self.verify_ssl, self.timeout = verify_ssl, timeout
        self.lock = asyncio.Lock()

    async def request(self, adr, data=None):
        if not (adr in ("/getidentity", "/getdatamulti") or adr.endswith(("/gettree", "/iolreadacyclic"))):
            raise ValueError("Nur Leseoperationen sind erlaubt")
        return await self._request(adr, data)

    async def write_parameter(self, port, index, raw):
        if type(port) is not int or not 1 <= port <= 8 or type(index) is not int or not 0 <= index <= 65535:
            raise ValueError("Ungültiger Port/Parameterindex")
        if not isinstance(raw, str) or len(raw) > 2048 or len(raw) % 2:
            raise ValueError("Ungültiger Hexwert")
        if any(c not in "0123456789abcdefABCDEF" for c in raw):
            raise ValueError("Ungültiger Hexwert")
        return await self._request(
            f"/iolinkmaster/port[{port}]/iolinkdevice/iolwriteacyclic",
            {"index": index, "subindex": 0, "value": raw.upper()},
            empty_response=True,
        )

    async def write_port_mode(self, port, mode):
        if type(port) is not int or not 1 <= port <= 8 or type(mode) is not int or mode not in (0, 1, 2, 3):
            raise ValueError("Ungültiger Port/Portmodus")
        return await self._request(
            f"/iolinkmaster/port[{port}]/mode/setdata", {"newvalue": mode}, empty_response=True
        )

    async def write_port_output(self, port, on):
        if type(port) is not int or not 1 <= port <= 8 or type(on) is not bool:
            raise ValueError("Ungültiger Port/Ausgangswert")
        return await self._request(
            f"/iolinkmaster/port[{port}]/iolinkdevice/pdout/setdata",
            {"newvalue": "01" if on else "00"},
            empty_response=True,
        )

    async def _request(self, adr, data=None, empty_response=False):
        body = {"code": "request", "cid": 1, "adr": adr}
        if data is not None:
            body["data"] = data
        if self.password:
            if not self.url.startswith("https://"):
                raise IfmAuthError("Für Passwortzugriff ist HTTPS erforderlich")
            body["auth"] = {
                key: base64.b64encode(value.encode()).decode()
                for key, value in {"user": self.username or "administrator", "passwd": self.password}.items()
            }
        try:
            async with self.lock:
                async with self.session.post(
                    self.url,
                    json=body,
                    ssl=self.verify_ssl,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    allow_redirects=False,
                ) as response:
                    if response.status in (401, 403):
                        raise IfmAuthError("Zugangsdaten prüfen")
                    response.raise_for_status()
                    chunks, size = [], 0
                    async for chunk in response.content.iter_chunked(65536):
                        size += len(chunk)
                        if size > 2_000_000:
                            raise IfmError("Antwort zu groß")
                        chunks.append(chunk)
                    raw = b"".join(chunks)
                    payload = json.loads(raw)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise IfmError(f"IoT-Anfrage fehlgeschlagen: {type(err).__name__}") from err
        if not isinstance(payload, dict):
            raise IfmError("Ungültige IoT-Antwort")
        if payload.get("code") in (401, 403):
            raise IfmAuthError("IoT-Zugriff verweigert")
        if empty_response and payload.get("code") == 200 and payload.get("data") in (None, {}):
            return {}
        if payload.get("code") != 200 or not isinstance(payload.get("data"), dict):
            raise IfmError(f"IoT-Fehlercode {payload.get('code', 'fehlt')}")
        return payload["data"]

    async def multi(self, paths):
        return await self.request("/getdatamulti", {"datatosend": paths})

    async def identify(self):
        # Older firmware reports a MAC, not the model, in getidentity.iot.name.
        paths = ["/deviceinfo/productcode", "/deviceinfo/serialnumber", "/deviceinfo/swrevision"]
        values = await self.multi(paths)
        model = str(data_value(values, paths[0]) or "").upper()
        serial = str(data_value(values, paths[1]) or "")
        if model not in MODELS:
            raise IfmError("Kein unterstützter AL1350/AL1352")
        if not serial:
            raise IfmError("Keine Seriennummer; Zugriff und Security Mode prüfen")
        return {"model": model, "serial": serial, "firmware": data_value(values, paths[2]), "ports": MODELS[model]}


async def discover(session, cidr: str):
    """Probe a user-selected private IPv4 subnet, at most 1024 addresses."""
    network = ipaddress.ip_network(cidr, strict=False)
    if (
        network.version != 4
        or not network.is_private
        or network.num_addresses > 1024
        or network.is_loopback
        or network.is_link_local
    ):
        raise ValueError("Privates IPv4-Netz mit maximal 1024 Adressen angeben")
    semaphore = asyncio.Semaphore(24)

    async def probe(address):
        async with semaphore:
            client = IfmClient(session, str(address), timeout=1)
            try:
                info = await client.identify()
                return {**info, "url": client.url}
            except IfmError:
                return None

    found = await asyncio.gather(*(probe(address) for address in network.hosts()))
    return sorted((item for item in found if item), key=lambda item: item["url"])
