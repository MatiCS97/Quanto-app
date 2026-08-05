"""Spider para Compras Paraguai (https://www.comprasparaguai.com.br/), categoría celular.

ADVERTENCIA DE DISEÑO — LEER ANTES DE USAR ESTE SPIDER EN PRODUCCIÓN
=====================================================================

Compras Paraguai NO es una tienda. Es un agregador/comparador de precios
que ya scrapea y republica ofertas de ~50+ tiendas paraguayas (Nissei,
VisãoVIP, Shopping China, Cellshop, Mobile Zone, Atacado Connect, etc.).
El propio sitio lo dice explícitamente: "o Compras Paraguai não possui
loja e nem realiza venda de produtos. Somos um comparador de preços."

Es, de hecho, un competidor directo de Quanto (mismo modelo de negocio).
Se usa aquí ÚNICAMENTE como fuente indirecta/temporal para poder mostrar
precios de tiendas que bloquean scraping directo por Cloudflare en su
sitio original (Nissei, VisãoVIP). Esto implica un riesgo aceptado: los
datos pueden estar desactualizados respecto a la tienda real, porque
pasan por un intermediario que los cachea a su propio ritmo.

CÓMO SE RESOLVIÓ LA ATRIBUCIÓN DE TIENDA REAL (investigación confirmada)
--------------------------------------------------------------------------
La página de LISTADO de categoría (`/celular/`) NO sirve para esto: cada
producto ahí solo muestra un precio "a partir de" y un botón "N OFERTAS"
sin decir de qué tienda. Usar esa página habría obligado a inventar o a
mostrar "vendido por Compras Paraguai", lo cual sería un dato falso.

En cambio, la página de DETALLE de cada producto
(`/<slug-producto>_<id>/`) sí lista cada oferta individual dentro de
`<div id="container-ofertas">`, y cada oferta trae, en el HTML servido
por el propio servidor (sin JS, confirmado con httpx plano):
  - El nombre de la tienda real que vende esa unidad, dos veces:
    - atributo `title` (y `alt`) de `img.store-image`, ej. title="Nissei"
    - también aparece en `data-advertiser` / los payloads de `gtag(...)`
      embebidos como `'advertiser': 'Nissei'`
  - Un link `a.btn-store-redirect[href]` que apunta AL SITIO REAL de la
    tienda (ej. https://nissei.com/br/catalog/product/view/id/1651071),
    no a Compras Paraguai.
  - El precio de esa oferta específica, en `US$` y en `R$` (ver limitación
    de moneda más abajo).

Se confirmó esto contra dos productos reales de la categoría celular:
  - "Apple iPhone 17 A3520 256 GB - Azul Névoa" (id 63988): 208 bloques de
    oferta, con tiendas reales distintas: Nissei, Shopping China,
    Cellshop, Mobile Zone, VisãoVIP, Atacado Connect, Mega Eletrônicos,
    Star Company, Prime Shop, etc. (los últimos 3-5 bloques del HTML son
    "Produtos Relacionados", no ofertas — por eso se limita la búsqueda al
    contenedor `#container-ofertas`, que descarta ese ruido).
  - "Celular Tecno Spark 30C KL5 Dual Chip 256GB 4G" (id 57380): la página
    anuncia "9 OFERTAS em 5 lojas" y el contenedor `#container-ofertas`
    trae exactamente 9 bloques, confirmando 1:1 el conteo declarado por
    el sitio contra lo extraído.

ALCANCE DELIBERADAMENTE ACOTADO A NISSEI Y VISÃOVIP
------------------------------------------------------
Compras Paraguai agrega ofertas de 40+ tiendas distintas por producto
(confirmado: 46 tiendas distintas en una muestra de solo 10 productos).
La mayoría de esas tiendas nunca fueron evaluadas por este proyecto — no
sabemos si son legítimas, si sus datos son confiables, ni nada sobre
ellas. Por decisión explícita del usuario, este spider descarta cualquier
oferta que no sea de Nissei o VisãoVIP (las dos tiendas que sabemos
bloqueadas por Cloudflare y que motivaron usar esta fuente indirecta en
primer lugar). Si en el futuro se decide aceptar más tiendas de este
agregador, debe ser una decisión explícita nueva, no un efecto colateral
de este spider.

CÓMO SE REPRESENTA LA "TIENDA REAL"
-----------------------------------------------------------------------
`ScrapedItem` (ver base_spider.py) no tiene un campo para la tienda de
origen real — solo existe `store_name` a nivel de spider/clase, que
asume una tienda fija por spider. Como en este spider la tienda real SÍ
puede variar por oferta (aunque acotada a solo 2 valores posibles), en
vez de forzar el dato dentro del `title` (frágil: rompería la detección
de marca y ensuciaría el nombre visible del producto en cualquier
consumidor del pipeline), este spider expone `fetch_offers_by_store()`,
que devuelve un dict `{nombre_tienda_real: [ScrapedItem, ...]}`. Quien
cargue estos datos debe resolver/crear una fila de `stores` por cada
clave real (Nissei, VisãoVIP), nunca una fila "Compras Paraguai".

`product_url` de cada item ya apunta al sitio REAL de la tienda
(`btn-store-redirect`), no al agregador — así que si alguien hace clic,
termina en Nissei o VisãoVIP, no en Compras Paraguai.

`fetch_category`/`search` (requeridos por BaseSpider) devuelven la unión
de ambas tiendas en una sola lista, para cumplir el contrato — pero
cualquier código que necesite atribuir la tienda real debe usar
`fetch_offers_by_store()` en su lugar.

LIMITACIÓN CONOCIDA: MONEDA (USD, no Guaraníes)
--------------------------------------------------
Los precios en comprasparaguai.com.br se muestran en `US$` y en `R$`
(reales brasileños) — NUNCA en Guaraníes, a diferencia del resto de la
base de datos de Quanto, que asume Gs. No existe en el sitio ninguna
tasa de cambio a Gs. confiable ni oficial para hacer la conversión acá.

Este spider NO convierte a Gs. con una tasa inventada/hardcodeada: eso
sería peor que no tener el dato, porque produciría un precio "en
guaraníes" falso que nadie podría auditar. En su lugar:
  - `ScrapedItem.price` / `original_price` quedan en USD tal cual los
    reporta el sitio (float, ej. 910.00). El `title` NO lleva ningún
    aviso de moneda embebido — ese aviso vive en `stores.is_indirect_source`
    / `stores.source_note` (migración 0003_indirect_sources.sql), que la
    UI usa para mostrarlo a nivel de tienda, no de producto.
  - Cualquier script de carga (`scripts/load_*.py`) que use este spider
    DEBE decidir explícitamente qué hacer con la conversión (aplicar una
    tasa documentada externamente, o rechazar la carga) antes de meter
    estos precios en `product_prices`. Este spider no lo decide por vos.
    Ver `scripts/load_comprasparaguai.py` para la tasa usada.

Formato de precio fuente: "US$ 910,00" o "US$ 1.325,00" (punto de miles,
coma decimal — estilo pt-BR/es-PY). `_parse_brl_usd_price` maneja ambos.
"""

