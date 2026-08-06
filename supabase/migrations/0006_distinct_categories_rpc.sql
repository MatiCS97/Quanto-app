-- Quanto — RPC para traer las categorías distintas de products sin
-- depender del límite default de PostgREST (1000 filas por select).
-- El catálogo superó esa cantidad (1436 productos al 06/08/2026) y el
-- dropdown de categorías en el frontend empezó a perder categorías
-- reales (notebook, smartwatch, tablet) porque select("category") sin
-- límite explícito solo trae las primeras 1000 filas.
create function distinct_product_categories()
returns table (category text)
language sql
stable
as $$
  select distinct category from products order by category;
$$;

comment on function distinct_product_categories() is
  'Categorías distintas de productos, vía SQL DISTINCT — evita el límite de 1000 filas de PostgREST al traer todas las filas de products solo para deduplicar en el cliente.';
