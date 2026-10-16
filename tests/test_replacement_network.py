"""Replacement transfer failures and recovery without real network access."""
import asyncio
from copy import deepcopy
from types import SimpleNamespace as NS

import pytest

from custom_components.ifm_iolink import replacement as replacement
from custom_components.ifm_iolink import replacement_network as mod
from custom_components.ifm_iolink.api import IfmError

NETWORK = {"dhcp": 0, "ipaddress": "10.100.1.241", "subnetmask": "255.255.252.0",
           "ipdefaultgateway": "10.100.0.1"}


@pytest.mark.parametrize("change", [{"dhcp": 1}, {"dhcp": False}, {"subnetmask": "255.0.255.0"},
                                  {"ipdefaultgateway": "192.168.1.1"}, {"ipaddress": "127.0.0.1"},
                                  {"ipaddress": "10.100.3.255"}, {"mac": "00:00:00:00:00:00"}])
def test_invalid_network_rejected(change):
    with pytest.raises(ValueError):
        mod.validate_network({**NETWORK, **change})


@pytest.fixture
def transfer(monkeypatch):
    entry = NS(entry_id="garage", unique_id="OLD", data={"replacement_paused": True, "ports": 4}, options={})
    target = {"serial": "NEW", "model": "AL1352", "ports": 8}
    preview = {"token": "TOKEN", "expires": float("inf"), "source": deepcopy(entry.data), "options": {},
               "url": "http://10.100.1.242/", "target": target, "rows": []}
    entries = [entry]
    hass = NS(data={"ifm_iolink": {"replacement_previews": {"garage": preview}}},
              config_entries=NS(async_entries=lambda domain: entries,
                                async_get_entry=lambda entry_id: next((e for e in entries if e.entry_id == entry_id), None)))
    backup = {"entry_id": entry.entry_id, "unique_id": entry.unique_id,
              "data": {key: value for key, value in entry.data.items() if key != "replacement_paused"},
              "options": {},
              "hardware": {"network": NETWORK, "modes": {"1": 3, "2": 2, "3": 1, "4": 0}}}
    state = {"moved": False, "code": 233, "serial": "NEW", "occupied": False, "modes": {},
             "write_error": False, "offline": False, "bad_readback": False, "fail_save": False,
             "entries": entries, "saves": 0, "other_backups": {}}
    writes = []
    async def in_use(url):
        return state["occupied"]
    monkeypatch.setattr(mod, "address_in_use", in_use)
    class Store:
        def __init__(self, entry_id):
            self.entry_id = entry_id
        async def async_load(self):
            return deepcopy(backup if self.entry_id == entry.entry_id else state["other_backups"].get(self.entry_id))
        async def async_save(self, data):
            state["saves"] += 1
            if state["fail_save"] or state.get("fail_save_at") == state["saves"]:
                raise OSError("disk full")
            backup.clear()
            backup.update(deepcopy(data))
            if state.get("on_save"):
                state["on_save"](data)
    monkeypatch.setattr(mod, "store", lambda h, e: Store(e.entry_id))
    class Client:
        def __init__(self, url):
            self.url = url
        async def identify(self):
            if self.url.endswith("242/") and state.get("source_offline"):
                raise IfmError("old candidate address offline")
            if self.url.endswith("241/") and (state["offline"] or not state["moved"]):
                if state["occupied"]:
                    return {**target, "serial": "OLD"}
                raise IfmError("offline")
            return {**target, "serial": state["serial"]}
        async def write_network(self, values):
            assert backup["transfer"]["stage"] == "write_attempted"
            writes.append(("network", values))
            if state["code"] != 230:
                state["moved"] = True
            if state["write_error"]:
                raise IfmError("response lost")
            return state["code"]
        async def reboot(self):
            assert backup["transfer"]["stage"] == "reboot_attempted"
            writes.append(("reboot",))
            if state.get("reboot_error"):
                raise IfmError("reboot response lost")
            state["moved"] = True
        async def multi(self, paths):
            return {path: {"code": 200, "data": (None if state.get("warming") and "/network/" in path else
                      999 if state["bad_readback"] else
                      state["modes"].get(path, NETWORK.get(path.rsplit("/", 1)[1])))} for path in paths}
        async def write_master_setting(self, path, value):
            writes.append(("setting", path, value))
            state["modes"][path] = value
        async def write_port_mode(self, port, mode):
            writes.append(("mode", port, mode))
            state["modes"][f"/iolinkmaster/port[{port}]/mode"] = mode
    monkeypatch.setattr(mod, "candidate_client", lambda h, e, url: Client(url))
    async def fresh(*args):
        return {"target": target, "rows": []}
    monkeypatch.setattr(replacement, "preview_replacement", fresh)
    async def sleep(seconds):
        pass
    monkeypatch.setattr(mod.asyncio, "sleep", sleep)
    return hass, entry, backup, state, writes


