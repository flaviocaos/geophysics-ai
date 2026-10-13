import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Geophysics AI",
  description: "Redução e interpretação de dados geofísicos de campo — gravimetria, magnetometria, eletrorresistividade e sísmica de refração",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
