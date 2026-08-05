"""Utilidades compartidas por los scripts de carga puntual (scripts/load_*.py).

Cada tienda sigue el mismo patron: correr su spider, upsert de store,
upsert de products/product_prices via REST API de Supabase (urllib, sin
supabase-py por problemas de SSL local ya documentados en otros scripts).
"""

import json
import os
import urllib.parse
import urllib.request

KNOWN_BRANDS = [
    "Samsung", "Apple", "iPhone", "Xiaomi", "Honor", "Motorola",
    "Huawei", "Jota", "Itel", "Realme", "Tecno", "Infinix",
]


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


def supabase_request(method, path, base_url, service_key, payload=None, prefer="return=representation"):
    url = f"{base_url}/rest/v1/{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("apikey", service_key)
    req.add_header("Authorization", f"Bearer {service_key}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Prefer", prefer)
    with urllib.request.urlopen(req) as resp:
        body = resp.read()
        return json.loads(body) if body else None


def get_or_create_store(base_url, service_key, store_name, website_url):
    escaped = urllib.parse.quote(store_name, safe="")
    existing = supabase_request(
        "GET", f"stores?name=eq.{escaped}&select=id",
        base_url, service_key,
    )
    if existing:
        return existing[0]["id"]

    created = supabase_request(
        "POST", "stores", base_url, service_key,
        payload={"name": store_name, "website_url": website_url},
    )
    return created[0]["id"]


def guess_brand(title):
    upper = title.upper()
    for brand in KNOWN_BRANDS:
        if brand.upper() in upper:
            return "Apple" if brand == "iPhone" else brand
    return None


def get_or_create_product(base_url, service_key, title, image_url):
    escaped = urllib.parse.quote(title, safe="")
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
            "brand": guess_brand(title),
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
        prefer="return=representation,resolution=merge-duplicates",
    )


async def run_load(spider, store_name, website_url, category_url, skip_no_price=True):
    load_env()
    base_url = os.environ["SUPABASE_URL"]
    service_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

    items = await spider.fetch_category(category_url)
    print(f"Scrapeados {len(items)} productos reales.")

    store_id = get_or_create_store(base_url, service_key, store_name, website_url)
    print(f"Store id: {store_id}")

    loaded = 0
    for item in items:
        if skip_no_price and item.price <= 0:
            print(f"Omitido (sin precio real): {item.title}")
            continue
        try:
            product_id = get_or_create_product(base_url, service_key, item.title, item.image_url)
            upsert_price(base_url, service_key, product_id, store_id, item)
            loaded += 1
        except Exception as exc:
            print(f"Error cargando '{item.title}': {exc}")

    print(f"Cargados {loaded}/{len(items)} productos en Supabase.")
