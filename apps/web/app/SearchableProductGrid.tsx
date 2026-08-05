"use client";

import { useEffect, useState, useTransition } from "react";
import { getLatestProducts, searchProducts, ProductWithBestPrice } from "./actions";

function formatGs(value: number) {
  return "Gs. " + Math.round(Number(value)).toLocaleString("es-PY");
}

function effectiveDiscountPct(basePrice: number, finalPrice: number) {
  if (basePrice <= 0) return 0;
  return Math.round(((basePrice - finalPrice) / basePrice) * 100);
}

function SearchIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function ProductCardSkeleton() {
  return (
    <div
      style={{
        borderRadius: "var(--radius-md)",
        border: "1px solid var(--color-border)",
        background: "var(--color-surface)",
        padding: 16,
      }}
    >
      <div style={{ height: 160, borderRadius: "var(--radius-sm)", background: "var(--color-border)", opacity: 0.6 }} />
      <div style={{ height: 12, marginTop: 14, width: "85%", borderRadius: 4, background: "var(--color-border)" }} />
      <div style={{ height: 12, marginTop: 8, width: "60%", borderRadius: 4, background: "var(--color-border)" }} />
      <div style={{ height: 20, marginTop: 14, width: "45%", borderRadius: 4, background: "var(--color-border)" }} />
    </div>
  );
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
      <div style={{ marginBottom: 36 }}>
        <div
          style={{
            position: "relative",
            maxWidth: 640,
            margin: "0 auto",
          }}
        >
          <span
            style={{
              position: "absolute",
              left: 18,
              top: "50%",
              transform: "translateY(-50%)",
              color: "var(--color-text-muted)",
              display: "flex",
            }}
          >
            <SearchIcon />
          </span>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar producto, ej. Xiaomi Redmi Note"
            style={{
              width: "100%",
              padding: "16px 18px 16px 48px",
              fontSize: 16,
              border: "1px solid var(--color-border-strong)",
              borderRadius: "var(--radius-lg)",
              outline: "none",
              background: "var(--color-surface)",
              color: "var(--color-text)",
              boxShadow: "var(--shadow-card)",
              transition: "border-color 150ms, box-shadow 150ms",
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = "var(--color-accent)";
              e.currentTarget.style.boxShadow = "0 0 0 3px var(--color-accent-tint)";
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = "var(--color-border-strong)";
              e.currentTarget.style.boxShadow = "var(--shadow-card)";
            }}
          />
        </div>
      </div>

      {!loaded ? (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(230px, 1fr))",
            gap: 20,
          }}
        >
          {Array.from({ length: 8 }).map((_, i) => (
            <ProductCardSkeleton key={i} />
          ))}
        </div>
      ) : products.length === 0 ? (
        <div style={{ textAlign: "center", padding: "60px 0", color: "var(--color-text-muted)" }}>
          <p style={{ fontSize: 15, margin: 0 }}>
            {query.trim().length >= 2
              ? `No encontramos productos para "${query.trim()}".`
              : "Todavía no hay productos cargados."}
          </p>
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(230px, 1fr))",
            gap: 20,
            opacity: isPending ? 0.55 : 1,
            transition: "opacity 150ms",
          }}
        >
          {products.map((product) => {
            const best = product.best!;
            const hasDiscount = Boolean(best.bank_name) && best.final_price < best.base_price;

            return (
              <a
                key={product.id}
                href={best.product_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: "flex",
                  flexDirection: "column",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-md)",
                  background: "var(--color-surface)",
                  padding: 16,
                  textDecoration: "none",
                  color: "var(--color-text)",
                  position: "relative",
                  boxShadow: "var(--shadow-card)",
                  transition: "box-shadow 180ms, transform 180ms, border-color 180ms",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.boxShadow = "var(--shadow-card-hover)";
                  e.currentTarget.style.transform = "translateY(-2px)";
                  e.currentTarget.style.borderColor = "var(--color-border-strong)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.boxShadow = "var(--shadow-card)";
                  e.currentTarget.style.transform = "translateY(0)";
                  e.currentTarget.style.borderColor = "var(--color-border)";
                }}
              >
                <div
                  style={{
                    position: "relative",
                    height: 160,
                    marginBottom: 14,
                    borderRadius: "var(--radius-sm)",
                    background: "var(--color-bg)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    overflow: "hidden",
                  }}
                >
                  {product.main_image_url && (
                    <img
                      src={product.main_image_url}
                      alt={product.name}
                      style={{ width: "100%", height: "100%", objectFit: "contain", padding: 10 }}
                    />
                  )}
                  {hasDiscount && (
                    <span
                      style={{
                        position: "absolute",
                        top: 10,
                        left: 10,
                        background: "var(--color-accent)",
                        color: "#fff",
                        fontSize: 11,
                        fontWeight: 700,
                        letterSpacing: "0.02em",
                        padding: "4px 10px",
                        borderRadius: 999,
                        boxShadow: "0 2px 6px rgba(229, 73, 59, 0.35)",
                      }}
                    >
                      -{effectiveDiscountPct(best.base_price, best.final_price)}% con {best.bank_name}
                    </span>
                  )}
                </div>

                <p
                  style={{
                    fontSize: 13.5,
                    lineHeight: 1.35,
                    margin: "0 0 10px",
                    color: "var(--color-text)",
                    minHeight: "2.7em",
                    display: "-webkit-box",
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: "vertical",
                    overflow: "hidden",
                  }}
                >
                  {product.name}
                </p>

                <div style={{ marginTop: "auto" }}>
                  {hasDiscount ? (
                    <>
                      <p
                        style={{
                          fontSize: 20,
                          fontWeight: 800,
                          letterSpacing: "-0.01em",
                          margin: "0 0 2px",
                          color: "var(--color-accent)",
                        }}
                      >
                        {formatGs(best.final_price)}
                      </p>
                      <p
                        style={{
                          fontSize: 12.5,
                          margin: "0 0 8px",
                          color: "var(--color-text-muted)",
                          textDecoration: "line-through",
                        }}
                      >
                        {formatGs(best.base_price)}
                      </p>
                    </>
                  ) : (
                    <p
                      style={{
                        fontSize: 20,
                        fontWeight: 800,
                        letterSpacing: "-0.01em",
                        margin: "0 0 8px",
                        color: "var(--color-text)",
                      }}
                    >
                      {formatGs(best.base_price)}
                    </p>
                  )}

                  <p
                    style={{
                      fontSize: 11.5,
                      fontWeight: 600,
                      letterSpacing: "0.03em",
                      textTransform: "uppercase",
                      color: "var(--color-text-muted)",
                      margin: 0,
                    }}
                  >
                    {best.store_name}
                  </p>
                </div>
              </a>
            );
          })}
        </div>
      )}
    </>
  );
}
