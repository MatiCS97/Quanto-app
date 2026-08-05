from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ScrapedItem:
    title: str
    price: float
    original_price: Optional[float]
    product_url: str
    image_url: Optional[str]
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
    async def search(self, query: str) -> List[ScrapedItem]:
        ...

    @abstractmethod
    async def fetch_category(self, category_url: str) -> List[ScrapedItem]:
        ...
