from __future__ import annotations

import logging
from datetime import date
from typing import Any

from ..const import GOUSTO_NEEDS_SELECTION_STATUSES
from .base import DeliveryInfo, FoodBoxProvider, OrderInfo

_LOGGER = logging.getLogger(__name__)

# Unofficial Gousto API — endpoints may change without notice
_AUTH_URL = "https://www.gousto.co.uk/login"
_ORDERS_URL = "https://production-api.gousto.co.uk/user/current/orders"


class GoustoProvider(FoodBoxProvider):
    _access_token: str | None = None

    @property
    def name(self) -> str:
        return "Gousto"

    async def authenticate(self) -> bool:
        payload = {
            "grant_type": "password",
            "username": self._username,
            "password": self._password,
            "rememberMe": "true",
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
        }
        async with self._session.post(_AUTH_URL, data=payload, headers=headers) as resp:
            if resp.status != 200:
                _LOGGER.debug("Gousto auth failed: HTTP %s", resp.status)
                return False
            data: dict[str, Any] = await resp.json()
            self._access_token = data.get("access_token")
            return bool(self._access_token)

    async def _fetch_orders(self) -> list[dict[str, Any]]:
        headers = {"Authorization": f"Bearer {self._access_token}"}
        params = {"limit": 10, "sort_order": "desc", "state": "pending"}

        async with self._session.get(_ORDERS_URL, headers=headers, params=params) as resp:
            if resp.status == 401:
                await self.authenticate()
                headers["Authorization"] = f"Bearer {self._access_token}"
                async with self._session.get(_ORDERS_URL, headers=headers, params=params) as retry:
                    data = await retry.json()
            else:
                data = await resp.json()

        return data.get("result", {}).get("data", [])

    async def get_delivery_info(self) -> DeliveryInfo:
        if not self._access_token:
            await self.authenticate()

        raw_orders = await self._fetch_orders()
        today = date.today()
        upcoming: list[OrderInfo] = []

        for order in raw_orders:
            delivery_str: str = order.get("delivery_date", "")
            if not delivery_str:
                continue
            try:
                delivery_date = date.fromisoformat(delivery_str[:10])
            except ValueError:
                continue
            if delivery_date < today:
                continue

            recipes = order.get("recipe_items", [])
            recipe_names = [r.get("title", "") for r in recipes if isinstance(r, dict)]
            box = order.get("box", {})
            slot = order.get("delivery_slot", {})
            slot_str = None
            if isinstance(slot, dict):
                slot_str = f"{slot.get('delivery_start', '')} – {slot.get('delivery_end', '')}".strip(" –") or None

            status = order.get("state", "unknown")
            upcoming.append(OrderInfo(
                delivery_date=delivery_date,
                order_status=status,
                recipe_count=len(recipes),
                box_type=box.get("box_type") if isinstance(box, dict) else None,
                recipes=recipe_names,
                delivery_slot=slot_str,
                order_number=str(order.get("id", "")),
                price=order.get("prices", {}).get("total"),
                needs_recipe_selection=status in GOUSTO_NEEDS_SELECTION_STATUSES,
            ))

        upcoming.sort(key=lambda o: o.delivery_date or date.max)
        return DeliveryInfo(
            provider_name=self.name,
            next_order=upcoming[0] if upcoming else None,
            upcoming_orders=upcoming,
        )
