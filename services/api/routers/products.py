from fastapi import APIRouter, Query

from services.supabase_client import get_client

router = APIRouter()


@router.get("/search")
def search_products(q: str = Query(..., min_length=2)):
    client = get_client()
    result = (
        client.table("products")
        .select("*")
        .text_search("name", q)
        .limit(20)
        .execute()
    )
    return result.data


@router.get("/{product_id}")
def get_product(product_id: str):
    client = get_client()
    result = client.table("products").select("*").eq("id", product_id).single().execute()
    return result.data
