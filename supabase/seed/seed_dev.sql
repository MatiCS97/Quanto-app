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

-- Promo bancaria REAL y VIGENTE, verificada en fuente oficial:
-- Banco GNB Paraguay, "Potenciá tus estudios Universitarios" —
-- 15% de reintegro con Mastercard crédito/prepaga, tope Gs. 1.500.000,
-- compra máxima Gs. 10.000.000, del día 1 al 10 de cada mes.
-- Vigencia de campaña: 01/03/2026 al 10/12/2026.
-- Fuente: beneficiosbancognb.com.py/beneficios/426/
--
-- No está atada a un comercio específico (aplica a cualquier compra con
-- Mastercard GNB), por eso se carga para todas las tiendas existentes.
--
-- Limitación de esquema: active_days sólo modela días de la semana, no
-- rango de días del mes. Como la ventana real (1-10) incluye la fecha
-- de hoy, se carga con todos los días de semana para que el efecto sea
-- correcto ahora — pero el rango real "1 al 10 de cada mes" queda
-- documentado en terms. Si se reactiva este seed en otro momento del
-- mes, revisar terms antes de asumir que sigue vigente.
insert into bank_promotions (store_id, bank_name, card_type, discount_percentage, max_refund_amount, active_days, terms, active)
select
  s.id,
  'GNB',
  'ambas',
  15,
  1500000,
  array['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'],
  'Reintegro 15% con Mastercard crédito/prepaga GNB, tope Gs. 1.500.000, compra máxima Gs. 10.000.000, válido del día 1 al 10 de cada mes. Campaña vigente 01/03/2026 al 10/12/2026. No aplicar fuera de esa ventana de días del mes sin volver a verificar. Fuente: beneficiosbancognb.com.py/beneficios/426/',
  true
from stores s;
