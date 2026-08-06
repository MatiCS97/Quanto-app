"""Carga puntual: corre el spider de Tienda Naranja y guarda los
resultados reales en Supabase (products + product_prices), via REST API.

Uso: python scripts/load_tienda_naranja.py
Requiere .env en la raiz del repo con SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _load_common import run_load
from spiders.tienda_naranja_spider import TiendaNaranjaSpider

STORE_NAME = "Tienda Naranja"
WEBSITE_URL = "https://www.tiendanaranja.com.py"
CATEGORY_PATH = "/tecnologia-e-informatica/celulares/celulares.html"


async def main():
    spider = TiendaNaranjaSpider()
    await run_load(spider, STORE_NAME, WEBSITE_URL, CATEGORY_PATH)


if __name__ == "__main__":
    asyncio.run(main())
