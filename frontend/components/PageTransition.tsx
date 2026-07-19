"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

/**
 * One short enter animation per route change — instead of every section
 * independently “rising in” (which feels stiff and slow).
 */
export function PageTransition({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <div key={pathname} className="page-enter">
      {children}
    </div>
  );
}
