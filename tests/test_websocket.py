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
    assert results[0][1]["version"].count(".") == 2
    if include_profiles:
        assert results[0][1]["profiles"] == [{"id": "pn7096"}]
    else:
        assert "profiles" not in results[0][1]


@pytest.mark.parametrize(
    "name",
    [
        "snapshot",
        "assign",
        "set_parameter_entities",
        "save_profile",
        "delete_profile",
        "debug",
        "test_profile",
        "import_profile",
        "read_parameter",
        "send_command",
        "read_parameters",
        "get_parameter_backup",
        "rename_master",
        "delete_master",
        "preview_restore",
        "restore_parameters",
        "get_restore_report",
        "preview_port_mode",
        "set_port_mode",
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


def test_assign_preserves_entities_for_same_profile_and_resets_on_change(ws):
    entry = SimpleNamespace(
        options={"ports": {"1": {"profile": "profA", "name": "", "location": "", "purpose": "", "entities": [10, 20]}}}
    )
    coordinator = SimpleNamespace(
        entry=entry, identity={"ports": 4}, library=SimpleNamespace(all={"profA": {}, "profB": {}})
    )
    updates = []
    hass = SimpleNamespace(
        tasks=[],
        data={"ifm_iolink": {"coordinators": {"entry1": coordinator}, "parameter_backups": SimpleNamespace(busy=set())}},
        config_entries=SimpleNamespace(async_update_entry=lambda entry, options: updates.append(options)),
    )
    connection = SimpleNamespace(user=SimpleNamespace(is_admin=True), send_result=lambda *a: None, send_error=lambda *a: None)

    async def call(profile):
        ws.assign(
            hass,
            connection,
            {"id": 1, "entry_id": "entry1", "port": 1, "profile": profile, "name": "", "location": "", "purpose": ""},
        )
        await asyncio.gather(*hass.tasks)
        hass.tasks.clear()

    async def run():
        await call("profA")
        assert updates[-1]["ports"]["1"]["entities"] == [10, 20]
        await call("profB")
        assert updates[-1]["ports"]["1"]["entities"] == []

    asyncio.run(run())


def test_assign_preserves_port_mode_set_by_a_previous_mode_change(ws):
    entry = SimpleNamespace(
        options={"ports": {"1": {"profile": "unknown", "name": "", "location": "", "purpose": "", "mode": 2}}}
    )
    coordinator = SimpleNamespace(entry=entry, identity={"ports": 4}, library=SimpleNamespace(all={}))
    updates = []
    hass = SimpleNamespace(
        tasks=[],
        data={"ifm_iolink": {"coordinators": {"entry1": coordinator}, "parameter_backups": SimpleNamespace(busy=set())}},
        config_entries=SimpleNamespace(async_update_entry=lambda entry, options: updates.append(options)),
    )
    connection = SimpleNamespace(user=SimpleNamespace(is_admin=True), send_result=lambda *a: None, send_error=lambda *a: None)

    async def run():
        ws.assign(
            hass,
            connection,
            {
                "id": 1,
                "entry_id": "entry1",
                "port": 1,
                "profile": "unknown",
                "name": "",
                "location": "Heizungsraum",
                "purpose": "",
            },
        )
        await asyncio.gather(*hass.tasks)

    asyncio.run(run())
    assert updates[-1]["ports"]["1"]["mode"] == 2
    assert updates[-1]["ports"]["1"]["location"] == "Heizungsraum"


def test_preview_port_mode_then_set_port_mode_updates_entry_options(ws):
    entry = SimpleNamespace(options={"ports": {"1": {"profile": "prof", "name": "Sensor"}}})
    coordinator = SimpleNamespace(
        entry=entry,
        identity={"ports": 4},
        data={"1": {"mode": 3, "connected": True, "assignment": {"name": "Sensor"}, "profile": "prof"}},
        condition_values={(1, "prof", 64): 0},
        metadata_at=1,
    )

    async def write_port_mode(port, mode):
        coordinator.data["1"]["mode"] = mode

    async def write_port_output(port, on):
        pass

    async def multi(paths):
        return {p: {"code": 200, "data": coordinator.data["1"]["mode"]} for p in paths}

    coordinator.client = SimpleNamespace(write_port_mode=write_port_mode, write_port_output=write_port_output, multi=multi)
    updates = []
    hass = SimpleNamespace(
        tasks=[],
        data={
            "ifm_iolink": {
                "coordinators": {"entry1": coordinator},
                "parameter_backups": SimpleNamespace(busy=set(), plans={}),
            }
        },
        config_entries=SimpleNamespace(async_update_entry=lambda entry, options: updates.append(options)),
    )
    results, errors = [], []
    connection = SimpleNamespace(
        user=SimpleNamespace(is_admin=True, id="admin"),
        send_result=lambda *a: results.append(a),
        send_error=lambda *a: errors.append(a),
    )

    async def run():
        ws.preview_port_mode(hass, connection, {"id": 1, "entry_id": "entry1", "port": 1, "target_mode": 2})
        await asyncio.gather(*hass.tasks)
        hass.tasks.clear()
        token = results[0][1]["token"]
        ws.set_port_mode(hass, connection, {"id": 2, "entry_id": "entry1", "port": 1, "token": token, "confirm": True})
        await asyncio.gather(*hass.tasks)

    asyncio.run(run())
    assert not errors
    assert (results[0][1]["current_mode"], results[0][1]["target_mode"]) == (3, 2)
    assert results[-1][1] == {"port": 1, "mode": 2}
    saved = updates[-1]["ports"]["1"]
    assert saved["mode"] == 2
    assert saved["profile"] == "unknown"  # a DO port cannot decode IO-Link process data
    assert saved["name"] == "Sensor"  # unrelated metadata is preserved
    assert not hass.data["ifm_iolink"]["parameter_backups"].plans  # single-use token


@pytest.mark.parametrize("target_mode", [0, 1])
def test_set_port_mode_resets_profile_for_di_and_disabled_too(ws, target_mode):
    entry = SimpleNamespace(options={"ports": {"1": {"profile": "prof", "name": "Sensor"}}})
    coordinator = SimpleNamespace(
        entry=entry,
        identity={"ports": 4},
        data={"1": {"mode": 3, "connected": False, "assignment": {"name": "Sensor"}, "profile": "prof"}},
        condition_values={},
        metadata_at=1,
    )

    async def write_port_mode(port, mode):
        coordinator.data["1"]["mode"] = mode

    async def write_port_output(port, on):
        pass

    async def multi(paths):
        return {p: {"code": 200, "data": coordinator.data["1"]["mode"]} for p in paths}

    coordinator.client = SimpleNamespace(
        write_port_mode=write_port_mode, write_port_output=write_port_output, multi=multi
    )
    updates = []
    hass = SimpleNamespace(
        tasks=[],
        data={
            "ifm_iolink": {
                "coordinators": {"entry1": coordinator},
                "parameter_backups": SimpleNamespace(busy=set(), plans={}),
            }
        },
        config_entries=SimpleNamespace(async_update_entry=lambda entry, options: updates.append(options)),
    )
    results, errors = [], []
    connection = SimpleNamespace(
        user=SimpleNamespace(is_admin=True, id="admin"),
        send_result=lambda *a: results.append(a),
        send_error=lambda *a: errors.append(a),
    )

    async def run():
        ws.preview_port_mode(hass, connection, {"id": 1, "entry_id": "entry1", "port": 1, "target_mode": target_mode})
        await asyncio.gather(*hass.tasks)
        hass.tasks.clear()
        token = results[0][1]["token"]
        ws.set_port_mode(hass, connection, {"id": 2, "entry_id": "entry1", "port": 1, "token": token, "confirm": True})
        await asyncio.gather(*hass.tasks)

    asyncio.run(run())
    assert not errors
    assert updates[-1]["ports"]["1"]["mode"] == target_mode
    assert updates[-1]["ports"]["1"]["profile"] == "unknown"


def test_port_mode_and_restore_tokens_are_not_interchangeable(ws):
    import time

    coordinator = object()
    backups = SimpleNamespace(
        busy=set(),
        plans={
            "restore-token": {
                "expires": time.monotonic() + 300,
                "user": "admin",
                "key": ("entry", 1),
                "coordinator": coordinator,
                "plan": {},
            }
        },
    )
    hass = SimpleNamespace(
        tasks=[], data={"ifm_iolink": {"parameter_backups": backups, "coordinators": {"entry": coordinator}}}
    )
    errors = []
    connection = SimpleNamespace(
        user=SimpleNamespace(is_admin=True, id="admin"), send_result=lambda *a: None, send_error=lambda *a: errors.append(a)
    )

    async def run():
        ws.set_port_mode(hass, connection, {"id": 1, "entry_id": "entry", "port": 1, "token": "restore-token", "confirm": True})
        await asyncio.gather(*hass.tasks)

    asyncio.run(run())
    assert errors
    assert "restore-token" in backups.plans  # rejected before being consumed


def test_set_parameter_entities_validates_indices_against_profile(ws):
    entry = SimpleNamespace(options={"ports": {"1": {"profile": "profA"}}})
    profile = {"id": "profA", "parameters": [{"index": 10}, {"index": 20}]}
    coordinator = SimpleNamespace(entry=entry, identity={"ports": 4}, library=SimpleNamespace(all={"profA": profile}))
    updates = []
    hass = SimpleNamespace(
        tasks=[],
        data={"ifm_iolink": {"coordinators": {"entry1": coordinator}}},
        config_entries=SimpleNamespace(async_update_entry=lambda entry, options: updates.append(options)),
    )
    results, errors = [], []
    connection = SimpleNamespace(
        user=SimpleNamespace(is_admin=True),
        send_result=lambda *a: results.append(a),
        send_error=lambda *a: errors.append(a),
    )

    async def call(indices):
        ws.set_parameter_entities(hass, connection, {"id": 1, "entry_id": "entry1", "port": 1, "indices": indices})
        await asyncio.gather(*hass.tasks)
        hass.tasks.clear()

    async def run():
        await call([20, 10])
        assert not errors
        assert updates[-1]["ports"]["1"]["entities"] == [10, 20]
        await call([10, 99])
        assert errors
        assert updates[-1]["ports"]["1"]["entities"] == [10, 20]  # unchanged: the invalid request was rejected

    asyncio.run(run())


def _command_coordinator(*, connected=True, identity_vendorid=310, identity_deviceid=602):
    profile = {
        "id": "prof",
        "match": [{"vendorid": 310, "deviceid": 602}],
        # Two commands deliberately share one index with different values, like a real
        # IO-Link "system command" parameter (e.g. calibrate empty/full tank).
        "commands": [
            {"index": 2, "value": 208, "name": "Leeren Tank abgleichen", "description": ""},
            {"index": 2, "value": 209, "name": "Vollen Tank abgleichen", "description": ""},
        ],
    }
    identity = {"vendorid": identity_vendorid, "deviceid": identity_deviceid, "serial": "abc", "status": 2}
    writes = []

    async def multi(paths):
        return {p: {"code": 200, "data": identity[p.rsplit("/", 1)[-1]]} for p in paths}

    async def write_parameter(port, index, raw):
        writes.append((port, index, raw))

    coordinator = SimpleNamespace(
        entry=SimpleNamespace(options={"ports": {"1": {"profile": "prof"}}}),
        identity={"ports": 4},
        data={"1": {"connected": connected, "profile": "prof"}},
        library=SimpleNamespace(all={"prof": profile}),
        client=SimpleNamespace(multi=multi, write_parameter=write_parameter),
    )
    return coordinator, writes


def _run_send_command(ws, coordinator, index=2, value=208, port=1):
    hass = SimpleNamespace(tasks=[], data={"ifm_iolink": {"coordinators": {"entry1": coordinator}}})
    results, errors = [], []
    connection = SimpleNamespace(
        user=SimpleNamespace(is_admin=True),
        send_result=lambda *a: results.append(a),
        send_error=lambda *a: errors.append(a),
    )

    async def run():
        ws.send_command(hass, connection, {"id": 1, "entry_id": "entry1", "port": port, "index": index, "value": value})
        await asyncio.gather(*hass.tasks)

    asyncio.run(run())
    return results, errors


def test_send_command_writes_the_encoded_value_after_identity_check(ws):
    coordinator, writes = _command_coordinator()
    results, errors = _run_send_command(ws, coordinator)
    assert not errors
    assert results[0][1] == {"sent": True}
    assert writes == [(1, 2, "D0")]


def test_send_command_picks_the_matching_value_when_index_is_shared(ws):
    coordinator, writes = _command_coordinator()
    results, errors = _run_send_command(ws, coordinator, value=209)
    assert not errors
    assert writes == [(1, 2, "D1")]


def test_send_command_rejects_matching_index_with_wrong_value(ws):
    coordinator, writes = _command_coordinator()
    results, errors = _run_send_command(ws, coordinator, value=1)
    assert errors
    assert not writes


def test_send_command_rejects_mismatched_identity_without_writing(ws):
    coordinator, writes = _command_coordinator(identity_vendorid=999)
    results, errors = _run_send_command(ws, coordinator)
    assert errors
    assert not writes


def test_send_command_rejects_when_port_not_connected(ws):
    coordinator, writes = _command_coordinator(connected=False)
    results, errors = _run_send_command(ws, coordinator)
    assert errors
    assert not writes


def test_send_command_rejects_unknown_command_index(ws):
    coordinator, writes = _command_coordinator()
    results, errors = _run_send_command(ws, coordinator, index=999)
    assert errors
    assert not writes
