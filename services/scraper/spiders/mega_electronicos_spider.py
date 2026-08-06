"""Spider para Mega Electrónicos (https://megaelectronicos.com.py).

Selectores CSS confirmados por exploración real:
- Tarjeta de producto: .slider-product-card
- Título: .card-product-name
- Precio: .price-container (dentro de tarjeta)
- Link: a[href*="/producto/"] (dentro de tarjeta)
- Imagen: .slider-product-image

Paginación (investigación posterior, importante para quien mantenga esto):

- La categoría SÍ pagina vía querystring `?page=N` sobre la misma URL
  (ej. `/producto/categoria/celular/110101?page=2`), confirmado navegando
  con Playwright real: cada página trae 42 tarjetas de producto distintas
  (se verificaron los títulos, no son repetidos). El spider original solo
  pedía la URL sin `page`, es decir la página 1, y por eso solo cargaba 42
  productos de un catálogo mucho más grande.
- El HTML incluye un widget de paginación (`div.paginaciones`) con enlaces
  numerados y un link "Siguiente"; el texto "N resultados" que aparece en
  esa misma zona (ej. "769 resultados") NO corresponde a esta categoría
  puntual — es un contador más amplio (aparenta ser del buscador/total del
  sitio) y no debe usarse para estimar cuántas páginas tiene esta
  categoría. Se comprobó empíricamente en su lugar.
- Comportamiento real confirmado pidiendo páginas una por una: la 1 a la
  10 devuelven 42 tarjetas cada una de forma consistente (con algo de
  mezcla de categorías vecinas — p.ej. monitores — hacia el final, normal
  en sliders de catálogo). A partir de la página 11 el servidor cierra la
  conexión (`net::ERR_EMPTY_RESPONSE`) de forma consistente y repetible
  incluso tras reintentos con pausas largas — no es un bloqueo transitorio
  por velocidad de pedidos (se confirmó que la página 1 seguía funcionando
  bien inmediatamente después), sino el comportamiento real del backend al
  pedir una página fuera de rango. Por eso se trata un error de red al
  pedir una página como "fin de la paginación", igual que una página sin
  tarjetas.
- Se aplica un límite defensivo de páginas (mismo criterio que
  contimarket_spider.py / tienda_movil_spider.py) para no quedar en loop
  si el sitio cambia de comportamiento, y se espacia cada pedido de página
  con una pausa corta para no bombardear el sitio (ya se observó que puede
  responder con errores de red bajo ráfagas de pedidos muy rápidos).
"""

import asyncio
from typing import List

from playwright.async_api import async_playwright

from .base_spider import BaseSpider, ScrapedItem

# Límite defensivo de páginas. Se confirmó que la categoría real de
# celulares tiene 10 páginas (42 productos/página); se deja algo de
# margen por si el catálogo crece, sin dejar la corrida sin techo.
_MAX_PAGES = 15

# Pausa entre pedidos de página sucesivos, para no generar ráfagas de
# tráfico que el sitio pueda tratar como abuso.
_PAGE_DELAY_SECONDS = 2.0


class MegaElectronicosSpider(BaseSpider):
    store_name = "Mega Electrónicos"
    base_url = "https://megaelectronicos.com.py"

    async def search(self, query: str) -> List[ScrapedItem]:
        """Buscar productos por término.

        La API de búsqueda está disponible en /api/search-products
        pero por ahora usando navegación por categoría como fallback.
        """
        # Para búsqueda real, podríamos usar la API de búsqueda,
        # pero por ahora navegamos a la categoría de celulares como demostración
        return await self.fetch_category("/producto/categoria/celular/110101")

    async def fetch_category(self, category_url: str) -> List[ScrapedItem]:
        """Scraping de categoría de productos, siguiendo paginación `?page=N`."""
        if not category_url.startswith("http"):
            category_url = f"{self.base_url}{category_url}"

        base = category_url.split("?")[0]

        items: List[ScrapedItem] = []
        seen_urls = set()

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            try:
                for page_number in range(1, _MAX_PAGES + 1):
                    page_url = base if page_number == 1 else f"{base}?page={page_number}"

                    page_items = await self._scrape_listing(browser, page_url)

                    new_any = False
                    for item in page_items:
                        if item.product_url in seen_urls:
                            continue
                        seen_urls.add(item.product_url)
                        items.append(item)
                        new_any = True

                    # Sin tarjetas nuevas (página vacía o error de red al
                    # pedirla, ambos observados como "fin real del
                    # catálogo" en este sitio): no seguir pidiendo páginas.
                    if not new_any:
                        break

                    if page_number < _MAX_PAGES:
                        await asyncio.sleep(_PAGE_DELAY_SECONDS)
            finally:
                await browser.close()

        return items

    async def _scrape_listing(self, browser, url: str) -> List[ScrapedItem]:
        """Scraping de una página de listado de productos."""
        items: List[ScrapedItem] = []
        page = await browser.new_page()
        try:
            # Navegar y esperar a que cargue contenido. Si el sitio cierra
            # la conexión (fin real de la paginación en este backend) o
            # cualquier otro error de red/timeout ocurre, se trata como
            # "página sin productos" en vez de propagar la excepción.
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
            except Exception:
                return items

            # Esperar a que aparezcan tarjetas de producto
            try:
                await page.wait_for_selector(".slider-product-card", timeout=10000)
            except Exception:
                # Si no hay tarjetas, retornar lista vacía
                return items

            # Obtener todas las tarjetas de producto
            cards = await page.query_selector_all(".slider-product-card")

            for card in cards:
                try:
                    # Extraer título
                    title_el = await card.query_selector(".card-product-name")
                    if not title_el:
                        continue
                    title = (await title_el.inner_text()).strip()

                    # Extraer precio
                    price_el = await card.query_selector(".price-container")
                    if not price_el:
                        continue
                    price_text = (await price_el.inner_text()).strip()
                    price = _parse_guarani_price(price_text)

                    # Extraer link
                    link_el = await card.query_selector("a[href*='/producto/']")
                    if not link_el:
                        continue
                    href = await link_el.get_attribute("href")

                    # Extraer imagen
                    img_el = await card.query_selector(".slider-product-image")
                    img_src = None
                    if img_el:
                        img_src = await img_el.get_attribute("src")

                    # Crear item
                    items.append(
                        ScrapedItem(
                            title=title,
                            price=price,
                            original_price=None,
                            product_url=href if href.startswith("http") else f"{self.base_url}{href}",
                            image_url=img_src,
                            in_stock=True,
                        )
                    )
                except Exception:
                    # Continuar si hay error en un elemento específico
                    continue
        finally:
            await page.close()
        return items


def _parse_guarani_price(text: str) -> float:
    """Parsear precio en Guaraní de formatos como 'Gs. 1.166.578'."""
    # Remover "Gs." y espacios
    text = text.replace("Gs.", "").replace("Gs", "").strip()
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
