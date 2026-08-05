"""Spider para Alemania Cell (https://www.alemaniacell.com/).

Selectores CSS confirmados por exploración real (rubro celulares):
- Contenedor de listado: div#catalogoProductos
- Tarjeta de producto: div.it (dentro del contenedor; siempre observado con
  clase adicional "rebajado" cuando hay precio anterior tachado)
- Link + imagen del producto: a.img (dentro de div.cnt) -> atributo href
- Imagen: img (dentro de a.img) -> atributo src (viene sin protocolo, "//...")
- Título: a.tit h2 (dentro de div.info)
- Precio actual: strong.precio.venta span.monto
- Precio original/tachado: del.precio.lista span.monto (puede no existir)
- Stock: viene en un input.json oculto con un blob JSON escapado en HTML
  (clave "tieneStock": true/false dentro de "variante")

Formato de precio: números con punto de mil, sin decimales, sin prefijo
"Gs." en el texto (el prefijo "PYG" está en un <span class="sim"> separado),
ej: "4.650.000", "2.850.000".

Listado: https://www.alemaniacell.com/celulares (12 items por página, sin
paginación por query param detectable en el HTML estático — el resto se
carga vía JS/AJAX, fuera de alcance de este spider basado en httpx).

Búsqueda: el formulario del sitio apunta a GET /catalogo?q=<término> y
reutiliza exactamente la misma estructura de tarjetas que el listado de
categoría, confirmado navegando /catalogo?q=iphone.
"""

import json
import re
from typing import List, Optional

import httpx
from bs4 import BeautifulSoup

from .base_spider import BaseSpider, ScrapedItem


class AlemaniaCellSpider(BaseSpider):
    store_name = "Alemania Cell"
    base_url = "https://www.alemaniacell.com"

    async def search(self, query: str) -> List[ScrapedItem]:
        """Buscar productos por término.

        Alemania Cell usa el mismo formulario de búsqueda global del sitio,
        GET /catalogo?q=<término>, que devuelve tarjetas con la misma
        estructura que las categorías.
        """
        url = f"{self.base_url}/catalogo?q={query}"
        return await self._scrape_listing(url)

    async def fetch_category(self, category_url: str) -> List[ScrapedItem]:
        """Scraping de categoría de productos.

        Acepta URLs como:
        - /celulares
        - /celulares?marca=samsung
        - https://www.alemaniacell.com/celulares
        """
        if not category_url.startswith("http"):
            if not category_url.startswith("/"):
                category_url = f"/{category_url}"
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

                container = soup.find("div", id="catalogoProductos")
                if not container:
                    return items

                cards = container.find_all(
                    "div", class_=lambda x: x and "it" in x.split()
                )

                for card in cards:
                    try:
                        cnt = card.find("div", class_="cnt")
                        if not cnt:
                            continue

                        link = cnt.find("a", class_="img")
                        if not link:
                            continue

                        href = link.get("href")
                        if not href:
                            continue

                        # Título
                        info = card.find("div", class_="info")
                        title = ""
                        if info:
                            tit_elem = info.find("a", class_="tit")
                            if tit_elem:
                                h2 = tit_elem.find("h2")
                                title = h2.get_text(strip=True) if h2 else tit_elem.get_text(strip=True)
                        if not title:
                            continue

                        # Imagen (puede venir sin protocolo: "//f.fcdn.app/...")
                        img = link.find("img")
                        img_src = img.get("src") if img else None
                        if img_src and img_src.startswith("//"):
                            img_src = f"https:{img_src}"

                        # Precios
                        price = 0.0
                        original_price = None
                        precios = card.find("div", class_="precios")
                        if precios:
                            price_elem = precios.find("strong", class_="precio")
                            if price_elem:
                                monto = price_elem.find("span", class_="monto")
                                if monto:
                                    price = _parse_guarani_price(monto.get_text(strip=True))

                            old_price_elem = precios.find("del", class_="precio")
                            if old_price_elem:
                                old_monto = old_price_elem.find("span", class_="monto")
                                if old_monto:
                                    parsed_old = _parse_guarani_price(old_monto.get_text(strip=True))
                                    if parsed_old > 0:
                                        original_price = parsed_old

                        # Stock: viene en un input oculto con JSON escapado por HTML
                        in_stock = True
                        json_input = card.find("input", class_="json")
                        if json_input and json_input.get("value"):
                            try:
                                data = json.loads(json_input["value"])
                                in_stock = bool(
                                    data.get("variante", {}).get("tieneStock", True)
                                )
                            except (ValueError, TypeError):
                                pass

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

        except Exception:
            # Si hay error en la solicitud, retornar lista vacía
            pass

        return items


def _parse_guarani_price(text: str) -> float:
    """Parsear precio en Guaraní de formatos como '4.650.000' o '2.850.000'.

    Alemania Cell no incluye prefijo "Gs." en el texto del monto (el
    prefijo "PYG" vive en un <span class="sim"> separado), solo números
    con punto de mil y sin decimales. Se maneja también el caso con coma
    decimal por robustez, igual que otros spiders del proyecto.
    """
    text = text.strip()

    if not text:
        return 0.0

    # Formato con coma decimal: remover puntos de mil, coma -> punto decimal
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        # Formato sin decimal: remover puntos de separación de miles
        text = text.replace(".", "")

    digits = "".join(ch for ch in text if ch.isdigit() or ch == ".")
    return float(digits) if digits else 0.0
