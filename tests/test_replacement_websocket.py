"""Automation scheduling, confirmation and cancellation boundaries."""
import asyncio
import sys
from types import ModuleType
from types import SimpleNamespace as NS

import pytest
from test_websocket import ws  # noqa: F401 -- shared fixture

from custom_components.ifm_iolink import replacement_flow as flow
from custom_components.ifm_iolink import replacement_network as net


@pytest.mark.parametrize("case", ["unconfirmed", "busy", "status", "cancel_after_write"])
def test_command_boundaries(ws, monkeypatch, case):  # noqa: F811 -- pytest fixture
    helper = ModuleType("homeassistant.helpers.aiohttp_client")
    helper.async_get_clientsession = lambda h: None
    monkeypatch.setitem(sys.modules, helper.__name__, helper)
    entry = NS(entry_id="garage", domain="ifm_iolink", data={"replacement_paused": True})
    updates = []
    hass = NS(tasks=[], data={"ifm_iolink": {}}, config_entries=NS(
        async_get_entry=lambda eid: entry, async_update_entry=lambda *args, **kwargs: updates.append(kwargs)))
    results, errors = [], []
    connection = NS(user=NS(is_admin=True), send_result=lambda *args: results.append(args),
                    send_error=lambda *args: errors.append(args))
    class Store:
        async def async_load(self):
            return {"transfer": {"stage": "write_attempted"}}
    monkeypatch.setattr(net, "store", lambda *args: Store())
    monkeypatch.setattr(flow, "store", lambda *args: Store())
    async def run():
        lock = flow.operation_lock(hass)
        if case in ("busy", "status"):
            await lock.acquire()
        action = "job_status" if case == "status" else "cancel" if case == "cancel_after_write" else "run"
        message = ws.replacement.schema({"id": 1, "type": "ifm_iolink/replacement", "entry_id": "garage",
                                         "action": action, "confirm": case != "unconfirmed"})
        ws.replacement(hass, connection, message)
        await asyncio.gather(*hass.tasks)
        if case in ("busy", "status"):
            assert lock.locked()  # Status reads must not release another operation's lock.
            lock.release()
        else:
            assert not lock.locked()
    asyncio.run(run())
    assert not updates and not hass.data["ifm_iolink"].get("replacement_jobs")
    if case == "status":
        assert results and not errors and results[0][1]["resumable"]
    else:
        assert errors and not results