@pytest.mark.parametrize("code", [200, 230, 233])
def test_network_reconnect_and_restore_without_enabling_outputs(transfer, code):
    hass, entry, backup, state, writes = transfer
    state["code"] = code
    async def run():
        assert (await mod.transfer_network(hass, entry, "TOKEN"))["verified"]
        result = await mod.restore_modes(hass, entry)
        assert len(result["ports"]) == 4
        # Durable journal makes retry after a process restart read-only.
        assert (await mod.transfer_network(hass, entry, "TOKEN"))["verified"]
        before = list(writes)
        await mod.restore_modes(hass, entry)
        assert writes == before
    asyncio.run(run())
    assert sum(w[0] == "network" for w in writes) == 1
    assert sum(w[0] == "reboot" for w in writes) == (1 if code == 230 else 0)
    assert ("mode", 2, 0) in writes and not any(w[0] == "mode" and w[2] == 2 for w in writes)


def test_lost_response_is_read_back_not_replayed(transfer):
    hass, entry, backup, state, writes = transfer
    state["write_error"] = True
    assert asyncio.run(mod.transfer_network(hass, entry, "TOKEN"))["verified"]
    assert len(writes) == 1


@pytest.mark.parametrize("failure", ["occupied", "fail_save", "serial", "token"])
def test_rejects_before_any_write(transfer, failure):
    hass, entry, backup, state, writes = transfer
    token = "TOKEN"
    if failure == "token":
        token = "wrong"
    elif failure == "serial":
        state["serial"] = "OTHER"
    else:
        state[failure] = True
    with pytest.raises((ValueError, OSError)):
        asyncio.run(mod.transfer_network(hass, entry, token))
    assert writes == []


def test_offline_after_write_can_resume_read_only(transfer):
    hass, entry, backup, state, writes = transfer
    state["offline"] = True
    assert not asyncio.run(mod.transfer_network(hass, entry, "TOKEN"))["verified"]
    state["offline"] = False
    assert asyncio.run(mod.verify_network(hass, entry))["verified"]
    assert len(writes) == 1


def test_wrong_target_blocks_restore(transfer):
    hass, entry, backup, state, writes = transfer
    asyncio.run(mod.transfer_network(hass, entry, "TOKEN"))
    state["serial"] = "OTHER"
    with pytest.raises(ValueError, match="nicht der ausgewählte"):
        asyncio.run(mod.restore_modes(hass, entry))
    assert len(writes) == 1


def test_network_readback_mismatch_blocks_restore(transfer):
    hass, entry, backup, state, writes = transfer
    asyncio.run(mod.transfer_network(hass, entry, "TOKEN"))
    state["bad_readback"] = True
    with pytest.raises(ValueError, match="Rücklesen"):
        asyncio.run(mod.restore_modes(hass, entry))
    assert len(writes) == 1


def test_supported_settings_restored_and_mac_rejected(transfer):
    hass, entry, backup, state, writes = transfer
    backup["hardware"]["settings"] = {"/devicetag/applicationtag": "Garage", "/iotsetup/smobip": "255.255.255.255",
                                     "/iotsetup/smobport": 35100, "/iotsetup/smobinterval": 0}
    asyncio.run(mod.transfer_network(hass, entry, "TOKEN"))
    asyncio.run(mod.restore_modes(hass, entry))
    assert sum(w[0] == "setting" for w in writes) == 4
    with pytest.raises(ValueError):
        mod.validate_setting("/iotsetup/network/macaddress", "00:00:00:00:00:00")


def test_adoption_rejects_incomplete_restore_and_wrong_url(transfer):
    hass, entry, backup, state, writes = transfer
    asyncio.run(mod.transfer_network(hass, entry, "TOKEN"))
    preview = {"target": {"serial": "NEW"}, "url": "http://10.100.1.242/"}
    with pytest.raises(ValueError, match="bestätigten Ziel-IP"):
        asyncio.run(mod.check_adoption(hass, entry, preview))
    preview["url"] = "http://10.100.1.241/"
    # Skipping restore altogether must not silently adopt factory port modes.
    with pytest.raises(ValueError, match="unvollständig"):
        asyncio.run(mod.check_adoption(hass, entry, preview))
    backup["transfer"]["restore_attempted"] = True
    with pytest.raises(ValueError, match="unvollständig"):
        asyncio.run(mod.check_adoption(hass, entry, preview))
    asyncio.run(mod.restore_modes(hass, entry))
    asyncio.run(mod.check_adoption(hass, entry, preview))


