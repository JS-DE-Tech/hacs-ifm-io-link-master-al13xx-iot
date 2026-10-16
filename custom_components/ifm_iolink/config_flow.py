"""User setup, DHCP discovery, subnet search and connection settings."""

import ipaddress

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import network
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from .api import IfmAuthError, IfmClient, IfmError, discover, normalize_url
from .const import DEFAULT_INTERVAL, DOMAIN


def connection_schema(defaults=None):
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required("url", default=defaults.get("url", "")): str,
            vol.Optional("name", default=defaults.get("name", "IO-Link Master")): str,
            vol.Optional("username", default=defaults.get("username", "administrator")): str,
            vol.Optional("password", default=defaults.get("password", "")): str,
            vol.Optional("verify_ssl", default=defaults.get("verify_ssl", True)): bool,
        }
    )


class IfmConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self.found = {}
        self.defaults = {}

    def _reserved_serial(self, serial):
        return any(entry.data.get("registry_serial") == serial
                   for entry in self.hass.config_entries.async_entries(DOMAIN))

    async def async_step_user(self, user_input=None):
        return self.async_show_menu(step_id="user", menu_options=["manual", "scan"])

    async def async_step_manual(self, user_input=None):
        errors = {}
        if user_input is not None:
            self.defaults = user_input
            try:
                client = IfmClient(
                    async_get_clientsession(self.hass),
                    user_input["url"],
                    user_input.get("username", ""),
                    user_input.get("password", ""),
                    user_input.get("verify_ssl", True),
                )
                identity = await client.identify()
                if self._reserved_serial(identity["serial"]):
                    return self.async_abort(reason="already_configured")
                await self.async_set_unique_id(identity["serial"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input.get("name") or identity["model"],
                    data={**user_input, "url": client.url, **identity},
                    options={"interval": DEFAULT_INTERVAL, "ports": {}},
                )
            except IfmAuthError:
                errors["base"] = "invalid_auth"
            except (IfmError, ValueError):
                errors["base"] = "cannot_connect"
        return self.async_show_form(step_id="manual", data_schema=connection_schema(self.defaults), errors=errors)

    async def async_step_scan(self, user_input=None):
        errors = {}
        default_cidr = "192.168.1.0/24"
        for adapter in await network.async_get_adapters(self.hass):
            for address in adapter.get("ipv4", []):
                parsed = ipaddress.ip_address(address["address"])
                if parsed.is_private and not parsed.is_loopback and not parsed.is_link_local:
                    default_cidr = str(ipaddress.ip_network(f"{parsed}/24", strict=False))
                    break
        if user_input:
            try:
                self.found = {
                    item["url"]: item
                    for item in await discover(async_get_clientsession(self.hass), user_input["network"])
                }
                if self.found:
                    return await self.async_step_select()
                errors["base"] = "none_found"
            except ValueError:
                errors["base"] = "invalid_network"
        return self.async_show_form(
            step_id="scan", data_schema=vol.Schema({vol.Required("network", default=default_cidr): str}), errors=errors
        )

    async def async_step_select(self, user_input=None):
        if user_input:
            if user_input["url"] not in self.found:
                return self.async_abort(reason="cannot_connect")
            item = self.found[user_input["url"]]
            self.defaults = {"url": item["url"], "name": f"{item['model']} · {item['serial']}"}
            return await self.async_step_manual()
        options = [
            {"value": url, "label": f"{item['model']} · {url} · {item['serial']}"} for url, item in self.found.items()
        ]
        return self.async_show_form(
            step_id="select",
            data_schema=vol.Schema({vol.Required("url"): SelectSelector(SelectSelectorConfig(options=options))}),
        )

    async def async_step_dhcp(self, discovery_info):
        self.defaults = {"url": f"http://{discovery_info.ip}/"}
        try:
            identity = await IfmClient(async_get_clientsession(self.hass), self.defaults["url"]).identify()
        except IfmError:
            return self.async_abort(reason="cannot_connect")
        if self._reserved_serial(identity["serial"]):
            return self.async_abort(reason="already_configured")
        await self.async_set_unique_id(identity["serial"])
        self._abort_if_unique_id_configured()
        self.defaults["name"] = identity["model"]
        self.context["title_placeholders"] = {"name": identity["model"]}
        return await self.async_step_manual()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return IfmOptionsFlow()


class IfmOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors = {}
        defaults = {**self.config_entry.data, "interval": self.config_entry.options.get("interval", DEFAULT_INTERVAL)}
        if user_input:
            try:
                settings = {key: user_input[key] for key in ("url", "username", "password", "verify_ssl")}
                settings["url"] = normalize_url(settings["url"])
                client = IfmClient(async_get_clientsession(self.hass), **settings)
                identity = await client.identify()
                if identity["serial"] != self.config_entry.unique_id:
                    errors["base"] = "wrong_device"
                else:
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        title=user_input.get("name") or self.config_entry.title,
                        data={
                            **self.config_entry.data,
                            **settings,
                            "name": user_input.get("name", self.config_entry.title),
                        },
                    )
                    return self.async_create_entry(
                        title="", data={**self.config_entry.options, "interval": user_input["interval"]}
                    )
            except IfmAuthError:
                errors["base"] = "invalid_auth"
            except (IfmError, ValueError):
                errors["base"] = "cannot_connect"
        schema = connection_schema(defaults).extend(
            {
                vol.Required("interval", default=defaults["interval"]): vol.All(
                    vol.Coerce(int), vol.Range(min=2, max=3600)
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
