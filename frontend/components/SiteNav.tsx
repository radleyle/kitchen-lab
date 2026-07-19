"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";

export function SiteNav() {
  const pathname = usePathname();
  const { user, logout, loading } = useAuth();

  return (
    <nav className="site-nav" aria-label="Main">
      <Link href="/" className={pathname === "/" ? "active" : undefined}>
        Ask
      </Link>
      <Link
        href="/lab"
        className={pathname === "/lab" ? "active" : undefined}
      >
        Lab
      </Link>
      <Link
        href="/kitchen"
        className={pathname === "/kitchen" ? "active" : undefined}
      >
        My kitchen
      </Link>
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
