"""Spider para TecnoStore (https://tecnostore.com.py/), rubro celulares.

El sitio corre sobre WooCommerce/WordPress (tema "Electro"), con URLs de
categoría del tipo /v2/index.php/product-category/celulares/.

Selectores CSS confirmados por exploración real del HTML (23 productos en
la página 1 de /v2/product-category/celulares/, sin ningún caso de oferta
con <del>/<ins> en esa muestra, pero soportado igual por robustez):

- Tarjeta de producto: li.product
- Link del producto: a.woocommerce-LoopProduct-link (atributo href)
- Título: h2.woocommerce-loop-product__title (dentro del link)
- Imagen: img dentro de div.product-thumbnail (atributo src, sin lazy-load)
- Precio (contenedor): span.price
  - Precio actual (sin oferta): span.woocommerce-Price-amount dentro de span.price
  - Precio original tachado (con oferta): <del> ... span.woocommerce-Price-amount
  - Precio final con oferta: <ins> ... span.woocommerce-Price-amount
- Paginación: nav.woocommerce-pagination, URLs tipo
  https://tecnostore.com.py/v2/product-category/celulares/page/2/

Formato de precio: símbolo "₲" en su propio span + número con COMAS de
miles (ej: "₲ 2,150,000"), a diferencia de Central Shop que usa puntos.
"""

from typing import List, Optional

import httpx
from bs4 import BeautifulSoup

from .base_spider import BaseSpider, ScrapedItem


class TecnoStoreSpider(BaseSpider):
    store_name = "TecnoStore"
    base_url = "https://tecnostore.com.py"

    async def search(self, query: str) -> List[ScrapedItem]:
        """Buscar productos por término usando el buscador nativo de WooCommerce."""
        url = f"{self.base_url}/v2/index.php?s={query}&post_type=product"
        items, _next_url = await self._scrape_page(url)
        return items

    async def fetch_category(self, category_url: str) -> List[ScrapedItem]:
        """Scraping de categoría de productos, siguiendo la paginación de WooCommerce.

        Acepta URLs como:
        - /v2/index.php/product-category/celulares/
        - https://tecnostore.com.py/v2/index.php/product-category/celulares/
        """
        if not category_url.startswith("http"):
            category_url = f"{self.base_url}{category_url}"

        items: List[ScrapedItem] = []
        seen_urls = set()

        next_url: Optional[str] = category_url
        # Límite defensivo de páginas para no quedar en loop infinito si el
        # sitio cambia su estructura de paginación.
        for _ in range(20):
            if not next_url:
                break

            page_items, next_url = await self._scrape_page(next_url)

            new_any = False
            for item in page_items:
                if item.product_url in seen_urls:
                    continue
                seen_urls.add(item.product_url)
                items.append(item)
                new_any = True

            # Si la página no aportó productos nuevos, evitar seguir
            # (protección extra contra loops de paginación mal formada).
            if not new_any:
                break

        return items

    async def _scrape_page(self, url: str):
        """Scraping de una sola página de listado. Devuelve (items, next_url)."""
        items: List[ScrapedItem] = []
        next_url: Optional[str] = None

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

                cards = soup.select("li.product")

                for card in cards:
                    try:
                        link = card.select_one("a.woocommerce-LoopProduct-link")
                        if not link:
                            continue

                        href = link.get("href")
                        if not href:
                            continue

                        title_elem = link.select_one("h2.woocommerce-loop-product__title")
                        title = title_elem.get_text(strip=True) if title_elem else ""
                        if not title:
                            continue

                        img = card.select_one("div.product-thumbnail img")
                        img_src = img.get("src") if img else None

                        price_container = card.select_one("span.price")
                        price = 0.0
                        original_price = None

                        if price_container:
                            del_elem = price_container.select_one("del")
                            ins_elem = price_container.select_one("ins")

                            if del_elem and ins_elem:
                                # Producto en oferta: <del> precio original,
                                # <ins> precio final con descuento.
                                original_price_val = _parse_guarani_price(
                                    del_elem.get_text(strip=True)
                                )
                                price = _parse_guarani_price(ins_elem.get_text(strip=True))
                                if original_price_val > 0:
                                    original_price = original_price_val
                            else:
                                # Sin oferta: un solo precio.
                                price = _parse_guarani_price(
                                    price_container.get_text(strip=True)
                                )

                        in_stock = "outofstock" not in (card.get("class") or [])

                        items.append(
                            ScrapedItem(
                                title=title,
                                price=price,
                                original_price=original_price,
                                product_url=href if href.startswith("http") else f"{self.base_url}{href}",
                                image_url=img_src,
                                in_stock=in_stock,
                            )
                        )
                    except Exception:
                        # Continuar si hay error en un elemento específico
                        continue

                # Buscar link "siguiente" de la paginación de WooCommerce
                next_link = soup.select_one("nav.woocommerce-pagination a.next.page-numbers")
                if next_link and next_link.get("href"):
                    next_url = next_link.get("href")

        except Exception:
            # Si hay error en la solicitud, retornar lo que se tenga (vacío en el peor caso)
            pass

        return items, next_url


def _parse_guarani_price(text: str) -> float:
    """Parsear precio en Guaraní de formatos como '₲ 2,150,000' o '2,150,000'.

    TecnoStore usa el símbolo "₲" en un span separado y COMAS como
    separador de miles (a diferencia de Central Shop, que usa puntos).
    """
    text = text.strip()

    # Remover símbolo de moneda y espacios/no-breaking-spaces
    text = text.replace("₲", "").replace("\xa0", " ").strip()

    if "," in text and "." in text:
        # Coma como separador de miles y punto como decimal (formato US): "1,234.56"
        text = text.replace(",", "")
    elif "," in text:
        # Solo comas: separador de miles paraguayo-en-inglés: "2,150,000"
        text = text.replace(",", "")
    elif "." in text:
        # Solo puntos: podría ser separador de miles (formato local) o decimal.
        # Si hay más de 2 dígitos después del último punto, es separador de miles.
        parts = text.split(".")
        if len(parts[-1]) == 2:
            # Decimal real, ej: "2150000.50" -> dejar el punto como decimal
            text = "".join(parts[:-1]) + "." + parts[-1]
        else:
            text = text.replace(".", "")

    # Extraer solo dígitos y punto decimal
    digits = "".join(ch for ch in text if ch.isdigit() or ch == ".")
    return float(digits) if digits else 0.0
