import asyncio
import json

import aiohttp
import pytest
from aiohttp import web

from custom_components.ifm_iolink.api import IfmAuthError, IfmClient, IfmError, discover, normalize_url


async def serve(handler, test):
    app = web.Application()
    app.router.add_post("/", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        async with aiohttp.ClientSession() as session:
            await test(IfmClient(session, f"http://127.0.0.1:{port}"))
    finally:
        await runner.cleanup()


def test_identification_uses_deviceinfo_and_accepts_al1352():
    async def handler(request):
        body = await request.json()
        assert body["adr"] == "/getdatamulti"
        return web.json_response(
            {
                "code": 200,
                "data": {
                    path: {"code": 200, "data": value}
                    for path, value in zip(body["data"]["datatosend"], ["AL1352", "SERIAL", "1.0"], strict=True)
                },
            }
        )

    async def check(client):
        assert await client.identify() == {"model": "AL1352", "serial": "SERIAL", "firmware": "1.0", "ports": 8}

    asyncio.run(serve(handler, check))


def test_chunked_response_and_request_serialization():
    active = 0

    async def handler(request):
        nonlocal active
        active += 1
        assert active == 1
        response = web.StreamResponse()
        await response.prepare(request)
        await response.write(b'{"code":200,')
        await asyncio.sleep(0.02)
        await response.write(b'"data":{"ok":true}}')
        await response.write_eof()
        active -= 1
        return response

    async def check(client):
        results = await asyncio.gather(client.request("/getidentity"), client.request("/getidentity"))
        assert results == [{"ok": True}, {"ok": True}]

    asyncio.run(serve(handler, check))


@pytest.mark.parametrize(
    "payload,status,error",
    [
        ({"code": 503}, 200, IfmError),
        ({"code": 403}, 200, IfmAuthError),
        ({}, 401, IfmAuthError),
        ([], 200, IfmError),
        ({"code": 200, "data": "bad"}, 200, IfmError),
    ],
)
def test_protocol_failures(payload, status, error):
    async def handler(request):
        return web.Response(text=json.dumps(payload), status=status)

    async def check(client):
        with pytest.raises(error):
            await client.request("/getidentity")

    asyncio.run(serve(handler, check))


def test_never_sends_password_over_http_or_write_commands():
    async def check():
        client = IfmClient(None, "http://localhost", password="secret")
        with pytest.raises(IfmAuthError):
            await client.request("/getidentity")
        with pytest.raises(ValueError):
            await client.request("/setdata", {})

    asyncio.run(check())


@pytest.mark.parametrize(
    "url", ["ftp://host", "http://user:password@host", "http://host?a=b", "http://host/#fragment", "host name"]
)
def test_invalid_urls(url):
    with pytest.raises(ValueError):
        normalize_url(url)


@pytest.mark.parametrize("cidr", ["10.0.0.0/8", "8.8.8.0/24", "127.0.0.0/24", "::1/128", "169.254.0.0/24", "bad"])
def test_scan_bounds(cidr):
    with pytest.raises(ValueError):
        asyncio.run(discover(None, cidr))


@pytest.mark.parametrize("payload", [{"code": 200}, {"code": 200, "data": None}, {"code": 200, "data": {}}])
def test_parameter_write_payload_and_empty_success(payload):
    calls = []

    async def handler(request):
        calls.append(await request.json())
        return web.json_response(payload)

    async def check(client):
        assert await client.write_parameter(2, 500, "ab") == {}

    asyncio.run(serve(handler, check))
    assert calls == [
        {
            "code": "request",
            "cid": 1,
            "adr": "/iolinkmaster/port[2]/iolinkdevice/iolwriteacyclic",
            "data": {"index": 500, "subindex": 0, "value": "AB"},
        }
    ]


def test_failed_parameter_write_is_not_retried():
    calls = []

    async def handler(request):
        calls.append(await request.json())
        return web.json_response({"code": 503})

    async def check(client):
        with pytest.raises(IfmError):
            await client.write_parameter(1, 500, "01")

    asyncio.run(serve(handler, check))
    assert len(calls) == 1


@pytest.mark.parametrize("payload", [{"code": 200}, {"code": 200, "data": None}, {"code": 200, "data": {}}])
def test_port_mode_write_payload_and_empty_success(payload):
    calls = []

    async def handler(request):
        calls.append(await request.json())
        return web.json_response(payload)

    async def check(client):
        assert await client.write_port_mode(3, 2) == {}

    asyncio.run(serve(handler, check))
    assert calls == [
        {"code": "request", "cid": 1, "adr": "/iolinkmaster/port[3]/mode/setdata", "data": {"newvalue": 2}}
    ]


@pytest.mark.parametrize(
    "port,mode", [(0, 3), (9, 3), ("1", 3), (1, 4), (1, -1), (1, "3"), (1, None)]
)
def test_port_mode_write_rejects_invalid_port_or_mode(port, mode):
    async def check():
        client = IfmClient(None, "http://localhost")
        with pytest.raises(ValueError):
            await client.write_port_mode(port, mode)

    asyncio.run(check())


@pytest.mark.parametrize("on,expected", [(True, "01"), (False, "00")])
def test_port_output_write_payload(on, expected):
    calls = []

    async def handler(request):
        calls.append(await request.json())
        return web.json_response({"code": 200})

    async def check(client):
        assert await client.write_port_output(7, on) == {}

    asyncio.run(serve(handler, check))
    assert calls == [
        {"code": "request", "cid": 1, "adr": "/iolinkmaster/port[7]/iolinkdevice/pdout/setdata", "data": {"newvalue": expected}}
    ]


@pytest.mark.parametrize("port,on", [(0, True), (9, True), ("1", True), (1, "on"), (1, 1), (1, None)])
def test_port_output_write_rejects_invalid_port_or_value(port, on):
    async def check():
        client = IfmClient(None, "http://localhost")
        with pytest.raises(ValueError):
            await client.write_port_output(port, on)

    asyncio.run(check())
