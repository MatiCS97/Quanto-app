"""Spider para Tienda Naranja (https://www.tiendanaranja.com.py/).

Selectores CSS confirmados por exploracion real de
https://www.tiendanaranja.com.py/tecnologia-e-informatica/celulares/celulares.html
(sitio Magento, server-rendered; httpx simple + headers de navegador basta,
no hace falta un navegador headless):

- Tarjeta de producto: li.product-item
  El listado trae ademas UNA tarjeta extra que es una plantilla KnockoutJS
  vacia (data-bind="...", sin datos reales, usada para renderizado via AJAX
  del lado del cliente). Se filtra exigiendo que el div.product-item-info
  interno tenga atributo "id" (formato "product-item-info_<sku>"), que solo
  existe en las tarjetas ya renderizadas por el servidor.
- Nombre + link: a.product-item-link (texto y href, ambos ya absolutos)
- Precio: dentro de div.price-box:
    - Caso sin descuento: span.price-wrapper[data-price-amount] suelto
      (atributo "data-price-amount" ya numerico, ej. "2194000").
    - Caso con descuento ("Precio especial" / "-25%" etc.): dos
      span.price-wrapper, uno con data-price-type="finalPrice" (precio
      actual/rebajado) y otro con data-price-type="oldPrice" (precio de
      lista, va a original_price). El descuento es una simple rebaja de
      precio de la tienda (special_price vs regular_price de Magento), NO
      esta condicionado a ningun banco o metodo de pago.
  El atributo "data-price-amount" es la fuente de verdad: evita tener que
  parsear el texto visible "Gs 2.194.000 Cuotas sin intereses Pagá con
  puntos 35.388", donde el precio real viene pegado sin separador al texto
  de cuotas/puntos (ver _extract_price_amount).
- Imagen: primer img dentro de div.swiper-wrapper (carrusel de fotos del
  producto), atributo "src" ya absoluto.
- Stock: no se encontraron marcadores explicitos de "sin stock" ni clases
  de agotado en el listado (las 36 tarjetas reales tienen boton "Agregar
  al Carrito"). Se asume in_stock=True para todo lo que aparece listado,
  igual que Central Shop.

Paginacion:
- La categoria "celulares" tiene exactamente 36 productos reales. El sitio
  muestra enlaces de paginacion "?p=2".."?p=5" en el HTML (son generados
  siempre, asumiendo que pudiera haber mas de una pagina), pero el listado
  usa un modulo de filtrado por AJAX (Plumrocket_LayeredNavigationLite) y
  el parametro "?p=N" es ignorado por el render del servidor: se confirmo
  pidiendo p=1..7 y product_list_limit=24/36/48, y siempre devuelve las
  mismas 36 tarjetas. No hay pagina 2 real vista desde un cliente sin JS.
  fetch_category igualmente sigue los enlaces "a.page" por si en el futuro
  el catalogo crece y el servidor empieza a paginar de verdad; si una
  "pagina siguiente" devuelve el mismo set de IDs que la anterior, se
  detiene (evita loop infinito y duplicados).

Promocion bancaria (Itau) vista en el listado y en el detalle de producto:
ver services/scraper/scripts/load_tienda_naranja.py para el detalle
completo investigado (no se carga a bank_promotions porque es solo
financiamiento en cuotas sin interes, sin descuento de precio).
"""

from typing import List, Optional, Tuple

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


