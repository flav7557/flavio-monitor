import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Market Terminal",
  description: "Personal market monitoring powered by London Strategic Edge.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
