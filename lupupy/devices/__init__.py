"""
Init file for devices directory.
"""

import json
import logging

from abc import ABC, abstractmethod


class Device(ABC):
    """Class to represent each Lupusec device."""

    def __init__(self, data, lupusec):
        """Set up Lupusec device."""
        self._data = data
        self._lupusec = lupusec

    @abstractmethod
    def refresh(self):
        """Refresh a device"""
