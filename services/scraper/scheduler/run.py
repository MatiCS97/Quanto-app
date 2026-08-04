import asyncio
import logging
import os

from apscheduler.schedulers.blocking import BlockingScheduler
from supabase import create_client

from spiders.example_store_spider import ExampleStoreSpider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("quanto.scraper")

SPIDERS = [ExampleStoreSpider()]


def get_client():
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])


async def run_spider(spider, client):
    store = client.table("stores").select("id").eq("name", spider.store_name).single().execute()
    if not store.data:
        logger.warning("Tienda '%s' no existe en la tabla stores, se omite.", spider.store_name)
        return

    store_id = store.data["id"]

    try:
        items = await spider.fetch_category(spider.base_url)
    except Exception:
        logger.exception("Spider '%s' falló — probable selector CSS roto.", spider.store_name)
        return

    for item in items:
        # upsert simplificado: en producción, primero resolver/crear el
        # product_id por matching de título+marca antes de este paso.
        logger.info("Scrapeado: %s — Gs. %.0f", item.title, item.price)

    logger.info("Spider '%s': %d items procesados.", spider.store_name, len(items))


def job():
    client = get_client()
    for spider in SPIDERS:
        asyncio.run(run_spider(spider, client))


def main():
    scheduler = BlockingScheduler()
    scheduler.add_job(job, "interval", hours=24, next_run_time=None)
    logger.info("Scheduler iniciado — corrida cada 24h.")
    job()  # primera corrida inmediata
    scheduler.start()


if __name__ == "__main__":
    main()
