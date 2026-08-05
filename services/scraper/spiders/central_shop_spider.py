"""Spider para Central Shop (https://www.centralshop.com.py/).

Selectores CSS confirmados por exploración real:
- Tarjeta de producto: div.pc.card
- Link y contenedor de info: a.pc-link
- Marca: div.pc-brand (dentro del link)
- Título: div.pc-name (dentro del link)
- Imagen: img.card-img-top (dentro del link)
- Footer con precios: div.pc-footer
- Precio actual: span.pc-price
- Precio original: span.pc-old-price

Formato de precio: números con punto de mil, sin "Gs." (ej: "240.000", "1.000.000")
"""

from typing import List

import httpx
from bs4 import BeautifulSoup

from .base_spider import BaseSpider, ScrapedItem


class CentralShopSpider(BaseSpider):
    store_name = "Central Shop"
    base_url = "https://www.centralshop.com.py"

    async def search(self, query: str) -> List[ScrapedItem]:
        """Buscar productos por término.

        Central Shop utiliza parámetros de búsqueda en /productos?q=...
        """
        # Usar la URL de búsqueda del sitio
        url = f"{self.base_url}/productos?q={query}&pagina=1"
        return await self._scrape_listing(url)

    async def fetch_category(self, category_url: str) -> List[ScrapedItem]:
        """Scraping de categoría de productos.

        Acepta URLs como:
        - /productos?categoria=celulares-y-smartwatches&pagina=1
        - https://www.centralshop.com.py/productos?categoria=...
        """
        if not category_url.startswith("http"):
            category_url = f"{self.base_url}{category_url}"
        return await self._scrape_listing(category_url)

    async def _scrape_listing(self, url: str) -> List[ScrapedItem]:
        """Scraping de página de listado de productos usando httpx + BeautifulSoup."""
        items: List[ScrapedItem] = []

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                headers = {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                }
                response = await client.get(url, headers=headers, follow_redirects=True)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")

                # Obtener todas las tarjetas de producto
                cards = soup.find_all("div", class_=lambda x: x and "pc" in x and "card" in x)

                for card in cards:
                    try:
                        # Extraer link y contenedor de información
                        link = card.find("a", class_="pc-link")
                        if not link:
                            continue

                        href = link.get("href")
                        if not href:
                            continue

                        # Extraer marca
                        brand_elem = link.find("div", class_="pc-brand")
                        brand = brand_elem.get_text(strip=True) if brand_elem else ""

                        # Extraer nombre/título
                        name_elem = link.find("div", class_="pc-name")
                        name = name_elem.get_text(strip=True) if name_elem else ""

                        # Combinar marca y nombre
                        title = f"{brand} {name}" if brand else name
                        if not title:
                            continue

                        # Extraer imagen
                        img = link.find("img", class_="card-img-top")
                        img_src = img.get("src") if img else None

                        # Extraer precios
                        footer = card.find("div", class_="pc-footer")
                        price = 0.0
                        original_price = None

                        if footer:
                            # Precio actual
                            price_elem = footer.find("span", class_="pc-price")
                            if price_elem:
                                price_text = price_elem.get_text(strip=True)
                                price = _parse_guarani_price(price_text)

                            # Precio original (si existe)
                            old_price_elem = footer.find("span", class_="pc-old-price")
                            if old_price_elem:
                                old_price_text = old_price_elem.get_text(strip=True)
                                parsed_old_price = _parse_guarani_price(old_price_text)
                                if parsed_old_price > 0:
                                    original_price = parsed_old_price

                        # Crear item
                        items.append(
                            ScrapedItem(
                                title=title,
                                price=price,
                                original_price=original_price,
                                product_url=href if href.startswith("http") else f"{self.base_url}{href}",
                                image_url=img_src,
                                in_stock=True,
                            )
                        )
                    except Exception:
                        # Continuar si hay error en un elemento específico
                        continue

        except Exception:
            # Si hay error en la solicitud, retornar lista vacía
            pass

        return items


def _parse_guarani_price(text: str) -> float:
    """Parsear precio en Guaraní de formatos como '240.000' o '1.000.000'.

    Central Shop no incluye prefijo "Gs.", solo números con punto de mil.
    """
    # Remover espacios
    text = text.strip()

    # Remover puntos de separación de miles (formato paraguayo: 1.000.000)
    # Pero mantener si hay coma decimal
    if "," in text:
        # Formato con coma decimal: remover puntos, reemplazar coma por punto
        text = text.replace(".", "").replace(",", ".")
    else:
        # Formato sin decimal: remover puntos
        text = text.replace(".", "")

    # Extraer solo dígitos y punto decimal
    digits = "".join(ch for ch in text if ch.isdigit() or ch == ".")
    return float(digits) if digits else 0.0
