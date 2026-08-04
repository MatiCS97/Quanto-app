"""Spider de ejemplo — plantilla a copiar por cada tienda nueva.

Los selectores CSS de abajo son placeholders. Cuando el selector real
cambie (va a pasar, es el riesgo #1 del proyecto), este es el archivo
a tocar — no el pipeline ni el scheduler.
"""

from playwright.async_api import async_playwright

from .base_spider import BaseSpider, ScrapedItem


class ExampleStoreSpider(BaseSpider):
    store_name = "Example Store"
    base_url = "https://www.example-store.com.py"

    async def search(self, query: str) -> list[ScrapedItem]:
        url = f"{self.base_url}/buscar?q={query}"
        return await self._scrape_listing(url)

    async def fetch_category(self, category_url: str) -> list[ScrapedItem]:
        return await self._scrape_listing(category_url)

    async def _scrape_listing(self, url: str) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle")

            cards = await page.query_selector_all(".product-card")
            for card in cards:
                title_el = await card.query_selector(".product-title")
                price_el = await card.query_selector(".product-price")
                link_el = await card.query_selector("a")
                img_el = await card.query_selector("img")

                if not (title_el and price_el and link_el):
                    continue

                title = (await title_el.inner_text()).strip()
                price_text = (await price_el.inner_text()).strip()
                price = _parse_guarani_price(price_text)
                href = await link_el.get_attribute("href")
                img_src = await img_el.get_attribute("src") if img_el else None

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

            await browser.close()
        return items


def _parse_guarani_price(text: str) -> float:
    """'Gs. 1.250.000' -> 1250000.0"""
    digits = "".join(ch for ch in text if ch.isdigit())
    return float(digits) if digits else 0.0
