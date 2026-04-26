from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_PROVIDER, CONF_USERNAME, CONF_PASSWORD
from .coordinator import FoodBoxCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = FoodBoxCoordinator(
        hass,
        entry.data[CONF_PROVIDER],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        # Reset combined-entity creation guards when the last account is removed
        remaining = [v for v in hass.data[DOMAIN].values() if isinstance(v, FoodBoxCoordinator)]
        if not remaining:
            hass.data[DOMAIN].pop("_combined_sensors_added", None)
            hass.data[DOMAIN].pop("_combined_binary_added", None)
    return unload_ok
