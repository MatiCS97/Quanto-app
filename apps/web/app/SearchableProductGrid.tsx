"use client";

import { useEffect, useState, useTransition } from "react";
import { getLatestProducts, searchProducts, ProductWithBestPrice } from "./actions";

function formatGs(value: number) {
  return "Gs. " + Number(value).toLocaleString("es-PY");
}

export default function SearchableProductGrid() {
  const [query, setQuery] = useState("");
  const [products, setProducts] = useState<ProductWithBestPrice[]>([]);
  const [isPending, startTransition] = useTransition();
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    getLatestProducts().then((data) => {
      setProducts(data);
      setLoaded(true);
    });
  }, []);

  useEffect(() => {
    const handle = setTimeout(() => {
      startTransition(() => {
        if (query.trim().length < 2) {
          getLatestProducts().then(setProducts);
        } else {
          searchProducts(query).then(setProducts);
        }
      });
    }, 300);
    return () => clearTimeout(handle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  return (
    <>
      <div style={{ marginBottom: 28 }}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Buscar producto (ej. Xiaomi Redmi)"
          style={{
            width: "100%",
            padding: "12px 16px",
            fontSize: 15,
            border: "1px solid #e3ddd5",
            borderRadius: 10,
            outline: "none",
          }}
        />
      </div>

      {!loaded ? (
        <p style={{ textAlign: "center", color: "#5b5551" }}>Cargando…</p>
      ) : products.length === 0 ? (
        <p style={{ textAlign: "center", color: "#5b5551" }}>
          {query.trim().length >= 2
            ? "No encontramos productos con ese nombre."
            : "Todavía no hay productos cargados."}
        </p>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
            gap: 16,
            opacity: isPending ? 0.6 : 1,
            transition: "opacity 150ms",
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
    </>
  );
}
