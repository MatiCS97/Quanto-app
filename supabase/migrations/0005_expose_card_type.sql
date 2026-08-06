-- Quanto — expone card_type (de bank_promotions) en best_price_today(),
-- para poder filtrar por banco Y tipo de tarjeta a la vez (ej. "Ueno +
-- crédito" debe mostrar solo promos que aplican a esa combinación).
-- Requiere haber corrido antes 0003_indirect_sources.sql y
-- 0004_expose_indirect_source.sql.

drop function if exists best_price_today(uuid);

create function best_price_today(p_product_id uuid)
returns table (
  store_id uuid,
  store_name text,
  base_price numeric,
  in_stock boolean,
  product_url text,
  bank_name text,
  card_type text,
  discount_percentage numeric,
  max_refund_amount numeric,
  final_price numeric,
  is_indirect_source boolean,
  source_note text
)
language sql
stable
as $$
  with today as (
    select trim(to_char(now(), 'Day')) as day_name
  ),
  candidate_promos as (
    select
      bp.store_id,
      bp.bank_name,
      bp.card_type,
      bp.discount_percentage,
      bp.max_refund_amount
    from bank_promotions bp, today
    where bp.active = true
      and today.day_name = any (bp.active_days)
  ),
  best_promo_per_store as (
    select
      store_id,
      bank_name,
      card_type,
      discount_percentage,
      max_refund_amount,
      row_number() over (
        partition by store_id
        order by discount_percentage desc
      ) as rnk
    from candidate_promos
  )
  select
    pp.store_id,
    s.name as store_name,
    pp.price as base_price,
    pp.in_stock,
    pp.product_url,
    bp.bank_name,
    bp.card_type,
    bp.discount_percentage,
    bp.max_refund_amount,
    case
      when bp.discount_percentage is null then pp.price
      else greatest(
        pp.price - least(
          pp.price * (bp.discount_percentage / 100.0),
          coalesce(bp.max_refund_amount, pp.price)
        ),
        0
      )
    end as final_price,
    s.is_indirect_source,
    s.source_note
  from product_prices pp
  join stores s on s.id = pp.store_id
  left join best_promo_per_store bp on bp.store_id = pp.store_id and bp.rnk = 1
  where pp.product_id = p_product_id
  order by final_price asc;
$$;

comment on function best_price_today(uuid) is
  'Devuelve precio base y precio final (con mejor promo bancaria activa hoy) por cada tienda que vende el producto, incluyendo tipo de tarjeta de la promo y si la fuente es indirecta.';
