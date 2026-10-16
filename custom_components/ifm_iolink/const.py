"""Constants for the local IO-Link integration."""

DOMAIN = "ifm_iolink"
MODELS = {"AL1350": 4, "AL1352": 8}
PLATFORMS = ["sensor", "binary_sensor", "switch"]
STATIC_URL = "/ifm_iolink_static"
DEFAULT_INTERVAL = 2
PORT_PROPERTIES = ("productname", "vendorid", "deviceid", "serial", "status", "applicationspecifictag")


def port_path(port: int, name: str) -> str:
    return f"/iolinkmaster/port[{port}]/iolinkdevice/{name}"
