"""Spider para Mega Electrónicos (https://megaelectronicos.com.py).

Selectores CSS confirmados por exploración real:
- Tarjeta de producto: .slider-product-card
- Título: .card-product-name
- Precio: .price-container (dentro de tarjeta)
- Link: a[href*="/producto/"] (dentro de tarjeta)
- Imagen: .slider-product-image
"""

from typing import List

from playwright.async_api import async_playwright

from .base_spider import BaseSpider, ScrapedItem


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
        url = f"{self.base_url}/producto/categoria/celular/110101"
        return await self._scrape_listing(url)

    async def fetch_category(self, category_url: str) -> List[ScrapedItem]:
        """Scraping de categoría de productos."""
        if not category_url.startswith("http"):
            category_url = f"{self.base_url}{category_url}"
        return await self._scrape_listing(category_url)

    async def _scrape_listing(self, url: str) -> List[ScrapedItem]:
        """Scraping de página de listado de productos."""
        items: List[ScrapedItem] = []
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page()

            # Navegar y esperar a que cargue contenido
            await page.goto(url, wait_until="networkidle", timeout=30000)

            # Esperar a que aparezcan tarjetas de producto
            try:
                await page.wait_for_selector(".slider-product-card", timeout=10000)
            except Exception:
                # Si no hay tarjetas, retornar lista vacía
                await browser.close()
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

            await browser.close()
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