@pytest.mark.parametrize("change", ["entry_id", "unique_id", "data", "options", "removed"])
def test_backup_bound_to_unchanged_existing_entry(transfer, change):
    hass, entry, backup, state, writes = transfer
    if change == "removed":
        state["entries"].clear()
    elif change in ("data", "options"):
        backup[change]["changed"] = True
    else:
        backup[change] = "OTHER"
    with pytest.raises(ValueError, match="Integrationskonfiguration"):
        asyncio.run(mod.transfer_network(hass, entry, "TOKEN"))
    assert not writes


@pytest.mark.parametrize("change", ["options", "removed", "duplicate"])
def test_final_source_and_target_checks_after_journal_save(transfer, change):
    hass, entry, backup, state, writes = transfer
    def changed(data):
        if data.get("transfer", {}).get("stage") != "write_attempted":
            return
        if change == "removed":
            state["entries"].clear()
        elif change == "duplicate":
            state["entries"].append(NS(entry_id="other", unique_id="NEW", data={}))
        else:
            entry.options["changed"] = True
    state["on_save"] = changed
    with pytest.raises(ValueError):
        asyncio.run(mod.transfer_network(hass, entry, "TOKEN"))
    assert not writes


@pytest.mark.parametrize("invalid", ["modes", "settings"])
def test_invalid_restore_plan_rejected_before_network_changes(transfer, invalid):
    hass, entry, backup, state, writes = transfer
    if invalid == "modes":
        backup["hardware"]["modes"].pop("4")
    else:
        backup["hardware"]["settings"] = {"/firmware/factoryreset": 1}
    with pytest.raises(ValueError):
        asyncio.run(mod.transfer_network(hass, entry, "TOKEN"))
    assert not writes and "transfer" not in backup


@pytest.mark.parametrize("reservation", ["configured", "logical", "transfer"])
def test_other_installation_cannot_claim_reserved_replacement(transfer, reservation):
    hass, entry, backup, state, writes = transfer
    other = NS(entry_id="other", unique_id="OTHER", data={"replacement_paused": True})
    state["entries"].append(other)
    if reservation == "configured":
        other.unique_id = "NEW"
    elif reservation == "logical":
        other.data["registry_serial"] = "NEW"
    else:
        state["other_backups"]["other"] = {"transfer": {"serial": "NEW"}}
    with pytest.raises(ValueError, match="anderen"):
        asyncio.run(mod.transfer_network(hass, entry, "TOKEN"))
    assert not writes


def test_accepted_230_can_resume_once_before_reboot_attempt(transfer):
    hass, entry, backup, state, writes = transfer
    state.update(code=230, fail_save_at=3)
    with pytest.raises(OSError):
        asyncio.run(mod.transfer_network(hass, entry, "TOKEN"))
    assert backup["transfer"]["network_code"] == 230
    assert backup["transfer"]["stage"] == "reboot_pending"
    assert backup["transfer"]["source_url"] == "http://10.100.1.242/"
    assert not any(w[0] == "reboot" for w in writes)
    assert asyncio.run(mod.transfer_network(hass, entry, "TOKEN"))["verified"]
    assert sum(w[0] == "network" for w in writes) == 1
    assert sum(w[0] == "reboot" for w in writes) == 1


def test_restart_after_reboot_intent_does_not_replay(transfer):
    hass, entry, backup, state, writes = transfer
    state["code"] = 230
    def interrupted(data):
        if data.get("transfer", {}).get("stage") == "reboot_attempted":
            raise asyncio.CancelledError
    state["on_save"] = interrupted
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(mod.transfer_network(hass, entry, "TOKEN"))
    state["on_save"] = None
    assert backup["transfer"]["reboot_attempted"]
    assert not asyncio.run(mod.transfer_network(hass, entry, "TOKEN"))["verified"]
    assert not any(w[0] == "reboot" for w in writes)
    # The user performs the uncertain reboot locally; continuation only reads.
    state["moved"] = True
    assert asyncio.run(mod.transfer_network(hass, entry, "TOKEN"))["verified"]
    assert len(writes) == 1


def test_lost_230_response_never_guesses_that_reboot_is_needed(transfer):
    hass, entry, backup, state, writes = transfer
    state.update(code=230, write_error=True)
    result = asyncio.run(mod.transfer_network(hass, entry, "TOKEN"))
    assert not result["verified"] and "10.100.1.242" in result["message"]
    assert "network_code" not in backup["transfer"]
    assert not asyncio.run(mod.transfer_network(hass, entry, "TOKEN"))["verified"]
    assert len(writes) == 1


