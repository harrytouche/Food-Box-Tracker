from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class OrderInfo:
    """Represents a single upcoming order."""
    delivery_date: Optional[date]
    order_status: str
    recipe_count: Optional[int]
    box_type: Optional[str]
    recipes: list[str] = field(default_factory=list)
    # Extended fields populated once providers expose them
    delivery_slot: Optional[str] = None
    order_number: Optional[str] = None
    price: Optional[float] = None
    needs_recipe_selection: bool = False


@dataclass
class DeliveryInfo:
    """Aggregated delivery data returned by a provider."""
    provider_name: str
    next_order: Optional[OrderInfo]
    upcoming_orders: list[OrderInfo] = field(default_factory=list)


class FoodBoxProvider(ABC):
    def __init__(self, session, username: str | None = None, password: str | None = None, **kwargs) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._extra_config = kwargs

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the provider. Returns True on success."""

    @abstractmethod
    async def get_delivery_info(self) -> DeliveryInfo:
        """Return upcoming delivery information."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""
