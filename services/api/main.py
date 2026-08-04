from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import products, prices, promotions, alerts, vision

app = FastAPI(title="Quanto API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ajustar a dominios reales antes de producción
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router, prefix="/products", tags=["products"])
app.include_router(prices.router, prefix="/prices", tags=["prices"])
app.include_router(promotions.router, prefix="/promotions", tags=["promotions"])
app.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
app.include_router(vision.router, prefix="/vision", tags=["vision"])


@app.get("/health")
def health():
    return {"status": "ok"}
