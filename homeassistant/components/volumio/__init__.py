"""The Volumio integration."""
import asyncio
import logging

from pyvolumio import CannotConnectError, Volumio

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DATA_INFO, DATA_VOLUMIO, DOMAIN

PLATFORMS = ["media_player"]

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Volumio component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Volumio from a config entry."""

    volumio = Volumio(
        entry.data[CONF_HOST], entry.data[CONF_PORT], async_get_clientsession(hass)
    )
    try:
        info = await volumio.get_system_version()
    except CannotConnectError as error:
        raise ConfigEntryNotReady from error

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        DATA_VOLUMIO: volumio,
        DATA_INFO: info,
    }

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


def volumio_exception_handler(func):
    """Decorate Volumio calls to handle Volumio exceptions."""

    async def handler(self, *args, **kwargs):
        try:
            return await func(self, *args, **kwargs)
        except CannotConnectError as error:
            if self.available:
                # Currently this always returns True.
                # TO DO: Implement better handling of loss of connection.
                # Combine this with better update handling,
                # using DataUpdateCoordinator and CoordinatorEntity?
                # Look at Roku integration for example
                _LOGGER.error(
                    "Error communicating with API in function %s: %s",
                    func.__name__,
                    error,
                )

    return handler


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
