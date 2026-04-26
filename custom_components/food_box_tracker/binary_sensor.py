from __future__ import annotations

from datetime import date, timedelta

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PROVIDER, DOMAIN, PROVIDERS, SIGNAL_COORDINATOR_UPDATED
from .coordinator import FoodBoxCoordinator
from .providers.base import DeliveryInfo


def _all_coordinators(hass: HomeAssistant) -> list[FoodBoxCoordinator]:
    return [v for v in hass.data.get(DOMAIN, {}).values() if isinstance(v, FoodBoxCoordinator)]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: FoodBoxCoordinator = hass.data[DOMAIN][entry.entry_id]
    provider_name = PROVIDERS[entry.data[CONF_PROVIDER]]

    entities: list[BinarySensorEntity] = [
        DeliveryTodaySensor(coordinator, entry, provider_name),
        DeliveryTomorrowSensor(coordinator, entry, provider_name),
        RecipesNeedSelectingSensor(coordinator, entry, provider_name),
    ]

    # Combined binary sensors are created once for the whole domain.
    domain_data = hass.data[DOMAIN]
    if not domain_data.get("_combined_binary_added"):
        domain_data["_combined_binary_added"] = True
        entities += [
            AnyDeliveryTodaySensor(hass),
            AnyRecipesNeedSelectingSensor(hass),
        ]

    async_add_entities(entities)


# ---------------------------------------------------------------------------
# Per-account binary sensors
# ---------------------------------------------------------------------------

class _FoodBoxBinarySensorBase(CoordinatorEntity[FoodBoxCoordinator], BinarySensorEntity):
    def __init__(
        self,
        coordinator: FoodBoxCoordinator,
        entry: ConfigEntry,
        provider_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._provider_name = provider_name

    @property
    def device_info(self) -> dict:
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._provider_name,
            "manufacturer": self._provider_name,
        }

    @property
    def _data(self) -> DeliveryInfo | None:
        return self.coordinator.data


class DeliveryTodaySensor(_FoodBoxBinarySensorBase):
    _attr_icon = "mdi:truck-check"

    def __init__(self, coordinator, entry, provider_name):
        super().__init__(coordinator, entry, provider_name)
        self._attr_unique_id = f"{entry.entry_id}_delivery_today"
        self._attr_name = f"{provider_name} Delivery Today"

    @property
    def is_on(self) -> bool:
        if self._data and self._data.next_order and self._data.next_order.delivery_date:
            return self._data.next_order.delivery_date == date.today()
        return False


class DeliveryTomorrowSensor(_FoodBoxBinarySensorBase):
    _attr_icon = "mdi:truck-fast"

    def __init__(self, coordinator, entry, provider_name):
        super().__init__(coordinator, entry, provider_name)
        self._attr_unique_id = f"{entry.entry_id}_delivery_tomorrow"
        self._attr_name = f"{provider_name} Delivery Tomorrow"

    @property
    def is_on(self) -> bool:
        if self._data and self._data.next_order and self._data.next_order.delivery_date:
            return self._data.next_order.delivery_date == date.today() + timedelta(days=1)
        return False


class RecipesNeedSelectingSensor(_FoodBoxBinarySensorBase):
    _attr_icon = "mdi:silverware-fork-knife"

    def __init__(self, coordinator, entry, provider_name):
        super().__init__(coordinator, entry, provider_name)
        self._attr_unique_id = f"{entry.entry_id}_recipes_need_selecting"
        self._attr_name = f"{provider_name} Recipes Need Selecting"

    @property
    def is_on(self) -> bool:
        if self._data and self._data.next_order:
            return self._data.next_order.needs_recipe_selection
        return False


# ---------------------------------------------------------------------------
# Combined binary sensors (one instance across all configured accounts)
# ---------------------------------------------------------------------------

_COMBINED_DEVICE = {
    "identifiers": {(DOMAIN, "combined")},
    "name": "Food Box Tracker",
}


class _CombinedBinarySensorBase(BinarySensorEntity):
    _attr_should_poll = False
    _attr_device_info = _COMBINED_DEVICE

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_COORDINATOR_UPDATED,
                self._handle_coordinator_update,
            )
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class AnyDeliveryTodaySensor(_CombinedBinarySensorBase):
    _attr_unique_id = f"{DOMAIN}_combined_any_delivery_today"
    _attr_name = "Any Food Box Delivery Today"
    _attr_icon = "mdi:truck-check-outline"

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(hass)

    @property
    def is_on(self) -> bool:
        today = date.today()
        return any(
            c.data
            and c.data.next_order
            and c.data.next_order.delivery_date == today
            for c in _all_coordinators(self.hass)
        )


class AnyRecipesNeedSelectingSensor(_CombinedBinarySensorBase):
    _attr_unique_id = f"{DOMAIN}_combined_any_recipes_need_selecting"
    _attr_name = "Any Food Box Recipes Need Selecting"
    _attr_icon = "mdi:clipboard-list"

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(hass)

    @property
    def is_on(self) -> bool:
        return any(
            c.data and c.data.next_order and c.data.next_order.needs_recipe_selection
            for c in _all_coordinators(self.hass)
        )

    @property
    def extra_state_attributes(self) -> dict:
        providers = [
            c.data.provider_name
            for c in _all_coordinators(self.hass)
            if c.data and c.data.next_order and c.data.next_order.needs_recipe_selection
        ]
        return {"providers_pending": providers}
