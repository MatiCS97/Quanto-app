from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ScrapedItem:
    title: str
    price: float
    original_price: float | None
    product_url: str
    image_url: str | None
    in_stock: bool


class BaseSpider(ABC):
    """Contrato que cada spider de tienda debe implementar.

    Un spider por tienda, no un spider genérico configurable: cada
    e-commerce cambia su HTML de forma independiente y un spider dedicado
    es más fácil de arreglar cuando se rompe (ver riesgo de mantenimiento
    en el plan de producto).
    """

    store_name: str

    @abstractmethod
    async def search(self, query: str) -> list[ScrapedItem]:
        ...

    @abstractmethod
    async def fetch_category(self, category_url: str) -> list[ScrapedItem]:
        ...
