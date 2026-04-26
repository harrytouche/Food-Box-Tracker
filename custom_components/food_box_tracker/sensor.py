from __future__ import annotations

from datetime import date

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
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

    entities: list[SensorEntity] = [
        NextDeliveryDateSensor(coordinator, entry, provider_name),
        OrderStatusSensor(coordinator, entry, provider_name),
        RecipeCountSensor(coordinator, entry, provider_name),
        DeliverySlotSensor(coordinator, entry, provider_name),
        BoxTypeSensor(coordinator, entry, provider_name),
    ]

    # Combined sensors are created once for the whole domain, not per-entry.
    domain_data = hass.data[DOMAIN]
    if not domain_data.get("_combined_sensors_added"):
        domain_data["_combined_sensors_added"] = True
        entities += [
            CombinedNextDeliverySensor(hass),
            CombinedNextDeliveryProviderSensor(hass),
        ]

    async_add_entities(entities)


# ---------------------------------------------------------------------------
# Per-account sensors
# ---------------------------------------------------------------------------

class _FoodBoxSensorBase(CoordinatorEntity[FoodBoxCoordinator], SensorEntity):
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


class NextDeliveryDateSensor(_FoodBoxSensorBase):
    _attr_device_class = SensorDeviceClass.DATE
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator, entry, provider_name):
        super().__init__(coordinator, entry, provider_name)
        self._attr_unique_id = f"{entry.entry_id}_next_delivery_date"
        self._attr_name = f"{provider_name} Next Delivery Date"

    @property
    def native_value(self) -> date | None:
        if self._data and self._data.next_order:
            return self._data.next_order.delivery_date
        return None


class OrderStatusSensor(_FoodBoxSensorBase):
    _attr_icon = "mdi:package-variant-closed"

    def __init__(self, coordinator, entry, provider_name):
        super().__init__(coordinator, entry, provider_name)
        self._attr_unique_id = f"{entry.entry_id}_order_status"
        self._attr_name = f"{provider_name} Order Status"

    @property
    def native_value(self) -> str | None:
        if self._data and self._data.next_order:
            return self._data.next_order.order_status
        return None

    @property
    def extra_state_attributes(self) -> dict:
        if self._data and self._data.next_order:
            return {
                "order_number": self._data.next_order.order_number,
                "price": self._data.next_order.price,
                "upcoming_delivery_count": len(self._data.upcoming_orders),
            }
        return {}


class RecipeCountSensor(_FoodBoxSensorBase):
    _attr_icon = "mdi:food-variant"
    _attr_native_unit_of_measurement = "recipes"

    def __init__(self, coordinator, entry, provider_name):
        super().__init__(coordinator, entry, provider_name)
        self._attr_unique_id = f"{entry.entry_id}_recipe_count"
        self._attr_name = f"{provider_name} Recipe Count"

    @property
    def native_value(self) -> int | None:
        if self._data and self._data.next_order:
            return self._data.next_order.recipe_count
        return None

    @property
    def extra_state_attributes(self) -> dict:
        if self._data and self._data.next_order:
            return {"recipes": self._data.next_order.recipes}
        return {}


class DeliverySlotSensor(_FoodBoxSensorBase):
    _attr_icon = "mdi:clock-delivery"

    def __init__(self, coordinator, entry, provider_name):
        super().__init__(coordinator, entry, provider_name)
        self._attr_unique_id = f"{entry.entry_id}_delivery_slot"
        self._attr_name = f"{provider_name} Delivery Slot"

    @property
    def native_value(self) -> str | None:
        if self._data and self._data.next_order:
            return self._data.next_order.delivery_slot
        return None


class BoxTypeSensor(_FoodBoxSensorBase):
    _attr_icon = "mdi:package-variant"

    def __init__(self, coordinator, entry, provider_name):
        super().__init__(coordinator, entry, provider_name)
        self._attr_unique_id = f"{entry.entry_id}_box_type"
        self._attr_name = f"{provider_name} Box Type"

    @property
    def native_value(self) -> str | None:
        if self._data and self._data.next_order:
            return self._data.next_order.box_type
        return None


# ---------------------------------------------------------------------------
# Combined sensors (one instance across all configured accounts)
# ---------------------------------------------------------------------------

_COMBINED_DEVICE = {
    "identifiers": {(DOMAIN, "combined")},
    "name": "Food Box Tracker",
}


class _CombinedSensorBase(SensorEntity):
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


class CombinedNextDeliverySensor(_CombinedSensorBase):
    _attr_unique_id = f"{DOMAIN}_combined_next_delivery_date"
    _attr_name = "Next Food Box Delivery"
    _attr_device_class = SensorDeviceClass.DATE
    _attr_icon = "mdi:calendar-star"

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(hass)

    @property
    def native_value(self) -> date | None:
        dates = [
            c.data.next_order.delivery_date
            for c in _all_coordinators(self.hass)
            if c.data and c.data.next_order and c.data.next_order.delivery_date
        ]
        return min(dates) if dates else None


class CombinedNextDeliveryProviderSensor(_CombinedSensorBase):
    _attr_unique_id = f"{DOMAIN}_combined_next_delivery_provider"
    _attr_name = "Next Food Box Provider"
    _attr_icon = "mdi:truck-delivery"

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(hass)

    @property
    def native_value(self) -> str | None:
        candidates = [
            (c.data.next_order.delivery_date, c.data.provider_name)
            for c in _all_coordinators(self.hass)
            if c.data and c.data.next_order and c.data.next_order.delivery_date
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda t: t[0])[1]
