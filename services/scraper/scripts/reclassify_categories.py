"""Re-clasifica products.category por el nombre real del producto.

Cada script load_*.py carga productos nuevos con category="celulares"
fijo (ver get_or_create_product en _load_common.py) porque en su momento
no se anticipaba que las tiendas también vendieran accesorios, smartwatches,
notebooks, etc. Este script corrige eso re-derivando la categoría real a
partir del nombre y actualizando solo los productos cuyo category calculado
difiere del guardado.

Correr manualmente después de cargar una tienda nueva o de agregar
categorías/patrones nuevos:

    python scripts/reclassify_categories.py

Orden de patrones importa: se evalúa de arriba hacia abajo y se usa el
primer match. Por eso "funda_case" va antes de "celulares" (un
"Case Galaxy A36..." no debe caer en celular por mencionar el modelo).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _load_common import load_env, supabase_request

PATTERNS = [
    ("smartwatch", re.compile(r"smartwatch|reloj\s*inteligente|\bwatch\b", re.I)),
    ("funda_case", re.compile(r"\bcase\b|funda|protector|magsafe|clear\s*transparency|slip\s*cover|exfolio", re.I)),
    ("auricular", re.compile(r"auricular|airpod|earbud|earphone", re.I)),
    ("tablet", re.compile(r"\btablet\b|\bipad\b", re.I)),
    ("notebook", re.compile(r"notebook|laptop|\bportatil\b", re.I)),
    ("camara", re.compile(r"c[aá]mara\s*fotogr", re.I)),
    ("cargador", re.compile(r"cargador|power\s*adapter|power\s*bank|\bcable\b", re.I)),
    ("accesorio", re.compile(
        r"airtag|localizador|apple\s*pencil|tarjeta\s*de\s*memoria|micro\s*sd|memoria\s*sandisk|"
        r"soporte\b|tr[ií]pode|mouse|teclado|parlante|monitor\b|presentador|impresora|\bssd\b|"
        r"disco\s*(duro|s[oó]lido)|pendrive|memoria\s*ram\b",
        re.I,
    )),
    ("celulares", re.compile(
        r"celular|iphone|redmi|galaxy|smartphone|xiaomi|realme|honor|motorola|samsung|itel|"
        r"poco\b|tecno\b|infinix|fossibot|\boppo\b|\bnokia\b|\bvivo\b|\bnothing\b",
        re.I,
    )),
]

FALLBACK_CATEGORY = "celulares"


def classify(name: str) -> str:
    for category, pattern in PATTERNS:
        if pattern.search(name):
            return category
    return FALLBACK_CATEGORY


def main():
    load_env()
    base_url = os.environ["SUPABASE_URL"]
    service_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

    products = []
    offset = 0
    while True:
        batch = supabase_request(
            "GET", f"products?select=id,name,category&limit=1000&offset={offset}",
            base_url, service_key,
        )
        if not batch:
            break
        products.extend(batch)
        offset += len(batch)
        if len(batch) < 1000:
            break

    print(f"Total productos: {len(products)}")

    counts = {}
    updated = 0
    for p in products:
        new_category = classify(p["name"])
        counts[new_category] = counts.get(new_category, 0) + 1
        if new_category != p["category"]:
            supabase_request(
                "PATCH", f"products?id=eq.{p['id']}",
                base_url, service_key,
                payload={"category": new_category},
            )
            updated += 1

    print(f"Actualizados: {updated}")
    for cat, count in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
