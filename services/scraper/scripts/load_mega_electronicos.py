"""Carga puntual: corre el spider de Mega Electronicos y guarda los
resultados reales en Supabase (products + product_prices), via REST API.

Uso: python scripts/load_mega_electronicos.py
Requiere .env en la raiz del repo con SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY.
"""

import asyncio
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spiders.mega_electronicos_spider import MegaElectronicosSpider

STORE_NAME = "Mega Electronicos"
CATEGORY_PATH = "/producto/categoria/celular/110101"


def load_env():
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "..",
        ".env",
    )
    env_path = os.path.abspath(env_path)
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ[k] = v


def supabase_request(method, path, base_url, service_key, payload=None):
    url = f"{base_url}/rest/v1/{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("apikey", service_key)
    req.add_header("Authorization", f"Bearer {service_key}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Prefer", "return=representation")
    with urllib.request.urlopen(req) as resp:
        body = resp.read()
        return json.loads(body) if body else None


def get_or_create_store(base_url, service_key):
    existing = supabase_request(
        "GET", f"stores?name=eq.{STORE_NAME.replace(' ', '%20')}&select=id",
        base_url, service_key,
    )
    if existing:
        return existing[0]["id"]

    created = supabase_request(
        "POST", "stores", base_url, service_key,
        payload={"name": STORE_NAME, "website_url": "https://megaelectronicos.com.py"},
    )
    return created[0]["id"]


def get_or_create_product(base_url, service_key, title, image_url):
    escaped = title.replace(" ", "%20").replace('"', "%22")
    existing = supabase_request(
        "GET", f"products?name=eq.{escaped}&select=id",
        base_url, service_key,
    )
    if existing:
        return existing[0]["id"]

    created = supabase_request(
        "POST", "products", base_url, service_key,
        payload={
            "name": title,
            "brand": "Xiaomi",
            "category": "celulares",
            "main_image_url": image_url,
        },
    )
    return created[0]["id"]


def upsert_price(base_url, service_key, product_id, store_id, item):
    supabase_request(
        "POST", "product_prices?on_conflict=product_id,store_id,product_url",
        base_url, service_key,
        payload={
            "product_id": product_id,
            "store_id": store_id,
            "price": item.price,
            "original_price": item.original_price,
            "product_url": item.product_url,
            "in_stock": item.in_stock,
        },
    )


async def main():
    load_env()
    base_url = os.environ["SUPABASE_URL"]
    service_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

    spider = MegaElectronicosSpider()
    items = await spider.fetch_category(CATEGORY_PATH)
    print(f"Scrapeados {len(items)} productos reales.")

    store_id = get_or_create_store(base_url, service_key)
    print(f"Store id: {store_id}")

    loaded = 0
    for item in items:
        try:
            product_id = get_or_create_product(base_url, service_key, item.title, item.image_url)
            upsert_price(base_url, service_key, product_id, store_id, item)
            loaded += 1
        except Exception as exc:
            print(f"Error cargando '{item.title}': {exc}")

    print(f"Cargados {loaded}/{len(items)} productos en Supabase.")


if __name__ == "__main__":
    asyncio.run(main())
