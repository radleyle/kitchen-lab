import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Fraunces, Outfit } from "next/font/google";
import { PageTransition } from "@/components/PageTransition";
import { Providers } from "@/components/Providers";
import { SiteNav } from "@/components/SiteNav";
import "./globals.css";

// Fraunces = soft modern serif for brand/headlines (expressive, not Inter).
// Outfit = clean geometric sans for UI body.
const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-fraunces",
  weight: ["500", "600", "700", "800"],
});

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "KitchenLab",
  description: "Cook better through science — grounded answers, not guesswork.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="en"
      className={`${fraunces.variable} ${outfit.variable}`}
      suppressHydrationWarning
    >
      <head>
        {/* Apply saved theme before paint so dark mode doesn’t flash light. */}
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('kitchenlab_theme');if(t==='dark'||t==='light')document.documentElement.setAttribute('data-theme',t);}catch(e){}})();`,
          }}
        />
      </head>
      {/* Extensions (e.g. Grammarly) inject attributes onto <body> before
          React hydrates, which triggers a harmless mismatch warning. */}
      <body suppressHydrationWarning>
        <Providers>
          <SiteNav />
          <PageTransition>{children}</PageTransition>
        </Providers>
      </body>
    </html>
  );
}