import re
from typing import Dict, List, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from .base_spider import BaseSpider, ScrapedItem

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,es;q=0.8",
}

# Alcance deliberadamente acotado — ver docstring del módulo. Comparación
# case-insensitive porque el sitio no siempre capitaliza igual. Todas las
# variantes normalizan al nombre canónico correspondiente.
_TIENDAS_ACEPTADAS = {
    "nissei": "Nissei",
    "visãovip": "VisãoVIP",
    "visaovip": "VisãoVIP",
    "visão vip": "VisãoVIP",
    "visao vip": "VisãoVIP",
}


class ComprasParaguaiSpider(BaseSpider):
    """Fuente indirecta: agregador que republica ofertas de otras tiendas.

    Ver docstring del módulo. `store_name` identifica la fuente HTTP
    consultada (Compras Paraguai), NO la tienda que realmente vende cada
    producto — para eso usar `fetch_offers_by_store()`.
    """

    store_name = "Compras Paraguai"
    base_url = "https://www.comprasparaguai.com.br"
    default_category_path = "/celular/"

    async def search(self, query: str) -> List[ScrapedItem]:
        """Búsqueda por término dentro de la categoría celular.

        Compras Paraguai no expone una búsqueda de texto simple confirmada
        por URL para este spider; se filtra sobre el listado de celulares.
        """
        query_lower = query.strip().lower()
        by_store = await self.fetch_offers_by_store(self.default_category_path)
        all_items = [item for items in by_store.values() for item in items]
        return [item for item in all_items if query_lower in item.title.lower()]

    async def fetch_category(
        self, category_url: str, max_pages: int = 2, max_products: Optional[int] = None
    ) -> List[ScrapedItem]:
        """Unión de ofertas de Nissei y VisãoVIP para `category_url`.

        Para conservar la atribución real de tienda, usar
        `fetch_offers_by_store()` en vez de este método.
        """
        by_store = await self.fetch_offers_by_store(category_url, max_pages, max_products)
        return [item for items in by_store.values() for item in items]

    async def fetch_offers_by_store(
        self, category_url: str, max_pages: int = 2, max_products: Optional[int] = None
    ) -> Dict[str, List[ScrapedItem]]:
        """Recorre el listado de celulares y devuelve ofertas agrupadas por tienda real.

        `category_url` acepta una ruta relativa (ej. "/celular/") o una URL
        completa. `max_pages` limita cuántas páginas de listado (?page=N)
        se recorren — el sitio tiene ~64 páginas de listado para celular,
        y cada producto listado implica un fetch adicional a su página de
        detalle, así que sin límite esto es una operación muy pesada.
        `max_products` limita cuántos productos del listado se expanden a
        detalle (útil para pruebas rápidas); None = sin límite.

        Solo incluye ofertas de las tiendas en `_TIENDAS_ACEPTADAS`
        (Nissei, VisãoVIP) — ver "ALCANCE DELIBERADAMENTE ACOTADO" arriba.
        """
        if not category_url:
            category_url = self.default_category_path
        if not category_url.startswith("http"):
            category_url = urljoin(self.base_url, category_url)

        product_links = await self._collect_product_links(category_url, max_pages)
        if max_products is not None:
            product_links = product_links[:max_products]

        result: Dict[str, List[ScrapedItem]] = {name: [] for name in set(_TIENDAS_ACEPTADAS.values())}

        async with httpx.AsyncClient(timeout=30, headers=_HEADERS, follow_redirects=True) as client:
            for product_url in product_links:
                try:
                    response = await client.get(product_url)
                    response.raise_for_status()
                except Exception:
                    continue
                for store_name_real, item in _parse_offers(response.text, product_url):
                    result[store_name_real].append(item)

        return result

    async def _collect_product_links(self, listing_url: str, max_pages: int) -> List[str]:
        links: List[str] = []
        seen = set()

        async with httpx.AsyncClient(timeout=30, headers=_HEADERS, follow_redirects=True) as client:
            for page in range(1, max_pages + 1):
                page_url = listing_url if page == 1 else f"{listing_url}?page={page}"
                try:
                    response = await client.get(page_url)
                    response.raise_for_status()
                except Exception:
                    break

                soup = BeautifulSoup(response.text, "html.parser")
                found_this_page = 0
                for a in soup.select(".promocao-item-nome a[href]"):
                    href = a.get("href")
                    if not href:
                        continue
                    full_url = urljoin(self.base_url, href)
                    if full_url in seen:
                        continue
                    seen.add(full_url)
                    links.append(full_url)
                    found_this_page += 1

                if found_this_page == 0:
                    break  # se acabaron las páginas de listado

        return links


