from fastapi import APIRouter

from services.supabase_client import get_client

router = APIRouter()


@router.get("/{product_id}/best-today")
def best_price_today(product_id: str):
    """Precio base y precio final (con mejor promo bancaria vigente hoy) por tienda.

    Llama a la función SQL `best_price_today` definida en
    supabase/migrations/0002_pricing_engine.sql.
    """
    client = get_client()
    result = client.rpc("best_price_today", {"p_product_id": product_id}).execute()
    return result.data
