"""Spider para Tienda Móvil (https://tiendamovil.com.py/).

Selectores CSS confirmados por exploración real de
https://tiendamovil.com.py/shop/celulares/ (sitio basado en PrestaShop):

- Contenedor del listado principal: div#js-product-list
  (hay además carruseles "Lo último de..." con tarjetas casi idénticas;
  por eso se busca explícitamente dentro de #js-product-list y no en todo
  el documento).
- Tarjeta de producto: article.product-miniature
- Link + título: h2.product-title > a (texto y href)
- Imagen: img.product-thumbnail-first dentro de a.product-thumbnail.
  El sitio usa lazy-loading: el atributo "src" es un SVG placeholder en
  base64, la URL real está en el atributo "data-src".
- Precio actual: span.product-price, atributo "content" (ej: "17750000",
  ya numérico, sin puntos ni símbolo — más confiable que el texto visible
  "17.750.000 ₲").
- Precio original/tachado (si hay descuento): span.regular-price (texto,
  ej: "21.385.542 ₲"). No todos los productos lo tienen.
- Disponibilidad: span con clase "product-available" (en stock) o
  "product-unavailable" (sin stock), dentro de div.product-availability.
- Paginación: enlaces ?page=N, hasta 9 páginas en /shop/celulares/.

Nota sobre bloqueo: una prueba previa con un fetcher distinto (no httpx)
dio 403 al forzar https. Con httpx real + headers de navegador completos
(User-Agent, Accept, Accept-Language, Referer) el sitio respondió 200 sin
problema — no hay bloqueo real ni challenge de Cloudflare.
"""

from typing import List, Optional

import httpx
from bs4 import BeautifulSoup

from .base_spider import BaseSpider, ScrapedItem

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "es-PY,es;q=0.9,en;q=0.8",
    "Referer": "https://www.google.com/",
}


class TiendaMovilSpider(BaseSpider):
    store_name = "Tienda Móvil"
    base_url = "https://tiendamovil.com.py"

    async def search(self, query: str) -> List[ScrapedItem]:
        """Buscar productos por término usando el buscador del sitio."""
        url = f"{self.base_url}/shop/busqueda?controller=search&s={query}"
        return await self._scrape_listing(url)

    async def fetch_category(self, category_url: str, max_pages: int = 9) -> List[ScrapedItem]:
        """Scraping de categoría de productos, siguiendo paginación ?page=N.

        Acepta URLs como:
        - /shop/celulares/
        - https://tiendamovil.com.py/shop/celulares/
        """
        if not category_url.startswith("http"):
            category_url = f"{self.base_url}{category_url}"

        # Normalizar: quitar querystring de página si vino incluida
        base = category_url.split("?")[0]

        items: List[ScrapedItem] = []
        for page in range(1, max_pages + 1):
            page_url = base if page == 1 else f"{base}?page={page}"
            page_items = await self._scrape_listing(page_url)
            if not page_items:
                break
            items.extend(page_items)

        return items

    async def _scrape_listing(self, url: str) -> List[ScrapedItem]:
        """Scraping de una página de listado usando httpx + BeautifulSoup."""
        items: List[ScrapedItem] = []

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=_HEADERS, follow_redirects=True)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")

                # Restringir al listado principal para no capturar los
                # carruseles de "Lo último de..." que tienen tarjetas
                # con la misma clase product-miniature.
                container = soup.find("div", id="js-product-list") or soup

                cards = container.find_all("article", class_="product-miniature")

                for card in cards:
                    try:
                        title_link = card.select_one("h2.product-title a")
                        if not title_link:
                            continue

                        title = title_link.get_text(strip=True)
                        href = title_link.get("href")
                        if not title or not href:
                            continue

                        # Imagen: el sitio usa lazy-loading, la URL real
                        # está en data-src (src es un placeholder SVG).
                        img = card.select_one("a.product-thumbnail img")
                        image_url = None
                        if img:
                            image_url = img.get("data-src") or img.get("src")
                            if image_url and image_url.startswith("data:"):
                                image_url = None

                        # Precio actual: usar el atributo "content", ya
                        # numérico y sin formateo (ej: "17750000").
                        price_elem = card.select_one("span.product-price")
                        price = 0.0
                        if price_elem:
                            content_attr = price_elem.get("content")
                            if content_attr:
                                price = _parse_guarani_price(content_attr)
                            else:
                                price = _parse_guarani_price(price_elem.get_text(strip=True))

                        # Precio original (tachado), si hay descuento
                        original_price = None
                        old_price_elem = card.select_one("span.regular-price")
                        if old_price_elem:
                            parsed_old_price = _parse_guarani_price(old_price_elem.get_text(strip=True))
                            if parsed_old_price > 0:
                                original_price = parsed_old_price

                        # Disponibilidad
                        unavailable_elem = card.select_one("span.product-unavailable")
                        in_stock = unavailable_elem is None

                        items.append(
                            ScrapedItem(
                                title=title,
                                price=price,
                                original_price=original_price,
                                product_url=href if href.startswith("http") else f"{self.base_url}{href}",
                                image_url=image_url,
                                in_stock=in_stock,
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
    """Parsear precio en Guaraní.

    Soporta:
    - Atributo "content" ya numérico: "17750000"
    - Texto visible con puntos de mil y símbolo: "17.750.000 ₲"
    """
    if not text:
        return 0.0

    text = text.strip()

    # Quedarnos solo con dígitos, puntos y comas (quitar "₲", espacios, etc.)
    cleaned = "".join(ch for ch in text if ch.isdigit() or ch in ".,")
    if not cleaned:
        return 0.0

    if "," in cleaned:
        # Formato con coma decimal: quitar puntos de mil, coma -> punto
        cleaned = cleaned.replace(".", "").replace(",", ".")
    else:
        # Solo dígitos y puntos: si el atributo "content" ya viene limpio
        # (ej. "17750000") esto no tiene puntos y queda igual. Si viene
        # con puntos de mil (ej. "17.750.000") se remueven.
        cleaned = cleaned.replace(".", "")

    try:
        return float(cleaned)
    except ValueError:
        return 0.0
