from __future__ import annotations

import logging
from datetime import date
from typing import Any

from ..const import GREEN_CHEF_NEEDS_SELECTION_STATUSES
from .base import DeliveryInfo, FoodBoxProvider, OrderInfo

_LOGGER = logging.getLogger(__name__)

# Unofficial Green Chef (HelloFresh group) API — endpoints may change without notice
_AUTH_URL = "https://www.greenchef.co.uk/api/v2/customers/auth/login"
_DELIVERIES_URL = "https://www.greenchef.co.uk/api/v2/customers/me/subscriptions/upcoming"


class GreenChefProvider(FoodBoxProvider):
    def __init__(self, session, username: str | None = None, password: str | None = None, **kwargs) -> None:
        super().__init__(session, username, password, **kwargs)
        self._auth_token = kwargs.get("access_token")

    @property
    def name(self) -> str:
        return "Green Chef"

    async def authenticate(self) -> bool:
        payload = {"email": self._username, "password": self._password}
        async with self._session.post(_AUTH_URL, json=payload) as resp:
            if resp.status != 200:
                _LOGGER.debug("Green Chef auth failed: HTTP %s", resp.status)
                return False
            data: dict[str, Any] = await resp.json()
            self._auth_token = data.get("auth_token") or data.get("token")
            return bool(self._auth_token)

    async def _fetch_deliveries(self) -> list[dict[str, Any]]:
        headers = {"Authorization": f"Bearer {self._auth_token}"}

        async with self._session.get(_DELIVERIES_URL, headers=headers) as resp:
            if resp.status == 401:
                await self.authenticate()
                headers["Authorization"] = f"Bearer {self._auth_token}"
                async with self._session.get(_DELIVERIES_URL, headers=headers) as retry:
                    data = await retry.json()
            else:
                data = await resp.json()

        # API may return list directly or nested under a key
        if isinstance(data, list):
            return data
        return data.get("deliveries", data.get("upcoming_deliveries", []))

    async def get_delivery_info(self) -> DeliveryInfo:
        if not self._auth_token:
            await self.authenticate()

        raw_deliveries = await self._fetch_deliveries()
        today = date.today()
        upcoming: list[OrderInfo] = []

        for delivery in raw_deliveries:
            delivery_str: str = delivery.get("delivery_date", "")
            if not delivery_str:
                continue
            try:
                delivery_date = date.fromisoformat(delivery_str[:10])
            except ValueError:
                continue
            if delivery_date < today:
                continue

            meals = delivery.get("meals", delivery.get("recipes", []))
            recipe_names: list[str] = []
            if isinstance(meals, list):
                recipe_names = [
                    m.get("name", m.get("title", "")) for m in meals if isinstance(m, dict)
                ]
                meal_count = len(meals)
            else:
                meal_count = int(meals) if meals else None

            slot = delivery.get("delivery_slot") or delivery.get("time_slot")

            status = delivery.get("status", "unknown")
            upcoming.append(OrderInfo(
                delivery_date=delivery_date,
                order_status=status,
                recipe_count=meal_count,
                box_type=delivery.get("plan_name") or delivery.get("box_type"),
                recipes=recipe_names,
                delivery_slot=str(slot) if slot else None,
                order_number=str(delivery.get("id", "")),
                price=delivery.get("total_price") or delivery.get("price"),
                needs_recipe_selection=status in GREEN_CHEF_NEEDS_SELECTION_STATUSES,
            ))

        upcoming.sort(key=lambda o: o.delivery_date or date.max)
        return DeliveryInfo(
            provider_name=self.name,
            next_order=upcoming[0] if upcoming else None,
            upcoming_orders=upcoming,
        )
