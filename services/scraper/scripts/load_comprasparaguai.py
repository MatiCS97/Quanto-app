"""Carga puntual: trae ofertas de Nissei y VisãoVIP vía Compras Paraguai
(fuente indirecta, ver docstring de spiders/comprasparaguai_spider.py) y
las guarda en Supabase como si fueran esas tiendas reales — nunca como
"Compras Paraguai" (que no vende nada).

LIMITACIÓN DE MONEDA: los precios llegan en USD, no en Gs. Este script
convierte con una tasa fija documentada abajo. Esa tasa se desactualiza
con el tiempo — revisarla antes de confiar en el precio final mostrado.

Uso: python scripts/load_comprasparaguai.py [max_pages] [max_products]
Requiere .env en la raiz del repo con SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _load_common import (
    get_or_create_product,
    get_or_create_store,
    load_env,
    upsert_price,
)
from spiders.comprasparaguai_spider import ComprasParaguaiSpider

CATEGORY_PATH = "/celular/"

# Tasa de cambio USD -> Gs. oficial del Banco Central del Paraguay (BCP),
# cotización referencial del 04/08/2026 (bcp.gov.py/webapps/web/cotizacion/monedas).
# NO es una tasa en vivo: se desactualiza con el tiempo. Revisar/actualizar
# antes de confiar en el precio final si este script se vuelve a correr
# más adelante — el precio mostrado para Nissei/VisãoVIP puede desviarse
# del real si esta constante queda vieja.
USD_TO_GS = 5969.48

_WEBSITE_URLS = {
    "Nissei": "https://nissei.com",
    "VisãoVIP": "https://visaovip.com",
}


async def main():
    max_pages = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    max_products = int(sys.argv[2]) if len(sys.argv) > 2 else None

    load_env()
    base_url = os.environ["SUPABASE_URL"]
    service_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

    spider = ComprasParaguaiSpider()
    by_store = await spider.fetch_offers_by_store(CATEGORY_PATH, max_pages=max_pages, max_products=max_products)

    for store_name, items in by_store.items():
        print(f"{store_name}: {len(items)} ofertas via Compras Paraguai (USD -> Gs. tasa {USD_TO_GS})")

        store_id = get_or_create_store(base_url, service_key, store_name, _WEBSITE_URLS.get(store_name, ""))
        print(f"  Store id: {store_id}")

        loaded = 0
        for item in items:
            if item.price <= 0:
                continue
            try:
                price_gs = round(item.price * USD_TO_GS, 2)
                original_price_gs = (
                    round(item.original_price * USD_TO_GS, 2) if item.original_price else None
                )
                product_id = get_or_create_product(base_url, service_key, item.title, item.image_url)
                upsert_price(
                    base_url,
                    service_key,
                    product_id,
                    store_id,
                    _WithConvertedPrice(item, price_gs, original_price_gs),
                )
                loaded += 1
            except Exception as exc:
                print(f"  Error cargando '{item.title}': {exc}")

        print(f"  Cargados {loaded}/{len(items)} productos en Supabase.")


class _WithConvertedPrice:
    """Wrapper minimo: mismo shape que ScrapedItem pero con precio ya en Gs."""

    def __init__(self, item, price_gs, original_price_gs):
        self.price = price_gs
        self.original_price = original_price_gs
        self.product_url = item.product_url
        self.in_stock = item.in_stock


if __name__ == "__main__":
    asyncio.run(main())
