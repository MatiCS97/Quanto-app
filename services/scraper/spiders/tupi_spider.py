"""Spider para Tupi (https://www.tupi.com.py/).

httpx simple + BeautifulSoup: la home y las páginas de categoría de
tupi.com.py responden 200 con headers de navegador normales (no hay
challenge de Cloudflare real, un fetcher previo sin headers dio 403 pero
un GET con User-Agent/Accept/Accept-Language/Referer normales ya funciona).

Detalle clave: la página de categoría (ej. /lineas/151/Celulares/) trae el
HTML "cascarón" pero el grid de productos (<ul class="products columns-3">)
llega vacío — los productos se cargan vía un endpoint AJAX aparte:

    https://www.tupi.com.py/buscar_paginacion.php?id=<categoria_id>&linea=<categoria_id>&page=<n>&tamano=<tamanio>

Ese endpoint (usado por el propio JS del sitio, visible como link oculto
"Siguiente página" en el HTML de la categoría) devuelve directamente el
fragmento HTML con las tarjetas de producto y es el que este spider
consume.

Selectores CSS confirmados por exploración real (sobre el fragmento AJAX):
- Tarjeta de producto: div.product_unit
- Link + título: span.loop-product-categories.nombre_producto_ug > a[rel="tag"]
  (el texto incluye " ver detalles" en un <span class="prod_verdetalleslink"> que se descarta)
- Imagen: div.thumbnail img (atributo src)
- Precio actual y original: dentro de div.price-add-to-cart, en
  a.single_add_to_cart_button. El texto de ese <a> es:
    - sin descuento:  "Gs. 7.950.000"                          (precio actual)
    - con descuento:  "Gs. 5.499.000" (dentro de span.precio_tachado) + "Gs. 5.459.000"
      -> el contenido de span.precio_tachado es el precio ORIGINAL (tachado),
         el texto que queda después de sacar ese span es el precio ACTUAL.
- Estado de stock: span.badge.badge-success con texto "En Stock" indica
  disponible; cualquier otro texto (p.ej. "Sin Stock") se trata como no
  disponible.

Formato de precio: "Gs. 1.234.000" (punto de mil, sin decimales).
"""

import re
from typing import List, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from .base_spider import BaseSpider, ScrapedItem

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-PY,es;q=0.9,en;q=0.8",
}

# ID de línea/categoría "Celulares" (verificado real en tupi.com.py al momento
# de escribir este spider). Si el sitio reorganiza categorías, este id puede
# cambiar y hay que volver a inspeccionar /lineas/<id>/Celulares/.
_CELULARES_LINEA_ID = "151"

_PAGE_SIZE = 60


class TupiSpider(BaseSpider):
    store_name = "Tupi"
    base_url = "https://www.tupi.com.py"

    async def search(self, query: str) -> List[ScrapedItem]:
        """Buscar productos por término.

        Tupi no expone una API de búsqueda estable identificada; como
        fallback se recorre la categoría de Celulares completa (igual que
        hace mega_electronicos_spider) y no se filtra por texto acá.
        """
        return await self.fetch_category(f"/lineas/{_CELULARES_LINEA_ID}/Celulares/")

    async def fetch_category(self, category_url: str) -> List[ScrapedItem]:
        """Scraping de categoría de productos.

        Acepta URLs como:
        - /lineas/151/Celulares/
        - https://www.tupi.com.py/lineas/151/Celulares/
        """
        if not category_url.startswith("http"):
            category_url = f"{self.base_url}{category_url}"

        linea_id = _extract_linea_id(category_url) or _CELULARES_LINEA_ID

        items: List[ScrapedItem] = []
        async with httpx.AsyncClient(timeout=30, headers=_BROWSER_HEADERS) as client:
            # Referer real de la categoría, requerido por algunos sitios para
            # aceptar el pedido AJAX como "legítimo".
            headers = {"Referer": category_url, "X-Requested-With": "XMLHttpRequest"}

            page = 1
            while True:
                ajax_url = (
                    f"{self.base_url}/buscar_paginacion.php"
                    f"?id={linea_id}&linea={linea_id}&page={page}&tamano={_PAGE_SIZE}"
                )
                try:
                    response = await client.get(ajax_url, headers=headers, follow_redirects=True)
                    response.raise_for_status()
                except Exception:
                    break

                page_items = _parse_products(response.text, self.base_url)
                if not page_items:
                    break

                items.extend(page_items)

                # Si la página trajo menos que el tamaño pedido, no hay más.
                if len(page_items) < _PAGE_SIZE:
                    break
                page += 1

                # Salvaguarda para no loopear infinito si el sitio cambia de comportamiento.
                if page > 20:
                    break

        return items


def _extract_linea_id(category_url: str) -> Optional[str]:
    """Extrae el id numérico de una URL tipo /lineas/151/Celulares/."""
    match = re.search(r"/lineas/(\d+)/", category_url)
    return match.group(1) if match else None


def _parse_products(html: str, base_url: str) -> List[ScrapedItem]:
    items: List[ScrapedItem] = []
    soup = BeautifulSoup(html, "html.parser")

    cards = soup.find_all("div", class_="product_unit")

    for card in cards:
        try:
            # --- Título y link ---
            name_span = card.find("span", class_="nombre_producto_ug")
            if not name_span:
                continue
            title_link = name_span.find("a", rel="tag")
            if not title_link:
                continue

            href = title_link.get("href")
            if not href:
                continue

            # Sacar el sub-span "ver detalles" antes de tomar el texto.
            detalles_span = title_link.find("span", class_="prod_verdetalleslink")
            if detalles_span:
                detalles_span.extract()
            title = title_link.get_text(strip=True)
            if not title:
                continue

            # --- Imagen ---
            thumbnail = card.find("div", class_="thumbnail")
            img_src = None
            if thumbnail:
                img = thumbnail.find("img")
                if img:
                    img_src = img.get("src")

            # --- Precio ---
            price_container = card.find("div", class_="price-add-to-cart")
            price = 0.0
            original_price = None
            if price_container:
                price_link = price_container.find("a", class_="single_add_to_cart_button")
                if price_link:
                    tachado = price_link.find("span", class_="precio_tachado")
                    tachado_text = tachado.get_text(strip=True) if tachado else ""
                    if tachado:
                        tachado.extract()
                    current_text = price_link.get_text(strip=True)

                    price = _parse_guarani_price(current_text)
                    if tachado_text:
                        parsed_original = _parse_guarani_price(tachado_text)
                        if parsed_original > 0:
                            original_price = parsed_original

            if price <= 0:
                continue

            # --- Stock ---
            stock_badge = card.find("span", class_="badge-success")
            in_stock = bool(stock_badge and "stock" in stock_badge.get_text(strip=True).lower())

            items.append(
                ScrapedItem(
                    title=title,
                    price=price,
                    original_price=original_price,
                    product_url=href if href.startswith("http") else urljoin(base_url, href),
                    image_url=img_src,
                    in_stock=in_stock,
                )
            )
        except Exception:
            continue

    return items


def _parse_guarani_price(text: str) -> float:
    """Parsear precio en Guaraní de formatos como 'Gs. 1.234.000'."""
    text = text.replace("Gs.", "").replace("Gs", "").strip()

    if "," in text:
        # Formato con coma decimal: remover puntos, reemplazar coma por punto.
        text = text.replace(".", "").replace(",", ".")
    else:
        # Formato sin decimal: remover puntos de separación de miles.
        text = text.replace(".", "")

    digits = "".join(ch for ch in text if ch.isdigit() or ch == ".")
    return float(digits) if digits else 0.0