def _parse_offers(html: str, product_url: str):
    """Extrae cada oferta real (tienda + precio) de una página de detalle.

    Yields (nombre_tienda_canonico, ScrapedItem) solo para tiendas dentro
    de `_TIENDAS_ACEPTADAS`. Limitado a `#container-ofertas` porque el
    resto de la página (ej. "Produtos Relacionados") reusa clases
    visualmente similares pero no son ofertas del producto actual.
    """
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one("#container-ofertas")
    if not container:
        return

    name_tag = soup.select_one(".header-product-info h1, .promocao-item-nome a")
    base_title = name_tag.get_text(strip=True) if name_tag else "Producto"

    for box in container.select(".promocao-produtos-item-box"):
        store_img = box.select_one("img.store-image")
        store_name_raw = (store_img.get("title") or store_img.get("alt") or "").strip() if store_img else ""

        price_tag = box.select_one(".promocao-item-preco-oferta strong")
        if not price_tag or not store_name_raw:
            continue  # sin tienda real confirmada o sin precio: no inventar

        store_name_canonico = _TIENDAS_ACEPTADAS.get(store_name_raw.strip().lower())
        if store_name_canonico is None:
            continue  # fuera del alcance acotado (solo Nissei/VisãoVIP)

        price_usd = _parse_brl_usd_price(price_tag.get_text(strip=True))
        if price_usd <= 0:
            continue

        real_link = box.select_one("a.btn-store-redirect")
        real_href = real_link.get("href") if real_link else None
        final_url = real_href if real_href else product_url  # fallback: URL del agregador

        img = box.select_one(".promocao-item-img img")
        image_url = img.get("data-src") or img.get("src") if img else None

        yield (
            store_name_canonico,
            ScrapedItem(
                title=base_title,
                price=price_usd,
                original_price=None,
                product_url=final_url,
                image_url=image_url,
                in_stock=True,
            ),
        )


def _parse_brl_usd_price(text: str) -> float:
    """Parsea 'US$ 910,00' o 'US$ 1.325,00' -> float (formato pt-BR/es-PY).

    Punto de miles, coma decimal. Descarta el símbolo de moneda y espacios.
    """
    digits = re.sub(r"[^\d,]", "", text)  # deja solo dígitos y coma (el punto de miles ya se descarta acá)
    digits = digits.replace(",", ".")
    try:
        return float(digits)
    except ValueError:
        return 0.0
