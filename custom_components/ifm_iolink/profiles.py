"""Shared profile library, persisted once across all configured masters."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .decoder import validate_profile


class ProfileLibrary:
    def __init__(self, hass):
        self.hass = hass
        self.store = Store(hass, 1, f"{DOMAIN}.profiles")
        self.builtin = {}
        self.custom = {}
        self.lock = asyncio.Lock()
        self.revision = 0

    async def load(self):
        def read():
            return {
                p["id"]: validate_profile(p)
                for file in sorted((Path(__file__).parent / "profiles").glob("*.json"))
                for p in [json.loads(file.read_text(encoding="utf-8"))]
            }

        self.builtin = await self.hass.async_add_executor_job(read)
        saved = await self.store.async_load() or {}
        self.custom = {key: validate_profile(value, custom=True) for key, value in saved.items()}

    @property
    def all(self):
        return {**self.builtin, **self.custom}

    async def save(self, profile):
        validate_profile(profile, custom=True)
        async with self.lock:
            existing = self.all.get(profile["id"])
            if existing and existing.get("kind", "iolink") != profile.get("kind", "iolink"):
                raise ValueError("Für einen anderen Gerätetyp bitte ein neues Gerät anlegen")
            updated = {**self.custom, profile["id"]: profile}
            if len(updated) > 100:
                raise ValueError("Maximal 100 eigene Profile")
            await self.store.async_save(updated)
            self.custom = updated
            self.revision += 1

    async def delete(self, identifier):
        async with self.lock:
            if identifier not in self.custom:
                raise ValueError("Eigenes Profil nicht gefunden")
            updated = {key: value for key, value in self.custom.items() if key != identifier}
            await self.store.async_save(updated)
            self.custom = updated
            self.revision += 1

    def suggest(self, identity):
        return [
            key
            for key, profile in self.all.items()
            if any(
                identity.get("vendorid") == match["vendorid"] and identity.get("deviceid") == match["deviceid"]
                for match in profile.get("match", [])
            )
        ]
