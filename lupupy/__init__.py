"""
TODO Example Google style docstrings.
"""

from pathlib import Path
import logging
import os
import pickle
import re
import string
import time

import demjson
import requests
import lupupy.constants as CONST

from lupupy.devices.area import Area
from lupupy.devices.binary_sensor import BinarySensor

_LOGGER = logging.getLogger(__name__)
HOME = str(Path.home())


class Lupusec:
    """Interface to Lupusec Webservices."""

    def __init__(self, username, password, ip_address):
        """
        LupsecAPI constructor requires IP and credentials to the Lupusec
        Webinterface.
        """
        self._token = None

        self.session = requests.Session()
        self.session.auth = (username, password)
        self.api_url = "http://{}/action/".format(ip_address)

        self._devices_cache = None
        self._devices_refreshed = time.time()

        self._panel_cache = None
        self._panel_refreshed = time.time()

        self._areas = [Area(area, self) for area in self.fetch_panel()]
        self._sensors = [BinarySensor(device, self) for device in self.fetch_sensors()]

    def _request_get(self, action):
        response = self.session.get(self.api_url + action, timeout=15)
        _LOGGER.debug("GET %s: %s", action, response.status_code)
        return response

    def _request_post(self, action, params=None):
        # self._request_post("login")

        if self._token is None:
            response = self.session.post(self.api_url + "tokenGet").json()

            if response["result"] != 1:
                raise Exception("Fetching token failed")

            self._token = response["message"]

        return self.session.post(
            self.api_url + action, data=params, headers={"x-token": self._token}
        )

    def fetch_sensors(self):
        """Get available binary sensors"""
        now = time.time()

        if self._devices_cache is not None and now - self._devices_refreshed <= 2.0:
            return self._devices_cache

        response = self._request_get("deviceListGet")

        if response.status_code != 200:
            raise Exception("Unable to get devices: %s" % response.text)

        self._devices_refreshed = now

        sensors = []
        for device in decode(response.text)["senrows"]:
            device_info = CONST.DEVICES.get(int(device.get("type")))

            if device_info is not None and device_info.get("kind") == "binary_sensor":
                sensors.append(device)

        self._devices_cache = sensors

        return self._devices_cache

    def fetch_panel(self):
        """Get status of the alarm panel"""
        now = time.time()

        if self._panel_cache is not None and now - self._panel_refreshed <= 2.0:
            return self._panel_cache

        response = self._request_get("panelCondGet")

        if response.status_code != 200:
            raise Exception("Unable to get panel: %s" % response.text)

        self._panel_refreshed = now

        panel = decode(response.text)["updates"]

        self._panel_cache = [
            {"id": 1, "mode": panel["mode_a1"], "alarm": panel["alarm_ex"]},
            {"id": 2, "mode": panel["mode_a2"], "alarm": panel["alarm_ex"]},
        ]

        return self._panel_cache

    @property
    def areas(self):
        """Configured areas of the alarm panel"""
        return self._areas

    @property
    def sensors(self):
        """Configured areas of the alarm panel"""
        return self._sensors

    def set_mode(self, mode, area):
        """Set the mode of the alarm panel"""
        resp = self._request_post("panelCondPost", {"mode": mode, "area": area})
        return decode(resp.text)


def decode(raw):
    """Decodes a string to json"""
    _LOGGER.debug("Input for clean json %s", raw)
    return demjson.decode(raw.replace("\t", ""))
