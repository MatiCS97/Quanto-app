-- Quanto — motor de cálculo de "precio final hoy"
-- Dada la fecha actual, devuelve por cada (producto, tienda) el precio base
-- y el mejor descuento bancario vigente hoy, si existe.

create or replace function best_price_today(p_product_id uuid)
returns table (
  store_id uuid,
  store_name text,
  base_price numeric,
  in_stock boolean,
  product_url text,
  bank_name text,
  discount_percentage numeric,
  max_refund_amount numeric,
  final_price numeric
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
    end as final_price
  from product_prices pp
  join stores s on s.id = pp.store_id
  left join best_promo_per_store bp on bp.store_id = pp.store_id and bp.rnk = 1
  where pp.product_id = p_product_id
  order by final_price asc;
$$;

comment on function best_price_today(uuid) is
  'Devuelve precio base y precio final (con mejor promo bancaria activa hoy) por cada tienda que vende el producto.';
