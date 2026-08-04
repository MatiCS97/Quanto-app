from fastapi import APIRouter
from pydantic import BaseModel

from services.supabase_client import get_client

router = APIRouter()


class CreateAlert(BaseModel):
    user_id: str
    product_id: str
    target_price: float


@router.post("")
def create_alert(payload: CreateAlert):
    client = get_client()
    result = client.table("user_alerts").insert(payload.model_dump()).execute()
    return result.data


@router.get("/{user_id}")
def list_alerts(user_id: str):
    client = get_client()
    result = client.table("user_alerts").select("*").eq("user_id", user_id).execute()
    return result.data
