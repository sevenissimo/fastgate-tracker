"""Support for FastGate FastGates."""
from __future__ import annotations

from http import HTTPStatus
import logging

import requests
import voluptuous as vol

from homeassistant.components.device_tracker import (
    DOMAIN,
    PLATFORM_SCHEMA as PARENT_PLATFORM_SCHEMA,
    DeviceScanner,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PARENT_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST, default="192.168.1.254"): cv.string,
        vol.Required(CONF_USERNAME, default="admin"): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)


def get_scanner(hass: HomeAssistant, config: ConfigType) -> FastGateDeviceScanner | None:
    """Validate the configuration and return a FastGate Device Scanner."""
    scanner = FastGateDeviceScanner(config[DOMAIN])

    return scanner if scanner.success_init else None


class FastGateDeviceScanner(DeviceScanner):
    """Class which queries a FastGate router.

    Adapted from Xiaomi scanner.
    """

    def __init__(self, config):
        """Initialize the scanner."""
        self.host = config[CONF_HOST]
        self.username = config[CONF_USERNAME]
        self.password = config[CONF_PASSWORD]

        self.last_results = {}
        self.token, self.cookies = _get_token_and_cookies(self.host, self.username, self.password)

        self.mac2name = None
        self.success_init = self.token is not None

    def scan_devices(self):
        """Scan for new devices and return a list with found device IDs."""
        self._update_info()
        return self.last_results

    def get_device_name(self, device):
        """Return the name of the given device or None if we don't know."""
        if self.mac2name is None:
            result = self._retrieve_list_with_retry()
            if result:
                self.mac2name = dict(zip(
                    [val.upper() for (key, val) in result.items() if key.endswith("_mac")],
                    [val         for (key, val) in result.items() if key.endswith("_name")] ))
            else:
                # Error, handled in the _retrieve_list_with_retry
                return
        return self.mac2name.get(device.upper(), None)

    def _update_info(self):
        """Ensure the information from the router are up to date.

        Returns true if scanning successful.
        """
        if not self.success_init:
            return False

        result = self._retrieve_list_with_retry()
        if result:
            self._store_result(result)
            return True
        return False

    def _retrieve_list_with_retry(self):
        """Retrieve the device list with a retry if token is invalid.

        Return the list if successful.
        """
        _LOGGER.debug("Refreshing device list")
        result = _retrieve_list(self.host, self.token, self.cookies)
        if result:
            return result

        _LOGGER.debug("Refreshing token and retrying device list refresh")
        self.token, self.cookies = _get_token_and_cookies(self.host, self.username, self.password)
        return _retrieve_list(self.host, self.token, self.cookies)

    def _store_result(self, result):
        """Extract and store the device list in self.last_results."""
        self.last_results = [val.upper() for (key, val) in result.items() if key.endswith("_mac")]


def _retrieve_list(host, token, cookies, **kwargs):
    """Get device list for the given host."""
    url  = f"http://{host}/status.cgi"
    data = {"nvget": "connected_device_list", "sessionKey": token}
    try:
        res = requests.get(url, params=data, cookies=cookies, timeout=10, **kwargs)
    except requests.exceptions.Timeout:
        _LOGGER.exception("Connection to the router timed out at URL %s", url)
        return
    if res.status_code != HTTPStatus.OK:
        _LOGGER.exception("Connection failed with http code %s", res.status_code)
        return
    try:
        result = res.json()
    except ValueError:
        # If json decoder could not parse the response
        _LOGGER.exception("Failed to parse response from FastGate")
        return
    try:
        return result["connected_device_list"]
    except KeyError:
        _LOGGER.exception("No list in response from FastGate. %s", result)
        return
    else:
        _LOGGER.info("Something went wrong with FastGate. Response is %s", result)
        return


def _get_token_and_cookies(host, username, password):
    """Get authentication token for the given host+username+password."""
    url  = f"http://{host}/status.cgi"
    data = {"cmd": "3", "nvget": "login_confirm", "username": username, "password": password}
    try:
        res = requests.get(url, params=data, headers={"X-XSRF-TOKEN": "0"}, timeout=5)
    except requests.exceptions.Timeout:
        _LOGGER.exception("Connection to FastGate timed out")
        return
    if res.status_code == HTTPStatus.OK:
        try:
            result = res.json()
        except ValueError:
            # If JSON decoder could not parse the response
            _LOGGER.exception("Failed to parse response from FastGate")
            return
        try:
            return (result["login_confirm"]["check_session"], res.cookies)
        except KeyError:
            error_message = (
                "FastGate token cannot be refreshed, response from "
                + "url: [%s] \nwith parameter: [%s] \nwas: [%s]"
            )
            _LOGGER.exception(error_message, url, data, result)
            return
    else:
        _LOGGER.error(
            "Invalid response: [%s] at url: [%s] with data [%s]", res, url, data
        )
