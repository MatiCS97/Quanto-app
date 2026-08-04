-- Datos mínimos de prueba para desarrollo local.
-- NO ejecutar en producción.

insert into stores (name, website_url, logo_url) values
  ('Punto Store', 'https://www.puntostore.com.py', null),
  ('Electrofacil', 'https://www.electrofacil.com.py', null)
on conflict (name) do nothing;

insert into products (name, brand, model, category, main_image_url)
values ('iPhone 15 128GB', 'Apple', 'iPhone 15', 'celulares', null)
returning id;

-- Nota: en un seed real, encadenar los ids devueltos arriba.
-- Este archivo se piensa como plantilla para el script de carga,
-- no como fixture completo con ids fijos.

insert into bank_promotions (store_id, bank_name, card_type, discount_percentage, max_refund_amount, active_days, terms, active)
select
  s.id,
  'Ueno Bank',
  'credito',
  20,
  500000,
  array['Tuesday'],
  'Tope de reintegro Gs. 500.000 por transacción. Válido los martes.',
  true
from stores s where s.name = 'Punto Store';
