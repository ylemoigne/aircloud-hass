"""The Hitachi Air Cloud integration."""
from __future__ import annotations

from aircloudy import HitachiAirCloud
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .const import DOMAIN

PLATFORMS: list[Platform] = [Platform.CLIMATE]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hitachi Air Cloud from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    ac = HitachiAirCloud(entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])
    await ac.connect()
    hass.data[DOMAIN][entry.entry_id] = ac

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        ac:HitachiAirCloud = hass.data[DOMAIN].pop(entry.entry_id)
        await ac.close()

    return unload_ok
