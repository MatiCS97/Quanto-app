import SearchableProductGrid from "./SearchableProductGrid";

export default function HomePage() {
  return (
    <>
      <header
        style={{
          borderBottom: "1px solid var(--color-border)",
          background: "var(--color-surface)",
        }}
      >
        <div
          style={{
            maxWidth: 1120,
            margin: "0 auto",
            padding: "12px 24px",
            display: "flex",
            alignItems: "center",
            gap: 20,
          }}
        >
          <img
            src="/brand/logo_fondo_blanco.png"
            alt="Quanto"
            style={{ height: 88, width: "auto", display: "block" }}
          />
          <span
            style={{
              fontSize: 13,
              color: "var(--color-text-muted)",
              borderLeft: "1px solid var(--color-border-strong)",
              paddingLeft: 20,
            }}
          >
            Encontrá el mejor precio hoy, con tu banco
          </span>
        </div>
      </header>

      <main style={{ maxWidth: 1120, margin: "0 auto", padding: "40px 24px 80px" }}>
        <SearchableProductGrid />
      </main>
    </>
  );
}
