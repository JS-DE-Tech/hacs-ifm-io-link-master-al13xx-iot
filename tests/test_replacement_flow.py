"""Run real replacement orchestration against a simulated master and HA boundary."""
import asyncio
from copy import deepcopy
from types import SimpleNamespace as NS

import pytest

from custom_components.ifm_iolink import replacement as rep
from custom_components.ifm_iolink import replacement_flow as flow
from custom_components.ifm_iolink import replacement_network as net
from custom_components.ifm_iolink.api import IfmError


@pytest.fixture
def system(monkeypatch):
    old = {"serial": "OLD", "model": "AL1350", "ports": 4, "url": "http://10.0.0.10/"}
    target = {"serial": "NEW", "model": "AL1352", "ports": 8}
    entry = NS(entry_id="garage", unique_id="OLD", title="Garage", domain="ifm_iolink",
               data={**old, "replacement_paused": True}, options={"ports": {}})
    network = {"dhcp": 0, "ipaddress": "10.0.0.10", "subnetmask": "255.255.255.0", "ipdefaultgateway": "10.0.0.1"}
    backup = {"entry_id": entry.entry_id, "unique_id": "OLD", "data": old, "options": {},
              "hardware": {"network": network, "modes": {"1": 3, "2": 1, "3": 2, "4": 0}, "settings": {}}}
    backup["options"] = deepcopy(entry.options)
    state = {"moved": False, "delay": 3, "code": 233, "serial": "NEW", "fail_restore": False,
             "loaded": True, "lost_network_response": False, "writes": [], "modes": {p: 3 for p in range(1, 9)}}
    hass = NS(data={"ifm_iolink": {"library": NS(all={}), "parameter_backups": NS(busy=set()), "coordinators": {}}})
    def update(item, **kwargs):
        for k, v in kwargs.items():
            setattr(item, k, v)
        hass.data["ifm_iolink"][entry.entry_id] = item
        if state["loaded"]:
            hass.data["ifm_iolink"]["coordinators"][entry.entry_id] = NS(identity=target, last_update_success=True)
    hass.config_entries = NS(async_entries=lambda domain: [entry], async_get_entry=lambda eid: entry,
                             async_update_entry=update)
    hass.async_create_task = asyncio.create_task
    class Store:
        async def async_load(self):
            return deepcopy(backup)
        async def async_save(self, value):
            backup.clear()
            backup.update(deepcopy(value))
    monkeypatch.setattr(net, "store", lambda *args: Store())
    monkeypatch.setattr(flow, "store", lambda *args: Store())
    class Client:
        def __init__(self, url):
            self.url = url.rstrip("/") + "/"
        async def identify(self):
            if self.url == old["url"]:
                if not state["moved"] or state["delay"]:
                    state["delay"] = max(0, state["delay"] - 1)
                    raise IfmError("rebooting")
            return {**target, "serial": state["serial"]}
        async def multi(self, paths):
            def value(path):
                if "/network/" in path:
                    return network[path.rsplit("/", 1)[1]]
                port = int(path.split("port[")[1].split("]")[0])
                if path.endswith("/mode"):
                    return state["modes"][port]
                return "00" if path.endswith("/pdout") else 123
            return {path: {"code": 200, "data": value(path)} for path in paths}
        async def write_network(self, values):
            state["writes"].append("network")
            state["moved"] = state["code"] != 230
            if state["lost_network_response"]:
                raise IfmError("response lost")
            return state["code"]
        async def reboot(self):
            state["writes"].append("reboot")
            state["moved"] = True
        async def write_port_mode(self, port, mode):
            state["writes"].append((port, mode))
            state["modes"][port] = mode
            if state["fail_restore"]:
                state["fail_restore"] = False
                raise IfmError("port response lost")
    monkeypatch.setattr(rep, "candidate_client", lambda h, e, url: Client(url))
    monkeypatch.setattr(net, "candidate_client", lambda h, e, url: Client(url))
    async def free(url):
        return False
    monkeypatch.setattr(net, "address_in_use", free)
    async def sleep(seconds):
        return
    monkeypatch.setattr(asyncio, "sleep", sleep)
    return hass, entry, backup, state


