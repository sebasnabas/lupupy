"""Lupusec switch device."""

from lupupy.devices import LupusecDevice
import lupupy.constants as CONST


class LupusecSwitch(LupusecDevice):
    """Class to add switch functionality."""

    def refresh(self):
        for pss in self._lupusec.get_power_switches():
            if pss["device_id"] == self._device_id:
                self.update(pss)
                return pss

        return None

    def __set_status(self, status):
        """Set status of power switch."""
        raise NotImplementedError

    def switch_on(self):
        """Turn the switch on."""
        success = self.__set_status(CONST.STATUS_ON_INT)

        if success:
            self._json_state["status"] = CONST.STATUS_ON

        return success

    def switch_off(self):
        """Turn the switch off."""
        success = self.__set_status(CONST.STATUS_OFF_INT)

        if success:
            self._json_state["status"] = CONST.STATUS_OFF

        return success

    @property
    def is_on(self):
        """
        Get switch state.

        Assume switch is on.
        """
        return self.status not in (CONST.STATUS_OFF, CONST.STATUS_OFFLINE)

    @property
    def is_dimmable(self):
        """Device dimmable."""
        return False
