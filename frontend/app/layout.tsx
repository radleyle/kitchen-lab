import type { Metadata } from "next";
import type { ReactNode } from "react";
import { DM_Sans, Syne } from "next/font/google";
import { Providers } from "@/components/Providers";
import { SiteNav } from "@/components/SiteNav";
import "./globals.css";

// next/font downloads fonts at build time — no extra network request in the browser.
const syne = Syne({
  subsets: ["latin"],
  variable: "--font-syne",
  weight: ["600", "700", "800"],
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-dm-sans",
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "KitchenLab",
  description: "Cook better through science — grounded answers, not guesswork.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${syne.variable} ${dmSans.variable}`}>
      {/* Extensions (e.g. Grammarly) inject attributes onto <body> before
          React hydrates, which triggers a harmless mismatch warning. */}
      <body suppressHydrationWarning>
        <Providers>
          <SiteNav />
          {children}
        </Providers>
      </body>
    </html>
  );
}
