"""Constants for the local IO-Link integration."""

DOMAIN = "ifm_iolink"
MODELS = {"AL1350": 4, "AL1352": 8}
PLATFORMS = ["sensor", "binary_sensor", "number", "select", "switch"]
STATIC_URL = "/ifm_iolink_static"
DEFAULT_INTERVAL = 2
PORT_PROPERTIES = ("productname", "vendorid", "deviceid", "serial", "status", "applicationspecifictag")
MASTER_DIAGNOSTIC_PATHS = (
    "/processdatamaster/temperature",
    "/processdatamaster/voltage",
    "/processdatamaster/current",
    "/processdatamaster/supervisionstatus",
)


def port_path(port: int, name: str) -> str:
    return f"/iolinkmaster/port[{port}]/iolinkdevice/{name}"
