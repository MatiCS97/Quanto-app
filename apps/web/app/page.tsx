import { supabase } from "../lib/supabase";

type Product = {
  id: string;
  name: string;
  main_image_url: string | null;
};

type BestPriceRow = {
  store_id: string;
  store_name: string;
  base_price: number;
  in_stock: boolean;
  product_url: string;
  bank_name: string | null;
  discount_percentage: number | null;
  max_refund_amount: number | null;
  final_price: number;
};

type ProductWithBestPrice = Product & { best: BestPriceRow | null };

async function getProductsWithBestPrice(): Promise<ProductWithBestPrice[]> {
  const { data: products, error } = await supabase
    .from("products")
    .select("id, name, main_image_url")
    .limit(24);

  if (error || !products) {
    console.error(error);
    return [];
  }

  const withBest = await Promise.all(
    products.map(async (product) => {
      const { data: bestRows } = await supabase.rpc("best_price_today", {
        p_product_id: product.id,
      });
      const best = (bestRows as BestPriceRow[] | null)?.[0] ?? null;
      return { ...product, best };
    })
  );

  return withBest
    .filter((p) => p.best !== null)
    .sort((a, b) => (a.best!.final_price ?? 0) - (b.best!.final_price ?? 0));
}

function formatGs(value: number) {
  return "Gs. " + Number(value).toLocaleString("es-PY");
}

export default async function HomePage() {
  const products = await getProductsWithBestPrice();

  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: "48px 24px" }}>
      <div style={{ textAlign: "center", marginBottom: 40 }}>
        <img src="/brand/logo_fondo_blanco.png" alt="Quanto" style={{ width: "100%", maxWidth: 280 }} />
        <p style={{ color: "#5b5551", marginTop: 12 }}>
          Encontrá el mejor precio hoy, con tu banco.
        </p>
      </div>

      {products.length === 0 ? (
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
          {products.map((product) => {
            const best = product.best!;
            const hasDiscount = best.bank_name && best.final_price < best.base_price;

            return (
              <a
                key={product.id}
                href={best.product_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  border: "1px solid #e3ddd5",
                  borderRadius: 10,
                  padding: 14,
                  textDecoration: "none",
                  color: "#171412",
                  position: "relative",
                }}
              >
                {hasDiscount && (
                  <span
                    style={{
                      position: "absolute",
                      top: 10,
                      right: 10,
                      background: "#e34234",
                      color: "#fff",
                      fontSize: 11,
                      fontWeight: 700,
                      padding: "2px 8px",
                      borderRadius: 100,
                    }}
                  >
                    Hoy con {best.bank_name}
                  </span>
                )}
                {product.main_image_url && (
                  <img
                    src={product.main_image_url}
                    alt={product.name}
                    style={{ width: "100%", height: 140, objectFit: "contain", marginBottom: 10 }}
                  />
                )}
                <p style={{ fontSize: 13, margin: "0 0 6px", lineHeight: 1.3 }}>{product.name}</p>

                {hasDiscount ? (
                  <>
                    <p style={{ fontWeight: 700, margin: "0 0 2px", color: "#e34234" }}>
                      {formatGs(best.final_price)}
                    </p>
                    <p
                      style={{
                        fontSize: 12,
                        margin: "0 0 4px",
                        color: "#5b5551",
                        textDecoration: "line-through",
                      }}
                    >
                      {formatGs(best.base_price)}
                    </p>
                  </>
                ) : (
                  <p style={{ fontWeight: 700, margin: "0 0 4px" }}>{formatGs(best.base_price)}</p>
                )}

                <p style={{ fontSize: 12, color: "#5b5551", margin: 0 }}>{best.store_name}</p>
              </a>
            );
          })}
        </div>
      )}
    </main>
  );
}