class TiendaNaranjaSpider(BaseSpider):
    store_name = "Tienda Naranja"
    base_url = "https://www.tiendanaranja.com.py"

    async def search(self, query: str) -> List[ScrapedItem]:
        """Buscar productos por termino usando el buscador del sitio (Magento)."""
        url = f"{self.base_url}/catalogsearch/result/?q={query}"
        return await self._scrape_listing(url)

    async def fetch_category(self, category_url: str, max_pages: int = 5) -> List[ScrapedItem]:
        """Scraping de categoria de productos.

        Acepta URLs como:
        - /tecnologia-e-informatica/celulares/celulares.html
        - https://www.tiendanaranja.com.py/tecnologia-e-informatica/celulares/celulares.html

        Sigue "?p=N" mientras el sitio devuelva tarjetas nuevas (ver nota de
        paginacion en el docstring del modulo: hoy siempre es una sola
        pagina real, pero esto deja el spider listo si el catalogo crece).
        """
        if not category_url.startswith("http"):
            category_url = f"{self.base_url}{category_url}"

        base = category_url.split("?")[0]

        items: List[ScrapedItem] = []
        seen_urls = set()

        for page in range(1, max_pages + 1):
            page_url = base if page == 1 else f"{base}?p={page}"
            page_items = await self._scrape_listing(page_url)
            if not page_items:
                break

            new_items = [it for it in page_items if it.product_url not in seen_urls]
            if not new_items:
                # Misma pagina que la anterior (sitio ignora "?p=N") -> parar.
                break

            for it in new_items:
                seen_urls.add(it.product_url)
            items.extend(new_items)

        return items

    async def _scrape_listing(self, url: str) -> List[ScrapedItem]:
        """Scraping de una pagina de listado usando httpx + BeautifulSoup."""
        items: List[ScrapedItem] = []

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=_HEADERS, follow_redirects=True)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")

                cards = soup.select("li.product-item")

                for card in cards:
                    try:
                        # Filtrar la tarjeta-plantilla KnockoutJS vacia: solo
                        # las tarjetas renderizadas por el servidor tienen
                        # id="product-item-info_<sku>" en este div.
                        info = card.select_one(".product-item-info")
                        if not info or not info.get("id"):
                            continue

                        link = card.select_one("a.product-item-link")
                        if not link:
                            continue

                        title = link.get_text(strip=True)
                        href = link.get("href")
                        if not title or not href:
                            continue

                        # Imagen: primera foto del carrusel de la tarjeta.
                        img = card.select_one(".swiper-wrapper img")
                        image_url = img.get("src") if img else None

                        price, original_price = _extract_prices(card)

                        items.append(
                            ScrapedItem(
                                title=title,
                                price=price,
                                original_price=original_price,
                                product_url=href if href.startswith("http") else f"{self.base_url}{href}",
                                image_url=image_url,
                                in_stock=True,
                            )
                        )
                    except Exception:
                        # Continuar si hay error en un elemento especifico
                        continue

        except Exception:
            # Si hay error en la solicitud, retornar lista vacia
            pass

        return items


def _extract_prices(card) -> Tuple[float, Optional[float]]:
    """Extraer precio actual y precio original (si hay descuento) de una tarjeta.

    Usa el atributo "data-price-amount" de span.price-wrapper, que Magento
    ya entrega como numero limpio (ej. "2194000"), en vez de parsear el
    texto visible del price-box, que mezcla el precio con el texto de
    "Cuotas sin intereses" y "Pagá con puntos" sin separador
    (ej. "Gs 2.194.000 Cuotas sin intereses Pagá con puntos 35.388").
    """
    price_box = card.select_one(".price-box")
    if not price_box:
        return 0.0, None

    price = 0.0
    original_price: Optional[float] = None

    final_wrapper = price_box.select_one('span.price-wrapper[data-price-type="finalPrice"]')
    old_wrapper = price_box.select_one('span.price-wrapper[data-price-type="oldPrice"]')

    if final_wrapper:
        price = _parse_price_amount(final_wrapper)
    else:
        # Sin descuento: un unico price-wrapper suelto (sin data-price-type
        # explicito de finalPrice, pero es el unico presente).
        any_wrapper = price_box.select_one("span.price-wrapper[data-price-amount]")
        if any_wrapper:
            price = _parse_price_amount(any_wrapper)

    if old_wrapper:
        parsed_old = _parse_price_amount(old_wrapper)
        if parsed_old > 0:
            original_price = parsed_old

    return price, original_price


def _parse_price_amount(price_wrapper) -> float:
    """Leer el atributo numerico data-price-amount de un span.price-wrapper.

    Con fallback a parsear el texto visible (span.price, formato
    "Gs 2.194.000") por si el atributo faltara en algun caso no visto.
    """
    amount_attr = price_wrapper.get("data-price-amount")
    if amount_attr:
        try:
            return float(amount_attr)
        except ValueError:
            pass

    price_elem = price_wrapper.select_one(".price")
    text = price_elem.get_text(strip=True) if price_elem else price_wrapper.get_text(strip=True)
    return _parse_guarani_price(text)


def _parse_guarani_price(text: str) -> float:
    """Parsear precio en Guarani desde texto visible tipo "Gs 2.194.000".

    Solo se usa como fallback si data-price-amount no esta presente.
    """
    if not text:
        return 0.0

    text = text.strip()
    cleaned = "".join(ch for ch in text if ch.isdigit() or ch in ".,")
    if not cleaned:
        return 0.0

    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    else:
        cleaned = cleaned.replace(".", "")

    try:
        return float(cleaned)
    except ValueError:
        return 0.0
