-- Quanto — marca de tiendas cuya fuente de datos es indirecta (ej. Nissei
-- y VisãoVIP vía Compras Paraguai, porque bloquean scraping directo).
--
-- Antes esto se representaba metiendo un aviso de texto dentro del nombre
-- del producto ("... [PRECIO EN USD, NO Gs.]"), lo cual ensuciaba el dato
-- y no era reutilizable entre tiendas. Se mueve a nivel de tienda, que es
-- donde realmente vive esta propiedad.

alter table stores
  add column if not exists is_indirect_source boolean not null default false;

alter table stores
  add column if not exists source_note text;

comment on column stores.is_indirect_source is
  'true si los precios de esta tienda se obtienen via un agregador de terceros en vez de scraping directo (ej. bloqueo Cloudflare en el sitio real). Afecta cómo se muestra la tienda en la UI (aviso de frescura/fuente indirecta).';

comment on column stores.source_note is
  'Texto corto opcional mostrado en la UI cuando is_indirect_source=true, ej. "Precio convertido de USD, vía agregador de terceros".';

update stores
set is_indirect_source = true,
    source_note = 'Precio convertido de USD a Gs. (cotización referencial BCP), obtenido vía un agregador de terceros porque el sitio original bloquea el acceso directo.'
where name in ('Nissei', 'VisãoVIP');
