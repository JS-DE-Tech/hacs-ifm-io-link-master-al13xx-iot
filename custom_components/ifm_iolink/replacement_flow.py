"""Server-owned automatic replacement, independent of an open browser dialog."""

import asyncio
import logging
import secrets
import time
from copy import deepcopy

from .api import IfmError
from .const import DOMAIN, MODELS
from .replacement import confirm_replacement, preview_replacement, registry_serial
from .replacement_network import (
    restore_modes,
    saved,
    store,
    transfer_network,
    validate_restore_plan,
    wait_for_network,
)

_LOGGER = logging.getLogger(__name__)


def operation_lock(hass):
    return hass.data[DOMAIN].setdefault("replacement_operation_lock", asyncio.Lock())


def running_job(hass):
    return any(not job["task"].done() for job in hass.data[DOMAIN].get("replacement_jobs", {}).values())


async def wait_for_loaded(hass, entry, target):
    """Commit is not completion: also wait for the reloaded coordinator."""
    for _ in range(30):
        coordinator = hass.data[DOMAIN].get("coordinators", {}).get(entry.entry_id)
        if (coordinator and coordinator.last_update_success
                and all(coordinator.identity.get(k) == target[k] for k in ("serial", "model"))):
            return
        await asyncio.sleep(1)
    raise ValueError("Master übernommen, aber HA-Neuladen/Verbindung noch nicht bestätigt. Austausch fortsetzen prüft nur die Verbindung.")


async def mark_completed(hass, entry):
    backup = await store(hass, entry).async_load()
    backup["automation"]["completed"] = True
    await store(hass, entry).async_save(backup)


async def automatic_replacement(hass, entry, token, progress):
    # A crash after commit but before recording success must never replay hardware.
    backup = await store(hass, entry).async_load()
    automation = (backup or {}).get("automation")
    if automation and not entry.data.get("replacement_paused"):
        target = automation["target"]
        if (entry.unique_id != target["serial"] or entry.data.get("url") != backup.get("transfer", {}).get("url")
                or registry_serial(entry) != backup["data"].get("registry_serial", backup["unique_id"])):
            raise ValueError("Austausch wurde abgebrochen oder Konfiguration geändert; keine automatische Fortsetzung")
        progress("Übernahme gespeichert – Verbindung in Home Assistant prüfen")
        await wait_for_loaded(hass, entry, target)
        await mark_completed(hass, entry)
        return {"saved": True, "model": target["model"], "ports": target["ports"]}

    backup = await saved(hass, entry)
    validate_restore_plan(backup, entry)
    if automation is None:
        if backup.get("transfer"):
            transfer = backup["transfer"]
            target = {k: transfer[k] for k in ("serial", "model")}
            target["ports"] = MODELS[target["model"]]
            candidate_url = transfer["url"]
        else:
            preview = hass.data[DOMAIN].get("replacement_previews", {}).get(entry.entry_id)
            if (not preview or not secrets.compare_digest(preview["token"], token)
                    or preview["expires"] < time.monotonic()
                    or preview["source"] != dict(entry.data) or preview["options"] != dict(entry.options)):
                raise ValueError("Ersatzmaster erneut prüfen und Austausch bestätigen")
            target, candidate_url = preview["target"], preview["url"]
        automation = {"target": deepcopy(target), "candidate_url": candidate_url}
        backup["automation"] = automation
        await store(hass, entry).async_save(backup)

    if not backup.get("transfer"):
        progress("Ersatzmaster und gesicherte Konfiguration prüfen")
        preview = await preview_replacement(hass, entry, automation["candidate_url"])
        if preview["target"] != automation["target"]:
            raise ValueError("Ersatzmaster seit Bestätigung geändert")
        token = preview["token"]
    progress("Netzwerk übertragen und erforderlichen Neustart ausführen")
    result = await transfer_network(hass, entry, token)
    if not result["verified"]:
        progress("Auf Ersatzmaster an der Ziel-IP warten")
        result = await wait_for_network(hass, entry)
    if not result["verified"]:
        raise ValueError(result["message"])
    progress("Portmodi und Mastereinstellungen zurücksichern und zurücklesen")
    await restore_modes(hass, entry)
    progress("Ersatzmaster abschließend prüfen und bestehende IDs übernehmen")
    preview = await preview_replacement(hass, entry, result["url"])
    if any(preview["target"][key] != automation["target"][key] for key in ("serial", "model", "ports")):
        raise ValueError("Identität vor Übernahme geändert")
    result = await confirm_replacement(hass, entry, preview["token"])
    progress("Home Assistant lädt die Integration – Verbindung prüfen")
    await wait_for_loaded(hass, entry, automation["target"])
    await mark_completed(hass, entry)
    return result


def start_job(hass, entry, token):
    """Called under operation_lock; task acquires it after command returns."""
    jobs = hass.data[DOMAIN].setdefault("replacement_jobs", {})
    job = {"progress": "Austausch wird gestartet", "error": None, "result": None}
    jobs[entry.entry_id] = job

    async def run():
        try:
            async with operation_lock(hass):
                job["result"] = await automatic_replacement(
                    hass, entry, token, lambda text: job.update(progress=text))
                job["progress"] = "Austausch abgeschlossen; Home Assistant verbunden"
        except (ValueError, IfmError, OSError, TimeoutError) as err:
            job["error"] = str(err)
            job["progress"] = "Austausch angehalten – Verarbeitung bleibt pausiert, sofern noch nicht übernommen"
        except Exception:
            _LOGGER.exception("Unexpected error during master replacement")
            job["error"] = "Unerwarteter Fehler; HA-Protokoll prüfen. Schreibzugriffe werden nicht automatisch wiederholt."
    job["task"] = hass.async_create_task(run())
    return {"running": True}


async def job_status(hass, entry):
    backup = await store(hass, entry).async_load()
    automation = (backup or {}).get("automation", {})
    resumable = bool(backup and ((automation and not automation.get("completed"))
                                 or (entry.data.get("replacement_paused") and backup.get("transfer"))))
    job = hass.data[DOMAIN].get("replacement_jobs", {}).get(entry.entry_id)
    if job:
        return {key: job[key] for key in ("progress", "error", "result")} | {
            "running": not job["task"].done(), "resumable": resumable}
    return {"running": False, "error": None, "result": None, "resumable": resumable,
            "progress": "Gespeicherter Austausch vorhanden – Fortsetzen prüft den aktuellen Stand" if resumable else ""}
