"""Spider para ContiMarket (https://contimarket.com), el marketplace de
e-commerce del Banco Continental de Paraguay, rubro celulares y accesorios.

Contexto de investigación (importante para quien mantenga esto):

- La plataforma es GrandNode (e-commerce .NET). La categoría
  "Celulares y Accesorios" (https://contimarket.com/celulares-y-accesorios)
  es en realidad un MARKETPLACE multi-vendedor: cada producto pertenece a
  un "Vendor" (ej. "LA ELECTROTIENDA", "COMPRE MEJOR", "AMERICAN STORE",
  "COMPUMARKET", "PC HOUSE", etc.), no a ContiMarket como vendedor directo.
  Este spider no filtra por vendedor: trae todo lo publicado en la
  categoría, igual que el resto de los spiders del proyecto tratan una
  categoría dada.

- Investigación de red real con Playwright (`page.on("request", ...)`,
  headless=True): NO existe ningún endpoint AJAX/XHR/fetch que traiga los
  productos como JSON. La única request de documento es el GET normal a
  la URL de categoría. La confusión inicial (ver nota histórica más abajo)
  vino de mirar el HTML "en frío" sin ejecutar JS: el bloque
  `var catalog = new Vue({ data() { return { Model: [] } } })` con
  `created() { this.Model = {...} }` que aparece cerca del principio del
  HTML es SOLO el estado inicial de un componente Vue que maneja
  paginación/ordenamiento/filtros del lado cliente (botones "página
  siguiente", cambios de orden, etc. via `catalog.loadProducts(url)` ->
  `axios.get(url, {headers: {'X-Response-View': 'Json'}})`). Ese Vue
  interno arranca con `Products: []` y `TotalItems: 0`. PERO el listado de
  productos que ve el usuario en la carga inicial NO depende de ese Vue:
  viene server-side renderizado (Razor/GrandNode) directamente en el HTML
  de la respuesta inicial, embebido como un array JSON plano
  `"Products":[{"Name":...},...]` en un bloque de datos separado (probable
  estado inicial para hidratación/analytics), visible con un GET normal.

- CONFIRMADO: un GET simple con httpx (con o sin cookies previas, con
  headers de navegador normales) a la URL de categoría trae los 12
  productos reales de esa página embebidos en el HTML inicial, con
  nombre, SKU, precio actual, precio anterior, URL, imagen, vendedor y
  bandera de "no se puede comprar" (indicador de stock). No hace falta
  Playwright ni ningún navegador: httpx + regex/JSON basta. Esto es MÁS
  simple que lo anticipado (no hubo que reemplazar un endpoint AJAX
  encontrado por Playwright, porque nunca existió tal endpoint: los
  "productos AJAX" resultaron ser un array ya presente en la respuesta
  HTML normal).

- Paginación: `?pagenumber=N` sobre la misma URL de categoría (ej.
  `https://contimarket.com/celulares-y-accesorios?pagenumber=2`), 12
  productos por página. La categoría de celulares tiene ~107 páginas
  (~1277 ítems) al momento de esta investigación, por lo que se aplica un
  límite defensivo de páginas (igual criterio que tecnostore_spider.py)
  para no generar una carga excesiva ni quedar en loop si el sitio cambia
  su paginación.

- Precio: campo `ProductPrice.PriceValue` (float, en Guaraníes, ya
  numérico, ej. 2590000.0) y `ProductPrice.OldPriceValue` (precio antes
  del descuento, mismo formato; puede ser 0 o ausente si no hay oferta).
  No hace falta parsear strings de precio con separadores de miles.

- Stock: no hay un campo booleano "IsAvailable" directo y confiable; se
  usa `ProductPrice.DisableBuyButton` (True cuando GrandNode deshabilitó
  el botón de compra, típicamente sin stock) como proxy de
  `in_stock = not DisableBuyButton`.

- Promoción bancaria (NO se carga a bank_promotions desde este archivo,
  solo documentada aquí para quien decida si aplica):
  El footer/página de términos (`/conditionsofuse-2`) describe DOS
  programas de financiamiento del Banco Continental, ninguno es un
  descuento porcentual:
    1. "Financiación en hasta 6 cuotas sin intereses": para
       tarjetahabientes de CUALQUIER tarjeta de crédito emitida por Banco
       Continental, en todas las compras de contimarket.com.
       "Promoción por tiempo limitado" (sin fecha de fin específica
       publicada en esa página).
    2. "Financiación en 36 cuotas CON intereses" (según tarifario del
       banco): solo para tarjetahabientes Mastercard emitidas por Banco
       Continental, y solo para compras desde Gs. 10.000.000.
  Además, cada tarjeta de producto en el listado muestra un texto
  genérico "12 cuotas de <PriceCuota> con tarjetas de [logo Mastercard]"
  (campo `ProductPrice.PriceCuota` = precio/12), que es solo una
  simulación de cuota mostrada por producto y no corresponde 1:1 a
  ninguno de los dos programas contractuales de arriba (ese "12 cuotas"
  no aparece descrito en los términos como programa propio). Como es
  financiamiento en cuotas y no un % de descuento sobre el precio, no
  encaja en el esquema de `bank_promotions.discount_percentage` del
  proyecto.
"""

