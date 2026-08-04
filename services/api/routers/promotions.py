from fastapi import APIRouter

from services.supabase_client import get_client

router = APIRouter()


@router.get("/active")
def list_active_promotions():
    client = get_client()
    result = client.table("bank_promotions").select("*").eq("active", True).execute()
    return result.data
