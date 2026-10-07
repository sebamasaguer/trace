import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "ReciclaTrace",
  description: "Trazabilidad digital de reciclaje"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="es"><body>{children}</body></html>;
}
