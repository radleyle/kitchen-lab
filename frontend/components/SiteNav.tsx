"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useTheme } from "@/lib/theme";

const LINKS = [
  { href: "/ask", label: "Ask" },
  { href: "/recipes", label: "Recipes" },
  { href: "/lab", label: "Lab" },
  { href: "/calculators", label: "Calculators" },
  { href: "/kitchen", label: "My kitchen" },
] as const;

export function SiteNav() {
  const pathname = usePathname();
  const { user, logout, loading } = useAuth();
  const { theme, toggle, ready } = useTheme();
  const onHome = pathname === "/";

  return (
    <nav
      className={onHome ? "site-nav site-nav--over-hero" : "site-nav"}
      aria-label="Main"
    >
      <Link href="/" className="nav-brand">
        KitchenLab
      </Link>
      {LINKS.map((link) => (
        <Link
          key={link.href}
          href={link.href}
          className={pathname === link.href ? "active" : undefined}
        >
          {link.label}
        </Link>
      ))}
      <button
        type="button"
        className="theme-toggle"
        onClick={toggle}
        aria-label={
          theme === "light" ? "Switch to dark mode" : "Switch to light mode"
        }
        title={theme === "light" ? "Dark mode" : "Light mode"}
      >
        {ready ? (theme === "light" ? "Dark" : "Light") : "Theme"}
      </button>
      {!loading && user && (
        <button type="button" className="nav-logout" onClick={logout}>
          Sign out
        </button>
      )}
      {!loading && user && (
        <span className="nav-user" title={user.email}>
          {user.display_name || user.email}
        </span>
      )}
    </nav>
  );
}