import json
from typing import List, Optional

import httpx

from .base_spider import BaseSpider, ScrapedItem

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-PY,es;q=0.9,en;q=0.8",
}

# Límite defensivo de páginas (12 productos/página): la categoría de
# celulares tiene ~107 páginas reales, pero no tiene sentido cargar todo
# el marketplace en una corrida puntual. Igual criterio que otros spiders
# del proyecto (ver tecnostore_spider.py).
_MAX_PAGES = 15


class ContiMarketSpider(BaseSpider):
    store_name = "ContiMarket"
    base_url = "https://contimarket.com"

    async def search(self, query: str) -> List[ScrapedItem]:
        """Búsqueda por texto usando el buscador nativo de GrandNode."""
        url = f"{self.base_url}/search?q={query}"
        items, _ = await self._scrape_page(url)
        return items

    async def fetch_category(self, category_url: str) -> List[ScrapedItem]:
        """Scraping de categoría de productos, siguiendo `?pagenumber=N`.

        Acepta URLs como:
        - /celulares-y-accesorios
        - https://contimarket.com/celulares-y-accesorios
        """
        if not category_url.startswith("http"):
            category_url = f"{self.base_url}{category_url}"

        separator = "&" if "?" in category_url else "?"

        items: List[ScrapedItem] = []
        seen_urls = set()

        async with httpx.AsyncClient(timeout=30, headers=_HEADERS, follow_redirects=True) as client:
            for page_number in range(1, _MAX_PAGES + 1):
                page_url = (
                    category_url
                    if page_number == 1
                    else f"{category_url}{separator}pagenumber={page_number}"
                )

                page_items = await self._scrape_page_with_client(client, page_url)

                new_any = False
                for item in page_items:
                    if item.product_url in seen_urls:
                        continue
                    seen_urls.add(item.product_url)
                    items.append(item)
                    new_any = True

                # Si la página no aportó productos nuevos (fin real de la
                # paginación, o el sitio cambió su estructura), no seguir.
                if not new_any:
                    break

        return items

    async def _scrape_page(self, url: str):
        """Scraping de una sola página, abriendo su propio cliente httpx."""
        async with httpx.AsyncClient(timeout=30, headers=_HEADERS, follow_redirects=True) as client:
            items = await self._scrape_page_with_client(client, url)
        return items, None

    async def _scrape_page_with_client(self, client: httpx.AsyncClient, url: str) -> List[ScrapedItem]:
        try:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text
        except Exception:
            return []

        products = _extract_products_from_html(html)
        items = [self._to_scraped_item(p) for p in products]
        return [item for item in items if item is not None]

    def _to_scraped_item(self, product: dict) -> Optional[ScrapedItem]:
        try:
            name = (product.get("Name") or "").strip()
            url = product.get("Url")
            if not name or not url:
                return None

            price_info = product.get("ProductPrice") or {}
            price = float(price_info.get("PriceValue") or 0)
            if price <= 0:
                return None

            old_price = float(price_info.get("OldPriceValue") or 0)
            original_price = old_price if old_price > price else None

            image_url = None
            picture = product.get("DefaultPictureModel") or {}
            image_url = picture.get("ImageUrl") or picture.get("FullSizeImageUrl")

            in_stock = not bool(price_info.get("DisableBuyButton", False))

            return ScrapedItem(
                title=name,
                price=price,
                original_price=original_price,
                product_url=url,
                image_url=image_url,
                in_stock=in_stock,
            )
        except Exception:
            return None


def _extract_products_from_html(html: str) -> List[dict]:
    """Extrae los arrays `"Products":[...]` embebidos en el HTML inicial.

    GrandNode renderiza el catálogo server-side y lo embebe, entre otros
    bloques de estado (incluyendo un estado inicial vacío de un componente
    Vue de paginación/orden), como JSON plano `"Products":[{...}, ...]`.
    Se buscan todas las ocurrencias del marcador y se parsean con json.loads
    usando conteo de corchetes balanceado (respetando strings/escapes) para
    no depender de que el array completo esté en una sola línea.
    """
    products: List[dict] = []
    pos = 0
    marker = '"Products":['
    while True:
        idx = html.find(marker, pos)
        if idx == -1:
            break

        array_start = idx + len('"Products":')
        array_text = _extract_balanced_array(html, array_start)
        if array_text:
            try:
                parsed = json.loads(array_text)
                if isinstance(parsed, list):
                    products.extend(p for p in parsed if isinstance(p, dict) and p.get("Sku"))
            except Exception:
                pass
            pos = array_start + len(array_text)
        else:
            pos = idx + len(marker)

    # Deduplicar por Sku (por si el mismo array aparece más de una vez).
    seen = set()
    unique_products = []
    for p in products:
        sku = p.get("Sku")
        if sku in seen:
            continue
        seen.add(sku)
        unique_products.append(p)
    return unique_products


def _extract_balanced_array(text: str, start: int) -> Optional[str]:
    """Devuelve el substring `[...]` balanceado que arranca en `start`
    (que debe apuntar a un caracter '['), respetando strings/escapes JSON."""
    if start >= len(text) or text[start] != "[":
        return None

    depth = 0
    in_string = False
    escaped = False
    i = start
    while i < len(text):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        i += 1
    return None
