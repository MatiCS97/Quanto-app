"""Carga puntual: corre el spider de ContiMarket y guarda los
resultados reales en Supabase (products + product_prices), via REST API.

Uso: python scripts/load_contimarket.py
Requiere .env en la raiz del repo con SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _load_common import run_load
from spiders.contimarket_spider import ContiMarketSpider

STORE_NAME = "ContiMarket"
WEBSITE_URL = "https://contimarket.com"
CATEGORY_PATH = "/celulares-y-accesorios"


async def main():
    spider = ContiMarketSpider()
    await run_load(spider, STORE_NAME, WEBSITE_URL, CATEGORY_PATH)


if __name__ == "__main__":
    asyncio.run(main())
