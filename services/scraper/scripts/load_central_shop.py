"""Carga puntual: corre el spider de Central Shop y guarda los
resultados reales en Supabase (products + product_prices), via REST API.

Uso: python scripts/load_central_shop.py
Requiere .env en la raiz del repo con SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _load_common import run_load
from spiders.central_shop_spider import CentralShopSpider

STORE_NAME = "Central Shop"
WEBSITE_URL = "https://www.centralshop.com.py"
CATEGORY_PATH = "/productos?categoria=celulares-y-smartwatches&pagina=1"


async def main():
    spider = CentralShopSpider()
    await run_load(spider, STORE_NAME, WEBSITE_URL, CATEGORY_PATH)


if __name__ == "__main__":
    asyncio.run(main())