def test_accepted_230_external_reboot_skips_old_address_and_reboot(transfer):
    hass, entry, backup, state, writes = transfer
    state.update(code=230, fail_save_at=3)
    with pytest.raises(OSError):
        asyncio.run(mod.transfer_network(hass, entry, "TOKEN"))
    state.update(moved=True, source_offline=True)
    assert asyncio.run(mod.transfer_network(hass, entry, "TOKEN"))["verified"]
    assert backup["transfer"]["stage"] == "verified"
    assert len(writes) == 1


def test_accepted_230_waits_if_old_and_new_addresses_temporarily_offline(transfer):
    hass, entry, backup, state, writes = transfer
    state.update(code=230, fail_save_at=3)
    with pytest.raises(OSError):
        asyncio.run(mod.transfer_network(hass, entry, "TOKEN"))
    state.update(source_offline=True)
    assert not asyncio.run(mod.transfer_network(hass, entry, "TOKEN"))["verified"]
    assert len(writes) == 1 and backup["transfer"]["stage"] == "reboot_pending"


def test_reboot_resume_rejects_wrong_device_at_new_ip(transfer):
    hass, entry, backup, state, writes = transfer
    state.update(code=230, fail_save_at=3)
    with pytest.raises(OSError):
        asyncio.run(mod.transfer_network(hass, entry, "TOKEN"))
    state.update(moved=True, serial="OTHER")
    with pytest.raises(ValueError, match="nicht der ausgewählte"):
        asyncio.run(mod.transfer_network(hass, entry, "TOKEN"))
    assert len(writes) == 1


def test_incomplete_network_readback_during_warmup_is_retryable(transfer, monkeypatch):
    hass, entry, backup, state, writes = transfer
    state["warming"] = True
    result = asyncio.run(mod.transfer_network(hass, entry, "TOKEN"))
    assert not result["verified"] and "vollständig lesbar" in result["message"]
    async def finish_warmup(seconds):
        state["warming"] = False
    monkeypatch.setattr(mod.asyncio, "sleep", finish_warmup)
    assert asyncio.run(mod.wait_for_network(hass, entry, attempts=2))["verified"]
    assert len(writes) == 1


def test_delayed_reconnect_polling_never_replays_hardware_writes(transfer, monkeypatch):
    hass, entry, backup, state, writes = transfer
    state["offline"] = True
    asyncio.run(mod.transfer_network(hass, entry, "TOKEN"))
    delays = []
    async def delayed(seconds):
        delays.append(seconds)
        if len(delays) == 3:
            state["offline"] = False
    monkeypatch.setattr(mod.asyncio, "sleep", delayed)
    assert asyncio.run(mod.wait_for_network(hass, entry, attempts=5, interval=2))["verified"]
    assert delays == [2, 2, 2] and len(writes) == 1


def test_reconnect_polling_stops_at_attempt_limit(transfer):
    hass, entry, backup, state, writes = transfer
    state["offline"] = True
    asyncio.run(mod.transfer_network(hass, entry, "TOKEN"))
    assert not asyncio.run(mod.wait_for_network(hass, entry, attempts=2, interval=0))["verified"]
    assert len(writes) == 1


def test_restore_interruption_before_send_requires_readback_not_replay(transfer):
    hass, entry, backup, state, writes = transfer
    asyncio.run(mod.transfer_network(hass, entry, "TOKEN"))
    def interrupted(data):
        if data["transfer"].get("ports"):
            raise asyncio.CancelledError
    state["on_save"] = interrupted
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(mod.restore_modes(hass, entry))
    state["on_save"] = None
    with pytest.raises(ValueError, match="am Gerät prüfen"):
        asyncio.run(mod.restore_modes(hass, entry))
    assert len(writes) == 1
    # A locally corrected setting can be confirmed without repeating that write.
    state["modes"]["/iolinkmaster/port[1]/mode"] = 3
    asyncio.run(mod.restore_modes(hass, entry))
    assert not any(w[0] == "mode" and w[1] == 1 for w in writes)


@pytest.mark.parametrize("field", ["mode", "setting"])
def test_final_adoption_rechecks_restored_values(transfer, field):
    hass, entry, backup, state, writes = transfer
    backup["hardware"]["settings"] = {"/devicetag/applicationtag": "Garage"}
    asyncio.run(mod.transfer_network(hass, entry, "TOKEN"))
    asyncio.run(mod.restore_modes(hass, entry))
    path = "/iolinkmaster/port[1]/mode" if field == "mode" else "/devicetag/applicationtag"
    state["modes"][path] = 0 if field == "mode" else "Changed"
    with pytest.raises(ValueError, match="Konfiguration vor Übernahme geändert"):
        asyncio.run(mod.check_adoption(hass, entry, {"target": {"serial": "NEW"}, "url": "http://10.100.1.241/"}))
