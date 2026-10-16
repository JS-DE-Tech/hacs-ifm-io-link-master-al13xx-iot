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


@pytest.mark.parametrize("code", [200, 230, 233, 231, 500])
def test_network_block_status_is_not_accepted_for_other_writes(code):
    from custom_components.ifm_iolink.replacement_network import NETWORK_KEYS

    values = dict(zip(NETWORK_KEYS, [0, "10.100.1.241", "255.255.252.0", "10.100.0.1"], strict=True))
    async def handler(request):
        body = await request.json()
        if body["adr"] == "/iotsetup/network/setblock":
            assert body["data"] == {"datatoset": values}
        return web.json_response({"code": code})
    async def check(client):
        if code in (200, 230, 233):
            assert await client.write_network(values) == code
        else:
            with pytest.raises(IfmError):
                await client.write_network(values)
        if code != 200:
            with pytest.raises(IfmError):
                await client.write_port_mode(4, 0)
            with pytest.raises(IfmError):
                await client.reboot()
    asyncio.run(serve(handler, check))


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


@pytest.mark.parametrize("on,raw", [(True, "01"), (False, "00")])
def test_digital_output_writes_one_byte(on, raw):
    calls = []

    async def handler(request):
        calls.append(await request.json())
        return web.json_response({"code": 200})

    async def check(client):
        await client.write_port_output(2, on)
        with pytest.raises(ValueError):
            await client.write_port_output(2, 1)
        with pytest.raises(ValueError):
            await client.write_port_output(True, True)

    asyncio.run(serve(handler, check))
    assert len(calls) == 1
    assert calls[0]["adr"] == "/iolinkmaster/port[2]/iolinkdevice/pdout/setdata"
    assert calls[0]["data"] == {"newvalue": raw}


@pytest.mark.parametrize("mode", [0, 1, 2, 3])
def test_mode_api_payload(mode):
    calls = []

    async def handler(request):
        calls.append(await request.json())
        return web.json_response({"code": 200})

    async def check(client):
        await client.write_port_mode(8, mode)
        for port, value in [(True, mode), (9, mode), (1, True), (1, 4)]:
            with pytest.raises(ValueError):
                await client.write_port_mode(port, value)

    asyncio.run(serve(handler, check))
    assert len(calls) == 1
    assert calls[0]["adr"] == "/iolinkmaster/port[8]/mode/setdata"
    assert calls[0]["data"] == {"newvalue": mode}
