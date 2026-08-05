"""Carga puntual: corre el spider de TecnoStore y guarda los
resultados reales en Supabase (products + product_prices), via REST API.

Uso: python scripts/load_tecnostore.py
Requiere .env en la raiz del repo con SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _load_common import run_load
from spiders.tecnostore_spider import TecnoStoreSpider

STORE_NAME = "TecnoStore"
WEBSITE_URL = "https://tecnostore.com.py"
CATEGORY_PATH = "/v2/index.php/product-category/celulares/"


async def main():
    spider = TecnoStoreSpider()
    await run_load(spider, STORE_NAME, WEBSITE_URL, CATEGORY_PATH)


if __name__ == "__main__":
    asyncio.run(main())
