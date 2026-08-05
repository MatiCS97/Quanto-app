"""Carga puntual: corre el spider de Tienda Movil y guarda los
resultados reales en Supabase (products + product_prices), via REST API.

Uso: python scripts/load_tienda_movil.py
Requiere .env en la raiz del repo con SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _load_common import run_load
from spiders.tienda_movil_spider import TiendaMovilSpider

STORE_NAME = "Tienda Movil"
WEBSITE_URL = "https://tiendamovil.com.py"
CATEGORY_PATH = "/shop/celulares/"


async def main():
    spider = TiendaMovilSpider()
    await run_load(spider, STORE_NAME, WEBSITE_URL, CATEGORY_PATH)


if __name__ == "__main__":
    asyncio.run(main())
