"""
TODO Example Google style docstrings.
"""

import logging
import os
import pickle
import string
import time
from pathlib import Path

import demjson
import requests
import lupupy.constants as CONST
import lupupy.devices.alarm as ALARM
from lupupy.devices.binary_sensor import LupusecBinarySensor
from lupupy.devices.switch import LupusecSwitch
from lupupy.exceptions import LupusecException

_LOGGER = logging.getLogger(__name__)
HOME = str(Path.home())


class Lupusec:
    """Interface to Lupusec Webservices."""

    def __init__(self, username, password, ip_address, get_devices=False):
        """LupsecAPI constructor requires IP and credentials to the
         Lupusec Webinterface.
        """
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.api_url = "http://{}/action/".format(ip_address)
        self._request_post("login")

        self._devices = None

        try:
            file = open(HOME + "/" + CONST.HISTORY_CACHE_NAME, "rb")
            self._history_cache = pickle.load(file)
        except (OSError, IOError):
            self._history_cache = []
            pickle.dump(
                self._history_cache, open(HOME + "/" + CONST.HISTORY_CACHE_NAME, "wb")
            )

        self._panel = self.get_panel()
        self._cache_sensors = None
        self._cache_stamp_s = time.time()
        self._cache_pss = None
        self._cache_stamp_p = time.time()

        if get_devices or self._devices is None:
            self.get_devices()

    def _request_get(self, action):
        response = self.session.get(self.api_url + action, timeout=15)
        _LOGGER.debug("GET %s: %s", action, response.status_code)
        return response

    def _request_post(self, action, params=None):
        return self.session.post(self.api_url + action, data=params)

    def get_power_switches(self):
        """Get available power switches"""

        stamp_now = time.time()
        if self._cache_pss is None or stamp_now - self._cache_stamp_p > 2.0:
            self._cache_stamp_p = stamp_now

            response = self._request_get("pssStatusGet")
            response = clean_json(response.text)["forms"]
            power_switches = []
            counter = 1

            for pss in response:
                power_switch = {}

                if response[pss]["ready"] == 1:
                    power_switch["status"] = response[pss]["pssonoff"]
                    power_switch["device_id"] = counter + len(self._devices)
                    power_switch["type"] = CONST.TYPE_POWER_SWITCH
                    power_switch["name"] = response[pss]["name"]
                    power_switches.append(power_switch)
                else:
                    _LOGGER.debug("Pss skipped, not active")

                counter += 1

            self._cache_pss = power_switches

        return self._cache_pss

    def get_sensors(self):
        """Get available sensors"""

        stamp_now = time.time()
        if self._cache_sensors is None or stamp_now - self._cache_stamp_s > 2.0:
            self._cache_stamp_s = stamp_now

            response = self._request_get("sensorListGet")
            response = clean_json(response.text)["senrows"]
            sensors = []

            for device in response:
                device["status"] = device["cond"]
                device["device_id"] = device["no"]
                device.pop("cond")
                device.pop("no")
                if not device["status"]:
                    device["status"] = "Geschlossen"
                else:
                    device["status"] = None
                sensors.append(device)
            self._cache_sensors = sensors

        return self._cache_sensors

    def get_panel(self):
        """Get status of the alarm panel"""

        # we are trimming the json from Lupusec heavily, since its bullcrap
        response = self._request_get("panelCondGet")
        if response.status_code != 200:
            print(response.text)
            raise Exception("Unable to get panel")
        panel = clean_json(response.text)["updates"]
        panel["mode"] = panel["mode_st"]
        panel.pop("mode_st")
        panel["device_id"] = CONST.ALARM_DEVICE_ID
        panel["type"] = CONST.ALARM_TYPE
        panel["name"] = CONST.ALARM_NAME

        history = self.get_history()

        for histrow in history:
            if histrow not in self._history_cache:
                if CONST.MODE_ALARM_TRIGGERED in histrow[CONST.HISTORY_ALARM_COLUMN]:
                    panel["mode"] = CONST.STATE_ALARM_TRIGGERED
                self._history_cache.append(histrow)
                pickle.dump(
                    self._history_cache,
                    open(HOME + "/" + CONST.HISTORY_CACHE_NAME, "wb"),
                )

        return panel

    def get_history(self):
        """Get history of the alarm panel"""

        response = self._request_get(CONST.HISTORY_REQUEST)
        return clean_json(response.text)[CONST.HISTORY_HEADER]

    def refresh(self):
        """Do a full refresh of all devices and automations."""
        self.get_devices(refresh=True)

    def get_devices(self, refresh=False, generic_type=None):
        """Get all devices from Lupusec."""

        _LOGGER.info("Updating all devices...")

        if refresh or self._devices is None:
            if self._devices is None:
                self._devices = {}

            response_object = self.get_sensors()
            if response_object and not isinstance(response_object, (tuple, list)):
                response_object = response_object

            for device_json in response_object:
                # Attempt to reuse an existing device
                device = self._devices.get(device_json["name"])

                # No existing device, create a new one
                if device:
                    device.update(device_json)
                else:
                    device = new_device(device_json, self)

                    if not device:
                        _LOGGER.info("Device is unknown")
                        continue

                    self._devices[device.device_id] = device

            # We will be treating the Lupusec panel itself as an armable device.
            panel_json = self.get_panel()
            _LOGGER.debug("Get the panel in get_devices: %s", panel_json)

            self._panel.update(panel_json)

            alarm_device = self._devices.get("0")

            if alarm_device:
                alarm_device.update(panel_json)
            else:
                alarm_device = ALARM.create_alarm(panel_json, self)
                self._devices["0"] = alarm_device

            # Now we will handle the power switches
            switches = self.get_power_switches()
            _LOGGER.debug("Get active the power switches in get_devices: %s", switches)

            for device_json in switches:
                # Attempt to reuse an existing device
                device = self._devices.get(device_json["name"])

                # No existing device, create a new one
                if device:
                    device.update(device_json)
                else:
                    device = new_device(device_json, self)
                    if not device:
                        _LOGGER.info("Device is unknown")
                        continue
                    self._devices[device.device_id] = device

        if generic_type:
            devices = []
            for device in self._devices.values():
                if device.type is not None and device.type in generic_type[0]:
                    devices.append(device)
            return devices

        return list(self._devices.values())

    def get_device(self, device_id, refresh=False):
        """Get a single device."""

        if self._devices is None:
            self.get_devices()
            refresh = False

        device = self._devices.get(device_id)

        if device and refresh:
            device.refresh()

        return device

    def get_alarm(self, area="1", refresh=False):
        """Shortcut method to get the alarm device."""

        # TODO filter by area

        if self._devices is None:
            self.get_devices()
            refresh = False

        return self.get_device(CONST.ALARM_DEVICE_ID, refresh)

    def set_mode(self, mode):
        """Set the mode of the alarm panel"""

        resp = self._request_post("panelCondPost", {"mode": mode})
        return clean_json(resp.text)


def clean_json(textdata):
    """ Example Google style docstrings. """

    _LOGGER.debug("Input for clean json %s", textdata)

    textdata = textdata.replace("\t", "")
    i = textdata.index("\n")
    textdata = textdata[i + 1 : -2]

    return demjson.decode(textdata)


def new_device(device_json, lupusec):
    """Create new device object for the given type."""

    type_tag = device_json.get("type")

    if type_tag in CONST.TYPE_OPENING:
        return LupusecBinarySensor(device_json, lupusec)

    if type_tag in CONST.TYPE_SENSOR:
        return LupusecBinarySensor(device_json, lupusec)

    if type_tag in CONST.TYPE_SWITCH:
        return LupusecSwitch(device_json, lupusec)

    if not type_tag:
        _LOGGER.info("Device has no type")

    _LOGGER.info("Device is not known")

    return None
