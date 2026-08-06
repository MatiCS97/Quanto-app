import "./globals.css";
import { Analytics } from '@vercel/analytics/next';
import ChatWidget from "./ChatWidget";

export const metadata = {
  title: "Quanto",
  description: "Encontrá el mejor precio hoy, con tu banco.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>
        {children}
        <ChatWidget />
        <Analytics />
      </body>
    </html>
  );
}
