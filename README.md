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

## Deploy del frontend (Vercel)

El frontend (`apps/web`) es lo único pensado para Vercel — el backend FastAPI y el scraper con Playwright necesitan un proceso de larga duración (scheduler 24hs) que no encaja en funciones serverless, y viven aparte (Railway/Fly.io/VPS).

1. Pushear este repo a GitHub.
2. En [vercel.com/new](https://vercel.com/new), importar el repo.
3. En la configuración del proyecto, fijar **Root Directory** en `apps/web` (Vercel detecta Next.js automáticamente ahí).
4. Agregar las variables de entorno `NEXT_PUBLIC_SUPABASE_URL` y `NEXT_PUBLIC_SUPABASE_ANON_KEY` (ver `.env.example`) en Project Settings → Environment Variables.
5. Cada push a `master` dispara un deploy de producción; cada PR, un preview.
