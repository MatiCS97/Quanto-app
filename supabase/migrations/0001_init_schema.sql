-- Quanto — esquema inicial
-- Ejecutar en Supabase SQL editor o vía `supabase db push`

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------------
-- stores
-- ---------------------------------------------------------------------------
create table if not exists stores (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  website_url text not null,
  logo_url text,
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- products
-- ---------------------------------------------------------------------------
create table if not exists products (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  brand text,
  model text,
  category text not null,
  main_image_url text,
  created_at timestamptz not null default now()
);

create index if not exists idx_products_category on products (category);
create index if not exists idx_products_brand on products (brand);
-- búsqueda de texto simple sobre nombre/marca/modelo
create index if not exists idx_products_search on products
  using gin (to_tsvector('spanish', coalesce(name,'') || ' ' || coalesce(brand,'') || ' ' || coalesce(model,'')));

-- ---------------------------------------------------------------------------
-- product_prices
-- ---------------------------------------------------------------------------
create table if not exists product_prices (
  id uuid primary key default gen_random_uuid(),
  product_id uuid not null references products (id) on delete cascade,
  store_id uuid not null references stores (id) on delete cascade,
  price numeric(14,2) not null check (price >= 0),
  original_price numeric(14,2) check (original_price >= 0),
  product_url text not null,
  in_stock boolean not null default true,
  last_updated timestamptz not null default now(),
  unique (product_id, store_id, product_url)
);

create index if not exists idx_prices_product on product_prices (product_id);
create index if not exists idx_prices_store on product_prices (store_id);
create index if not exists idx_prices_last_updated on product_prices (last_updated);

-- ---------------------------------------------------------------------------
-- bank_promotions
-- active_days usa nombres de día en inglés ('Monday'..'Sunday') para que
-- coincida directo con to_char(now(), 'Day') trim() en el motor de cálculo.
-- ---------------------------------------------------------------------------
create table if not exists bank_promotions (
  id uuid primary key default gen_random_uuid(),
  store_id uuid references stores (id) on delete cascade,
  bank_name text not null,
  card_type text not null check (card_type in ('credito', 'debito', 'ambas')),
  discount_percentage numeric(5,2) not null check (discount_percentage >= 0 and discount_percentage <= 100),
  max_refund_amount numeric(14,2),
  active_days text[] not null default array[]::text[],
  terms text,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create index if not exists idx_promos_store on bank_promotions (store_id);
create index if not exists idx_promos_bank on bank_promotions (bank_name);
create index if not exists idx_promos_active on bank_promotions (active) where active = true;

-- ---------------------------------------------------------------------------
-- user_alerts
-- ---------------------------------------------------------------------------
create table if not exists user_alerts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  product_id uuid not null references products (id) on delete cascade,
  target_price numeric(14,2) not null check (target_price >= 0),
  created_at timestamptz not null default now(),
  unique (user_id, product_id)
);

create index if not exists idx_alerts_user on user_alerts (user_id);
create index if not exists idx_alerts_product on user_alerts (product_id);

-- ---------------------------------------------------------------------------
-- Row Level Security
-- stores / products / product_prices / bank_promotions: lectura pública,
-- escritura solo desde el backend (service role, que bypassea RLS).
-- user_alerts: cada usuario solo ve y gestiona las suyas.
-- ---------------------------------------------------------------------------
alter table stores enable row level security;
alter table products enable row level security;
alter table product_prices enable row level security;
alter table bank_promotions enable row level security;
alter table user_alerts enable row level security;

create policy "stores_public_read" on stores for select using (true);
create policy "products_public_read" on products for select using (true);
create policy "prices_public_read" on product_prices for select using (true);
create policy "promotions_public_read" on bank_promotions for select using (true);

create policy "alerts_owner_select" on user_alerts for select using (auth.uid() = user_id);
create policy "alerts_owner_insert" on user_alerts for insert with check (auth.uid() = user_id);
create policy "alerts_owner_update" on user_alerts for update using (auth.uid() = user_id);
create policy "alerts_owner_delete" on user_alerts for delete using (auth.uid() = user_id);
