import SearchableProductGrid from "./SearchableProductGrid";

export default function HomePage() {
  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: "48px 24px" }}>
      <div style={{ textAlign: "center", marginBottom: 40 }}>
        <img src="/brand/logo_fondo_blanco.png" alt="Quanto" style={{ width: "100%", maxWidth: 280 }} />
        <p style={{ color: "#5b5551", marginTop: 12 }}>
          Encontrá el mejor precio hoy, con tu banco.
        </p>
      </div>

      <SearchableProductGrid />
    </main>
  );
}
