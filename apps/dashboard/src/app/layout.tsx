import "@/styles/globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "TrustAI Dashboard",
  description: "TrustAI verification dashboard",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
