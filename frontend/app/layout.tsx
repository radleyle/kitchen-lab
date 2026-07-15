// The root layout wraps every page of the site (like a page template).
// In Next.js App Router, files in app/ map to URLs: app/page.tsx is "/".
import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "KitchenLab",
  description: "Cook better through science",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          fontFamily:
            "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
          background: "#0f1115",
          color: "#e8e6e3",
          minHeight: "100vh",
        }}
      >
        {children}
      </body>
    </html>
  );
}
