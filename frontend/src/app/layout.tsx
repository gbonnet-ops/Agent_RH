import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Agent RH",
  description: "Agent IA de recherche d'emploi automatisée",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr">
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
