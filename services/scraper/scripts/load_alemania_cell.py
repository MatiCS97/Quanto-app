"""Carga puntual: corre el spider de Alemania Cell y guarda los
resultados reales en Supabase (products + product_prices), via REST API.

Uso: python scripts/load_alemania_cell.py
Requiere .env en la raiz del repo con SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _load_common import run_load
from spiders.alemania_cell_spider import AlemaniaCellSpider

STORE_NAME = "Alemania Cell"
WEBSITE_URL = "https://www.alemaniacell.com"
CATEGORY_PATH = "/celulares"


async def main():
    spider = AlemaniaCellSpider()
    await run_load(spider, STORE_NAME, WEBSITE_URL, CATEGORY_PATH)


if __name__ == "__main__":
    asyncio.run(main())
