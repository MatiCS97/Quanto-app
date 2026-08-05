import "./globals.css";

export const metadata = {
  title: "Quanto",
  description: "Encontrá el mejor precio hoy, con tu banco.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
