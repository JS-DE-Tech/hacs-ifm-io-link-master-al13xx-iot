"""Exercise panel commands against HA's synchronous decorator/scheduler contract.

This isolates the connection boundary; it is not a full Home Assistant test.
The connection deliberately exposes no require_admin method.
"""

import asyncio
import importlib
import sys
from functools import wraps
from types import ModuleType, SimpleNamespace

import pytest
import voluptuous as vol
from test_digital import fixture as digital_fixture


@pytest.fixture
def ws(monkeypatch):
    for name in ("homeassistant", "homeassistant.components"):
        module = ModuleType(name)
        module.__path__ = []
        monkeypatch.setitem(sys.modules, name, module)
    api = ModuleType("homeassistant.components.websocket_api")

    def command(schema):
        def decorate(fn):
            fn.schema = vol.Schema({vol.Required("id"): int, **schema})
            return fn

        return decorate

    def require_admin(fn):
        @wraps(fn)
        def guarded(hass, connection, message):
            if connection.user is None or not connection.user.is_admin:
                raise PermissionError
            fn(hass, connection, message)

        return guarded

    def async_response(fn):
        @wraps(fn)
        def scheduled(hass, connection, message):
            hass.tasks.append(asyncio.create_task(fn(hass, connection, message)))

        return scheduled

    api.websocket_command = command
    api.require_admin = require_admin
    api.async_response = async_response
    monkeypatch.setitem(sys.modules, api.__name__, api)
    name = "custom_components.ifm_iolink.websocket"
    sys.modules.pop(name, None)
    yield importlib.import_module(name)
    sys.modules.pop(name, None)


@pytest.mark.parametrize("include_profiles", [True, False])
def test_existing_masters_load_in_panel(ws, include_profiles):
    results = []
    connection = SimpleNamespace(user=SimpleNamespace(is_admin=True), send_result=lambda *args: results.append(args))
    masters = [{"entry_id": "garage"}, {"entry_id": "heizung"}]
    library = SimpleNamespace(revision=3, all={"pn7096": {"id": "pn7096"}})
    hass = SimpleNamespace(
        tasks=[],
        data={
            "ifm_iolink": {
                "library": library,
                "coordinators": {m["entry_id"]: SimpleNamespace(snapshot=lambda m=m: m) for m in masters},
            }
        },
    )

    async def run():
        message = ws.snapshot.schema({"id": 1, "type": "ifm_iolink/snapshot", "include_profiles": include_profiles})
        ws.snapshot(hass, connection, message)
        await asyncio.gather(*hass.tasks)

    asyncio.run(run())
    assert results[0][0] == 1
    assert results[0][1]["masters"] == masters
    assert results[0][1]["profile_revision"] == 3
    if include_profiles:
        assert results[0][1]["profiles"] == [{"id": "pn7096"}]
    else:
        assert "profiles" not in results[0][1]


@pytest.mark.parametrize("mode,success", [(2, True), (3, False)])
def test_panel_output_uses_guarded_write(ws, mode, success):
    hass, coordinator, state, writes, _ = digital_fixture()
    state["mode"] = mode
    hass.tasks = []
    results, errors = [], []
    connection = SimpleNamespace(
        user=SimpleNamespace(is_admin=True),
        send_result=lambda *args: results.append(args),
        send_error=lambda *args: errors.append(args),
    )

    async def refresh():
        pass

    coordinator.async_request_refresh = refresh

    async def run():
        message = ws.set_digital_output.schema(
            {"id": 1, "type": "ifm_iolink/set_digital_output", "entry_id": "entry", "port": 1, "on": True}
        )
        ws.set_digital_output(hass, connection, message)
        await asyncio.gather(*hass.tasks)

    asyncio.run(run())
    assert bool(results) is success
    assert bool(errors) is not success
    assert writes == ([(1, True)] if success else [])


@pytest.mark.parametrize(
    "name",
    [
        "snapshot",
        "set_digital_output",
        "set_port_mode",
        "assign",
        "save_profile",
        "delete_profile",
        "debug",
        "test_profile",
        "import_profile",
        "read_parameter",
        "read_parameters",
        "get_parameter_backup",
        "rename_master",
        "delete_master",
        "preview_restore",
        "restore_parameters",
        "get_restore_report",
    ],
)
@pytest.mark.parametrize("user", [None, SimpleNamespace(is_admin=False)])
def test_commands_reject_non_admin_before_scheduling(ws, name, user):
    hass = SimpleNamespace(tasks=[])
    connection = SimpleNamespace(user=user)
    with pytest.raises(PermissionError):
        getattr(ws, name)(hass, connection, {"id": 1})
    assert hass.tasks == []


