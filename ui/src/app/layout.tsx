import type { Metadata } from "next";
import { Orbitron, Inter, Geist_Mono } from "next/font/google";
import AppShell from "@/components/app-shell";
import NovaProvider from "@/components/nova-provider";
import "./globals.css";

const orbitron = Orbitron({
  variable: "--font-hud",
  subsets: ["latin"],
  weight: ["500", "700", "900"],
});

const inter = Inter({
  variable: "--font-body",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "NOVA",
  description: "Nova personal assistant — HUD dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`dark ${orbitron.variable} ${inter.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="scanlines h-full w-full">
        <NovaProvider>
          <AppShell>{children}</AppShell>
        </NovaProvider>
      </body>
    </html>
  );
}
