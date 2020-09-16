"""Support for HUAWEI routers."""
from . import DOMAIN
import voluptuous as vol
import logging
from collections import namedtuple

from homeassistant.components.device_tracker import (
    DeviceScanner,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import config_validation as cv, entity_platform, service

_LOGGER = logging.getLogger(__name__)

ICONS = {
    'DesktopComputer': 'mdi:desktop-classic',
    'laptop': 'mdi:laptop',
    'smartphone': 'mdi:cellphone-wireless',
    'game': 'mdi:gamepad-variant',
    'stb': 'mdi:television',
    'camera': 'mdi:cctv'
}

def get_scanner(hass, config):
    """Validate the configuration and return a HUAWEI scanner."""
    config = hass.data[DOMAIN]
    scanner = HuaweiH659DeviceScanner(config)
    return scanner

Device = namedtuple("Device", ["name", "ip", "mac", "state", "icon"])

class HuaweiH659DeviceScanner(DeviceScanner):
    """This class queries a router running HUAWEI HG659 firmware."""

    def __init__(self, cli):
        """Initialize the scanner."""
        # self.host = config[CONF_HOST]
        # self.username = config[CONF_USERNAME]
        # self.password = config[CONF_PASSWORD]
        self.router_client = cli
        self.last_results = []

    def scan_devices(self):
        """Scan for new devices and return a list with found device IDs."""
        self._update_info()
        return [client.mac for client in self.last_results]

    def get_device_name(self, device):
        """Return the name of the given device or None if we don't know."""
        if not self.last_results:
            return None
        for client in self.last_results:
            if client.mac == device:
                return client.name
        return None

    def _update_info(self):
        """Ensure the information from the router is up to date.

        Return boolean if scanning successful.
        """
        data = self._get_data()
        if not data:
            return False

        active_clients = [client for client in data if client.state]
        self.last_results = active_clients

        _LOGGER.debug(
            "%s Active clients: %s",
            len(active_clients),
            ",".join(f"{client.mac} {client.name}" for client in active_clients),
        )
        return True

    def _get_data(self):
        """Get the devices' data from the router.

        Returns a list with all the devices known to the router DHCP server.
        """
        devices_json = self.router_client.get_devices_response()
        devices = []
        if devices_json != False:
            for device in devices_json:
#                _LOGGER.debug("Device: {0}".format(device))
                dev = Device(
                    device['HostName'],
                    device['IPAddress'],
                    device['MACAddress'],
                    device['Active'],
                    ICONS.get(device['IconType'])
                )
 #               _LOGGER.debug("Device: {0}".format(dev))
                devices.append(dev)
        return devices