@pytest.mark.parametrize(
    "domain,confirmation,expected",
    [("other", "Master", False), ("ifm_iolink", "wrong", False), ("ifm_iolink", "Master", True)],
)
def test_delete_targets_only_confirmed_iolink_entry(ws, domain, confirmation, expected):
    from unittest.mock import AsyncMock

    entry = SimpleNamespace(domain=domain, title="Master", entry_id="selected")
    removed = AsyncMock(return_value={"require_restart": False})
    hass = SimpleNamespace(
        tasks=[],
        config_entries=SimpleNamespace(async_get_entry=lambda _: entry, async_remove=removed),
        data={"ifm_iolink": {"coordinators": {"selected": object(), "other": object()}}},
    )
    results, errors = [], []
    connection = SimpleNamespace(
        user=SimpleNamespace(is_admin=True),
        send_result=lambda *args: results.append(args),
        send_error=lambda *args: errors.append(args),
    )

    async def run():
        ws.delete_master(hass, connection, {"id": 1, "entry_id": "selected", "confirm_name": confirmation})
        await asyncio.gather(*hass.tasks)

    asyncio.run(run())
    assert bool(results) == expected
    assert bool(errors) != expected
    assert "other" in hass.data["ifm_iolink"]["coordinators"]
    if expected:
        removed.assert_awaited_once_with("selected")
    else:
        removed.assert_not_awaited()


@pytest.mark.parametrize("issue", ["valid", "expired", "user", "port", "unconfirmed", "master", "replay"])
def test_restore_confirmation_bound_to_preview(ws, monkeypatch, issue):
    import time

    results, errors, executed = [], [], []
    coordinator = object()
    saved = {
        "expires": time.monotonic() + 300,
        "user": "admin",
        "key": ("entry", 1),
        "coordinator": coordinator,
        "plan": {},
    }
    backups = SimpleNamespace(busy=set(), plans={"token": saved})
    hass = SimpleNamespace(
        tasks=[], data={"ifm_iolink": {"parameter_backups": backups, "coordinators": {"entry": coordinator}}}
    )
    connection = SimpleNamespace(
        user=SimpleNamespace(is_admin=True, id="admin"),
        send_result=lambda *a: results.append(a),
        send_error=lambda *a: errors.append(a),
    )
    message = {"id": 1, "entry_id": "entry", "port": 1, "token": "token", "confirm": True}
    if issue == "expired":
        saved["expires"] = 0
    if issue == "user":
        saved["user"] = "other"
    if issue == "port":
        saved["key"] = ("entry", 2)
    if issue == "unconfirmed":
        message["confirm"] = False
    if issue == "master":
        saved["coordinator"] = object()
    monkeypatch.setattr(ws, "coordinator_for", lambda *a: coordinator)

    async def execute(*a, **k):
        executed.append(True)
        return {"status": "completed"}

    monkeypatch.setattr(ws, "execute_restore", execute)

    async def run():
        ws.restore_parameters(hass, connection, message)
        await asyncio.gather(*hass.tasks)
        if issue == "replay":
            ws.restore_parameters(hass, connection, message)
            await asyncio.gather(*hass.tasks)

    asyncio.run(run())
    assert len(executed) == (1 if issue in ("valid", "replay") else 0)
    assert bool(errors) == (issue != "valid")
    assert not backups.busy


@pytest.mark.parametrize("confirm", [True, False])
def test_mode_command_requires_confirmation(ws, confirm):
    hass, c, state, writes, _ = digital_fixture()
    hass.tasks = []
    results, errors = [], []
    connection = SimpleNamespace(
        user=SimpleNamespace(is_admin=True),
        send_result=lambda *a: results.append(a),
        send_error=lambda *a: errors.append(a),
    )

    async def write_mode(port, mode):
        writes.append((port, mode))
        state["mode"] = mode

    async def refresh():
        pass

    c.client.write_port_mode = write_mode
    c.async_request_refresh = refresh

    async def run():
        msg = ws.set_port_mode.schema(
            {
                "id": 1,
                "type": "ifm_iolink/set_port_mode",
                "entry_id": "entry",
                "port": 1,
                "expected_mode": 2,
                "target_mode": 1,
                "confirm": confirm,
            }
        )
        ws.set_port_mode(hass, connection, msg)
        await asyncio.gather(*hass.tasks)

    asyncio.run(run())
    assert bool(results) == confirm
    assert bool(errors) != confirm
    assert writes == ([(1, 1)] if confirm else [])
