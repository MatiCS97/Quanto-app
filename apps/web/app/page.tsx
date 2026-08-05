import { supabase } from "../lib/supabase";

type PriceRow = {
  price: number;
  product_url: string;
  products: { name: string; brand: string | null; main_image_url: string | null } | null;
  stores: { name: string } | null;
};

async function getPrices(): Promise<PriceRow[]> {
  const { data, error } = await supabase
    .from("product_prices")
    .select("price, product_url, products(name, brand, main_image_url), stores(name)")
    .order("price", { ascending: true })
    .limit(24);

  if (error) {
    console.error(error);
    return [];
  }
  return (data as unknown as PriceRow[]) ?? [];
}

export default async function HomePage() {
  const prices = await getPrices();

  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: "48px 24px" }}>
      <div style={{ textAlign: "center", marginBottom: 40 }}>
        <img src="/brand/logo_fondo_blanco.png" alt="Quanto" style={{ width: "100%", maxWidth: 280 }} />
        <p style={{ color: "#5b5551", marginTop: 12 }}>
          Encontrá el mejor precio hoy, con tu banco.
        </p>
      </div>

      {prices.length === 0 ? (
        <p style={{ textAlign: "center", color: "#5b5551" }}>
          Todavía no hay productos cargados.
        </p>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
            gap: 16,
          }}
        >
          {prices.map((row, i) => (
            <a
              key={i}
              href={row.product_url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                border: "1px solid #e3ddd5",
                borderRadius: 10,
                padding: 14,
                textDecoration: "none",
                color: "#171412",
              }}
            >
              {row.products?.main_image_url && (
                <img
                  src={row.products.main_image_url}
                  alt={row.products?.name ?? ""}
                  style={{ width: "100%", height: 140, objectFit: "contain", marginBottom: 10 }}
                />
              )}
              <p style={{ fontSize: 13, margin: "0 0 6px", lineHeight: 1.3 }}>
                {row.products?.name}
              </p>
              <p style={{ fontWeight: 700, margin: "0 0 4px" }}>
                Gs. {Number(row.price).toLocaleString("es-PY")}
              </p>
              <p style={{ fontSize: 12, color: "#5b5551", margin: 0 }}>
                {row.stores?.name}
              </p>
            </a>
          ))}
        </div>
      )}
    </main>
  );
}
