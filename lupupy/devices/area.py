"""
Lupusec Area
"""

import logging

from lupupy.devices import Device

_LOGGER = logging.getLogger(__name__)

DISARM = 0
ARM = 1
HOME1 = 2
HOME2 = 3
HOME3 = 4


class Area(Device):
    """Class to represent the Lupusec alarm as a device."""

    def refresh(self):
        """Refresh the alarm device."""
        for area in self._lupusec.fetch_panel():
            if area["id"] == self.id:
                self._data = area
                break

    def set_home(self, level=1):
        """Arm Lupusec to home mode."""
        if level == 1:
            return self.__set_mode(HOME1)
        if level == 2:
            return self.__set_mode(HOME2)
        if level == 3:
            return self.__set_mode(HOME3)

        raise Exception("invalid level")

    def set_armed(self):
        """Arm Lupusec to armed mode."""
        return self.__set_mode(ARM)

    def set_disarmed(self):
        """Arm Lupusec to stay mode."""
        return self.__set_mode(DISARM)

    def __set_mode(self, mode):
        """Set Lupusec alarm mode."""

        if mode not in [ARM, DISARM, HOME1, HOME2, HOME3]:
            return _LOGGER.warning("Invalid mode")

        response = self._lupusec.set_mode(mode=mode, area=self.id)

        if response["result"] != 1:
            _LOGGER.warning("Mode setting unsuccessful: %s", response["message"])
            return False

        self._data["mode"] = r"{AREA_MODE_%s}" % mode
        _LOGGER.info("Mode set to: %s", self.mode)

        return True

    @property
    def id(self):  # pylint: disable=C0103
        """The area id"""
        return self._data.get("id")

    @property
    def name(self):
        """The area name"""
        return "Area {0}".format(self.id)

    @property
    def mode(self):
        """Get alarm mode."""
        mode_str = self._data.get("mode")

        if mode_str == "{AREA_MODE_0}":
            return DISARM
        if mode_str == "{AREA_MODE_1}":
            return ARM
        if mode_str == "{AREA_MODE_2}":
            return HOME1
        if mode_str == "{AREA_MODE_3}":
            return HOME2
        if mode_str == "{AREA_MODE_4}":
            return HOME3

        raise Exception("invalid mode: %s" % mode_str)

    @property
    def is_disarmed(self):
        """Is alarm in standby mode."""
        return self.mode == DISARM

    @property
    def is_armed(self):
        """Is alarm in away mode."""
        return self.mode == ARM

    @property
    def is_home(self):
        """Is alarm in home mode."""
        return self.mode in [HOME1, HOME2, HOME3]

    @property
    def is_alarm_triggered(self):
        """Is alarm in alarm triggered mode."""
        return self.mode > 0 and int(self._data.get("alarm")) == 1

    def __repr__(self):
        mode = (
            "Disarmed"
            if self.mode == DISARM
            else "Armed"
            if self.mode == ARM
            else "Home 1"
            if self.mode == HOME1
            else "Home 2"
            if self.mode == HOME2
            else "Home 3"
            if self.mode == HOME3
            else ""
        )

        alarm_triggered = " [ALARM TRIGGERED!]" if self.is_alarm_triggered else ""

        return "Area {0}: {1}{2}".format(self.id, mode, alarm_triggered)
