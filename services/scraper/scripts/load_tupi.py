"""Carga puntual: corre el spider de Tupi y guarda los
resultados reales en Supabase (products + product_prices), via REST API.

Uso: python scripts/load_tupi.py
Requiere .env en la raiz del repo con SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _load_common import run_load
from spiders.tupi_spider import TupiSpider

STORE_NAME = "Tupi"
WEBSITE_URL = "https://www.tupi.com.py"
CATEGORY_PATH = "/lineas/151/Celulares/"


async def main():
    spider = TupiSpider()
    await run_load(spider, STORE_NAME, WEBSITE_URL, CATEGORY_PATH)


if __name__ == "__main__":
    asyncio.run(main())
