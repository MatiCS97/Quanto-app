-- Datos de referencia para desarrollo.
-- NO ejecutar en producción sin revisar.
--
-- NOTA: la tienda 'Mega Electronicos' y sus productos/precios reales se
-- cargan con services/scraper/scripts/load_mega_electronicos.py, no acá.
-- Este archivo solo agrega una promo bancaria de EJEMPLO.

-- Promo bancaria de referencia (INACTIVA a propósito).
--
-- Patrón real observado en promociones de Itaú Paraguay ("todos los
-- martes", X% con tope en Gs., varias campañas de 2025 verificadas en
-- PDFs oficiales), pero NO se pudo verificar una promoción vigente para
-- HOY (agosto 2026) sin acceso a un documento de campaña actual — los
-- bancos paraguayos publican bases y condiciones por campaña mensual/
-- estacional, no una promo permanente. Confirma el riesgo de
-- mantenimiento manual sostenido documentado en el plan de producto.
--
-- active=false a propósito: no representar esto como una promo real
-- vigente. Sirve para probar que best_price_today() funciona con la
-- forma real de un dato de este tipo.
insert into bank_promotions (store_id, bank_name, card_type, discount_percentage, max_refund_amount, active_days, terms, active)
select
  s.id,
  'Itaú',
  'ambas',
  25,
  1000000,
  array['Tuesday'],
  'EJEMPLO NO VERIFICADO PARA HOY. Patrón real de campaña Itaú 2025 ("todos los martes", descuento con tope Gs. 1.000.000). No se confirmó vigencia para la fecha actual — reemplazar por una promo verificada antes de usar en producción.',
  false
from stores s where s.name = 'Mega Electronicos';
