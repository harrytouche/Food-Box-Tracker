from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, UPDATE_INTERVAL, PROVIDER_GOUSTO, PROVIDER_GREEN_CHEF, SIGNAL_COORDINATOR_UPDATED
from .providers.base import DeliveryInfo
from .providers.gousto import GoustoProvider
from .providers.green_chef import GreenChefProvider

_LOGGER = logging.getLogger(__name__)


class FoodBoxCoordinator(DataUpdateCoordinator[DeliveryInfo]):
    def __init__(
        self,
        hass: HomeAssistant,
        provider_id: str,
        username: str,
        password: str,
    ) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=UPDATE_INTERVAL)
        session = async_get_clientsession(hass)
        if provider_id == PROVIDER_GOUSTO:
            self.provider = GoustoProvider(session, username, password)
        elif provider_id == PROVIDER_GREEN_CHEF:
            self.provider = GreenChefProvider(session, username, password)
        else:
            raise ValueError(f"Unknown provider: {provider_id}")

    async def _async_update_data(self) -> DeliveryInfo:
        try:
            result = await self.provider.get_delivery_info()
            async_dispatcher_send(self.hass, SIGNAL_COORDINATOR_UPDATED)
            return result
        except Exception as err:
            raise UpdateFailed(f"Error fetching {self.provider.name} delivery info: {err}") from err
