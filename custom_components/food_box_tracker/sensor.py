from __future__ import annotations

from datetime import date

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PROVIDER, DOMAIN, PROVIDERS
from .coordinator import FoodBoxCoordinator
from .providers.base import DeliveryInfo


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: FoodBoxCoordinator = hass.data[DOMAIN][entry.entry_id]
    provider_name = PROVIDERS[entry.data[CONF_PROVIDER]]

    async_add_entities(
        [
            NextDeliveryDateSensor(coordinator, entry, provider_name),
            OrderStatusSensor(coordinator, entry, provider_name),
            RecipeCountSensor(coordinator, entry, provider_name),
            DeliverySlotSensor(coordinator, entry, provider_name),
            BoxTypeSensor(coordinator, entry, provider_name),
        ]
    )


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
