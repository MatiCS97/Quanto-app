"""Carga puntual: corre el spider de Mega Electronicos y guarda los
resultados reales en Supabase (products + product_prices), via REST API.

Uso: python scripts/load_mega_electronicos.py
Requiere .env en la raiz del repo con SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _load_common import run_load
from spiders.mega_electronicos_spider import MegaElectronicosSpider

STORE_NAME = "Mega Electronicos"
WEBSITE_URL = "https://megaelectronicos.com.py"
CATEGORY_PATH = "/producto/categoria/celular/110101"


async def main():
    spider = MegaElectronicosSpider()
    await run_load(spider, STORE_NAME, WEBSITE_URL, CATEGORY_PATH)


if __name__ == "__main__":
    asyncio.run(main())
