"""Lupusec binary sensor device."""

from lupupy.devices import LupusecDevice
import lupupy.constants as CONST


class LupusecBinarySensor(LupusecDevice):
    """Class to represent an on / off, online/offline sensor."""

    def refresh(self):
        for device in self._lupusec.get_sensors():
            if device["device_id"] == self._device_id:
                self.update(device)
                return device

        return None

    @property
    def is_on(self):
        """
        Get sensor state.

        Assume offline or open (worst case).
        """
        return self.status not in (
            CONST.STATUS_OFF,
            CONST.STATUS_OFFLINE,
            CONST.STATUS_CLOSED,
            CONST.STATUS_OPEN,
        )