@pytest.mark.parametrize("code,lost", [(233, False), (230, False), (200, False), (233, True)])
def test_automatic_full_flow_waits_restores_adopts_and_confirms_ha(system, code, lost):
    hass, entry, backup, state = system
    state.update(code=code, lost_network_response=lost)
    progress = []
    async def run():
        preview = await rep.preview_replacement(hass, entry, "http://10.0.0.11/")
        result = await flow.automatic_replacement(hass, entry, preview["token"], progress.append)
        assert result["saved"] and result["ports"] == 8
    asyncio.run(run())
    assert entry.unique_id == "NEW" and entry.data["registry_serial"] == "OLD"
    assert entry.options == backup["options"] and not entry.data["replacement_paused"]
    assert state["writes"].count("network") == 1
    assert state["writes"].count("reboot") == (1 if code == 230 else 0)
    assert state["modes"] == {1: 3, 2: 1, 3: 0, 4: 0, 5: 3, 6: 3, 7: 3, 8: 3}
    assert backup["transfer"]["restore_complete"]
    assert any("warten" in p for p in progress)


def test_resume_after_lost_port_reply_never_replays_a_write(system):
    hass, entry, backup, state = system
    state["fail_restore"] = True
    async def run():
        p = await rep.preview_replacement(hass, entry, "http://10.0.0.11/")
        with pytest.raises(IfmError):
            await flow.automatic_replacement(hass, entry, p["token"], lambda _: None)
        # Simulate restart: volatile previews/jobs disappear, persisted journal remains.
        hass.data["ifm_iolink"].pop("replacement_previews", None)
        result = await flow.automatic_replacement(hass, entry, "", lambda _: None)
        assert result["saved"]
    asyncio.run(run())
    assert len(state["writes"]) == 5


def test_adopted_but_reload_unconfirmed_resumes_without_hardware_writes(system):
    hass, entry, backup, state = system
    state["loaded"] = False
    async def run():
        p = await rep.preview_replacement(hass, entry, "http://10.0.0.11/")
        with pytest.raises(ValueError, match="Neuladen"):
            await flow.automatic_replacement(hass, entry, p["token"], lambda _: None)
        writes = list(state["writes"])
        hass.data["ifm_iolink"]["coordinators"][entry.entry_id] = NS(identity=backup["automation"]["target"], last_update_success=True)
        assert (await flow.automatic_replacement(hass, entry, "", lambda _: None))["saved"]
        assert writes == state["writes"]
    asyncio.run(run())


def test_wrong_token_or_changed_target_stops_before_writes(system):
    hass, entry, backup, state = system
    async def run():
        p = await rep.preview_replacement(hass, entry, "http://10.0.0.11/")
        with pytest.raises(ValueError):
            await flow.automatic_replacement(hass, entry, "WRONG", lambda _: None)
        backup["automation"] = {"target": {"serial": "EXPECTED"}, "candidate_url": "http://10.0.0.11/"}
        with pytest.raises(ValueError, match="geändert"):
            await flow.automatic_replacement(hass, entry, p["token"], lambda _: None)
    asyncio.run(run())
    assert state["writes"] == []


def test_background_job_finishes_without_browser_waiting(system):
    hass, entry, backup, state = system
    async def run():
        p = await rep.preview_replacement(hass, entry, "http://10.0.0.11/")
        async with flow.operation_lock(hass):
            assert flow.start_job(hass, entry, p["token"]) == {"running": True}
            assert flow.running_job(hass)
        await hass.data["ifm_iolink"]["replacement_jobs"][entry.entry_id]["task"]
        status = await flow.job_status(hass, entry)
        assert not status["running"] and status["result"]["saved"] and status["error"] is None
        assert not status["resumable"]
        hass.data["ifm_iolink"]["replacement_jobs"].clear()
        assert not (await flow.job_status(hass, entry))["resumable"]
        assert not flow.operation_lock(hass).locked()
    asyncio.run(run())


def test_timeout_never_restores_or_adopts_and_exposes_resume(system):
    hass, entry, backup, state = system
    state["delay"] = 999
    async def run():
        p = await rep.preview_replacement(hass, entry, "http://10.0.0.11/")
        flow.start_job(hass, entry, p["token"])
        await hass.data["ifm_iolink"]["replacement_jobs"][entry.entry_id]["task"]
        status = await flow.job_status(hass, entry)
        assert status["error"] and status["resumable"] and not status["result"]
        assert not flow.operation_lock(hass).locked()
    asyncio.run(run())
    assert state["writes"] == ["network"]
    assert entry.unique_id == "OLD" and entry.data["replacement_paused"]
