# Quanto

Comparador de precios con búsqueda visual y motor de promociones bancarias, enfocado en Paraguay.

## Estructura

```
quanto/
├── apps/web/          # Next.js PWA — frontend
├── services/api/      # FastAPI — backend
├── services/scraper/  # Playwright/Httpx — ingesta de precios
├── supabase/          # migrations + seed SQL
├── packages/shared-types/
└── docs/
```

## Plan de producto

Estudio de mercado, monetización, proyección de ingresos y roadmap de desarrollo completos: ver el documento publicado en la conversación (`quanto_plan.html`), o `docs/` una vez exportado.

## Primer arranque local

1. Crear proyecto en [supabase.com](https://supabase.com), copiar credenciales a `.env` (basado en `.env.example`).
2. Aplicar migraciones: `supabase db push` (o pegar el contenido de `supabase/migrations/*.sql` en el SQL editor de Supabase, en orden).
3. Backend: `cd services/api && pip install -r requirements.txt && uvicorn main:app --reload`
4. Frontend: `cd apps/web && npm install && npm run dev`
5. Scraper: `cd services/scraper && pip install -r requirements.txt && python -m scheduler.run`

Cada carpeta tiene su propio README con detalle.
