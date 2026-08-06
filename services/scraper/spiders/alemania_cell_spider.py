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

Listado: https://www.alemaniacell.com/celulares (12 items por página).

Paginación (corrección a la nota anterior de este docstring — se dejó la
nota original más abajo, tachada en texto, porque documenta un hallazgo
real útil): SÍ existe una forma de paginar sin JS/navegador. La página de
categoría en frío ("GET /celulares" sin parámetros) solo trae la primera
tanda de 12 productos y un `<div class="pagination"></div>` VACÍO —, eso
sigue siendo cierto y fue lo que llevó a la conclusión original de "no hay
paginación detectable". Pero el sitio usa scroll infinito: al hacer scroll,
el JS del cliente pide `GET /celulares?js=1&pag=N` (N=2,3,4,...), que es
un GET plano, sin headers especiales ni token de sesión, confirmado con
Playwright interceptando tráfico de red y luego reproducido igual con
httpx puro (sin ejecutar JS). Ese endpoint devuelve un fragmento HTML que
incluye el mismo `<div id="catalogoProductos">` y las mismas tarjetas
`div.it` que la página completa, así que se reutiliza el mismo parser.
Confirmado real: la categoría "celulares" tiene 11 páginas (10 páginas de
12 + 1 página final de 4 = 124 productos), la página 12 devuelve 0
tarjetas. No hace falta Playwright ni ningún bypass de protecciones: es
un GET normal con querystring, igual de "legítimo" que la paginación de
cualquier otro spider de este proyecto.

Búsqueda: el formulario del sitio apunta a GET /catalogo?q=<término> y
reutiliza exactamente la misma estructura de tarjetas que el listado de
categoría, confirmado navegando /catalogo?q=iphone.
"""

import json
from typing import List, Optional

import httpx
from bs4 import BeautifulSoup

from .base_spider import BaseSpider, ScrapedItem

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Límite defensivo de páginas (12 productos/página), mismo criterio que el
# resto de spiders del proyecto. El catálogo real de "celulares" tiene 11
# páginas al momento de esta investigación.
_MAX_PAGES = 20


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
        """Scraping de categoría de productos, siguiendo la paginación por
        scroll infinito (`?js=1&pag=N`) que usa el sitio.

        Acepta URLs como:
        - /celulares
        - /celulares?marca=samsung
        - https://www.alemaniacell.com/celulares

        La página 1 se pide tal cual (sin `js=1`, igual que un browser
        normal); desde la página 2 en adelante se usa el endpoint de
        scroll infinito `?js=1&pag=N`, que devuelve el mismo contenedor y
        tarjetas que la página completa.
        """
        if not category_url.startswith("http"):
            if not category_url.startswith("/"):
                category_url = f"/{category_url}"
            category_url = f"{self.base_url}{category_url}"

        base = category_url.split("?")[0]
        separator = "&" if "?" in category_url and category_url.split("?", 1)[1] else "?"
        extra_query = category_url.split("?", 1)[1] if "?" in category_url else ""

        items: List[ScrapedItem] = []
        seen_urls = set()

        async with httpx.AsyncClient(timeout=30, headers=_HEADERS, follow_redirects=True) as client:
            for page_number in range(1, _MAX_PAGES + 1):
                if page_number == 1:
                    page_url = category_url
                else:
                    js_param = f"js=1&pag={page_number}"
                    query = f"{extra_query}&{js_param}" if extra_query else js_param
                    page_url = f"{base}?{query}"

                page_items = await self._scrape_listing_with_client(client, page_url)

                new_any = False
                for item in page_items:
                    if item.product_url in seen_urls:
                        continue
                    seen_urls.add(item.product_url)
                    items.append(item)
                    new_any = True

                # Sin tarjetas nuevas: fin real de la paginación.
                if not new_any:
                    break

        return items

    async def _scrape_listing(self, url: str) -> List[ScrapedItem]:
        """Scraping de una sola página, abriendo su propio cliente httpx.

        Usado por `search`, que no necesita paginar (ver docstring del
        módulo: no se confirmó paginación equivalente para /catalogo?q=).
        """
        async with httpx.AsyncClient(timeout=30, headers=_HEADERS, follow_redirects=True) as client:
            return await self._scrape_listing_with_client(client, url)

    async def _scrape_listing_with_client(
        self, client: httpx.AsyncClient, url: str
    ) -> List[ScrapedItem]:
        """Scraping de página de listado de productos usando httpx + BeautifulSoup."""
        items: List[ScrapedItem] = []

        try:
            response = await client.get(url)
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
