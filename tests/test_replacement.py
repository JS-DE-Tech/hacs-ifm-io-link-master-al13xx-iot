"""Master replacement transactions with an in-memory HA boundary; no hardware I/O."""
import asyncio
import sys
from copy import deepcopy
from types import ModuleType
from types import SimpleNamespace as NS

import pytest

from custom_components.ifm_iolink import replacement as mod


@pytest.fixture
def setup(monkeypatch):
    from custom_components.ifm_iolink import replacement_network

    async def check_adoption(*args):
        pass
    monkeypatch.setattr(replacement_network, "check_adoption", check_adoption)
    entry = NS(entry_id="garage", unique_id="OLD", domain="ifm_iolink", title="Garage",
               data={"url": "http://old/", "serial": "OLD", "model": "AL1350", "ports": 4,
                     "registry_serial": "ORIGINAL", "replacement_paused": True},
               options={"ports": {"1": {"profile": "pressure", "name": "Filter"}}})
    state = {"serial": "NEW", "model": "AL1352", "ports": 8, "mode": 3, "output": "00"}
    entries = [entry]
    updates = []
    class Client:
        url = "http://new/"
        async def identify(self):
            return {key: state[key] for key in ("serial", "model", "ports")}
        async def multi(self, paths):
            return {path: {"code": 200, "data": state["mode"] if path.endswith("/mode")
                           else state["output"] if path.endswith("/pdout") else 123} for path in paths}
    monkeypatch.setattr(mod, "candidate_client", lambda *args: Client())
    def update(entry, **kwargs):
        updates.append(kwargs)
        for key, value in kwargs.items():
            setattr(entry, key, value)
    hass = NS(data={"ifm_iolink": {"library": NS(all={}), "parameter_backups": NS(busy=set())}},
              config_entries=NS(async_entries=lambda domain: entries, async_update_entry=update))
    return hass, entry, state, entries, updates


def test_upgrade_retains_options_namespace_and_config_entry(setup):
    hass, entry, state, entries, updates = setup
    original = deepcopy(entry.options)
    async def run():
        preview = await mod.preview_replacement(hass, entry, "http://new")
        assert len(preview["rows"]) == 8
        assert [r["port"] for r in preview["rows"] if r["new"]] == [5, 6, 7, 8]
        await mod.confirm_replacement(hass, entry, preview["token"])
    asyncio.run(run())
    assert entry.unique_id == "NEW" and entry.data["model"] == "AL1352"
    assert entry.entry_id == "garage" and entry.data["registry_serial"] == "ORIGINAL"
    assert entry.options == original and entry.title == "Garage"
    assert len(updates) == 1 and not entry.data["replacement_paused"]


@pytest.mark.parametrize("change", ["expired", "wrong_token", "options", "identity", "mode", "busy", "duplicate"])
def test_stale_or_unsafe_confirmation_never_commits(setup, change):
    hass, entry, state, entries, updates = setup
    async def run():
        preview = await mod.preview_replacement(hass, entry, "http://new")
        token = preview["token"]
        if change == "expired":
            hass.data["ifm_iolink"]["replacement_previews"]["garage"]["expires"] = 0
        elif change == "wrong_token":
            token = "incorrect"
        elif change == "options":
            entry.options["ports"]["1"]["name"] = "Changed"
        elif change == "identity":
            state["serial"] = "OTHER"
        elif change == "mode":
            state["mode"] = 1
        elif change == "busy":
            hass.data["ifm_iolink"]["parameter_backups"].busy.add(("garage", 1))
        elif change == "duplicate":
            entries.append(NS(entry_id="other", unique_id="NEW", data={}))
        with pytest.raises(ValueError):
            await mod.confirm_replacement(hass, entry, token)
    asyncio.run(run())
    assert not updates and entry.unique_id == "OLD"


@pytest.mark.parametrize("mode,output", [(None, "00"), (True, "00"), (2, "01"), (2, None)])
def test_preview_rejects_unknown_modes_or_active_output(setup, mode, output):
    hass, entry, state, entries, updates = setup
    state.update(mode=mode, output=output)
    with pytest.raises(ValueError):
        asyncio.run(mod.preview_replacement(hass, entry, "http://new"))
    assert not updates


def test_smaller_master_is_rejected(setup):
    hass, entry, state, entries, updates = setup
    entry.data["ports"] = 8
    state.update(model="AL1350", ports=4)
    with pytest.raises(ValueError, match="Ports"):
        asyncio.run(mod.preview_replacement(hass, entry, "http://new"))
    assert not updates


def test_unpaused_entry_is_rejected(setup):
    hass, entry, state, entries, updates = setup
    entry.data["replacement_paused"] = False
    with pytest.raises(ValueError, match="vorbereiten"):
        asyncio.run(mod.preview_replacement(hass, entry, "http://new"))


@pytest.mark.parametrize("reserved", [False, True])
def test_target_claimed_during_final_read_is_not_adopted(setup, monkeypatch, reserved):
    hass, entry, state, entries, updates = setup
    original_factory = mod.candidate_client

    async def run():
        preview = await mod.preview_replacement(hass, entry, "http://new")
        client = original_factory(hass, entry, "http://new")
        original_multi = client.multi
        async def interleaved_multi(paths):
            result = await original_multi(paths)
            # Another config entry claims the target while our final read waits.
            entries.append(NS(entry_id="second", unique_id="LATER" if reserved else "NEW",
                              data={"registry_serial": "NEW"} if reserved else {}))
            return result
        client.multi = interleaved_multi
        monkeypatch.setattr(mod, "candidate_client", lambda *args: client)
        with pytest.raises(ValueError, match="anderen Integration"):
            await mod.confirm_replacement(hass, entry, preview["token"])
    asyncio.run(run())
    assert not updates and entry.unique_id == "OLD"


@pytest.mark.parametrize("already_adopted", [False, True])
def test_prepare_preserves_unfinished_journal(setup, monkeypatch, already_adopted):
    from custom_components.ifm_iolink import replacement_network

    hass, entry, state, entries, updates = setup
    entry.data["replacement_paused"] = False
    saved = []
    journal = {"transfer": {"serial": entry.unique_id if already_adopted else "NEW",
                            "stage": "write_attempted"}}
    class Store:
        def __init__(self, *args):
            pass
        async def async_load(self):
            return deepcopy(journal)
        async def async_save(self, value):
            saved.append(value)
    storage = ModuleType("homeassistant.helpers.storage")
    storage.Store = Store
    monkeypatch.setitem(sys.modules, storage.__name__, storage)
    async def capture(*args):
        assert already_adopted, "An unfinished journal must block before hardware reads"
        assert hass.data["ifm_iolink"]["parameter_backups"].busy == {
            (entry.entry_id, port) for port in range(1, 5)
        }
        return {}
    monkeypatch.setattr(replacement_network, "capture", capture)
    if already_adopted:
        asyncio.run(mod.pause_replacement(hass, entry))
        assert len(saved) == 1 and entry.data["replacement_paused"]
    else:
        with pytest.raises(ValueError, match="Unvollständiger Austausch"):
            asyncio.run(mod.pause_replacement(hass, entry))
        assert not saved and not updates
    assert not hass.data["ifm_iolink"]["parameter_backups"].busy
