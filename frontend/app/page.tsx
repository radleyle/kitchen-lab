"use client";
// "use client" means this component runs in the browser (it uses state and
// fetches data on the user's machine). Server components can't do that.

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Check = { label: string; ok: boolean | null; detail: string };

export default function Home() {
  // Track the status of each link in the chain: backend, then database.
  const [checks, setChecks] = useState<Check[]>([
    { label: "Backend (FastAPI)", ok: null, detail: "checking..." },
    { label: "Database (Postgres)", ok: null, detail: "checking..." },
  ]);

  useEffect(() => {
    async function probe(path: string, index: number) {
      try {
        const res = await fetch(`${API_URL}${path}`);
        const body = await res.json();
        setChecks((prev) =>
          prev.map((c, i) =>
            i === index
              ? { ...c, ok: res.ok, detail: JSON.stringify(body) }
              : c,
          ),
        );
      } catch (err) {
        setChecks((prev) =>
          prev.map((c, i) =>
            i === index ? { ...c, ok: false, detail: String(err) } : c,
          ),
        );
      }
    }
    probe("/health", 0);
    probe("/health/db", 1);
  }, []);

  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: "4rem 1.5rem" }}>
      <h1 style={{ fontSize: "2.25rem", marginBottom: "0.25rem" }}>
        KitchenLab
      </h1>
      <p style={{ color: "#9a9791", marginTop: 0 }}>
        Cook better through science.
      </p>

      <section
        style={{
          marginTop: "2.5rem",
          border: "1px solid #23262e",
          borderRadius: 12,
          padding: "1.25rem 1.5rem",
          background: "#151821",
        }}
      >
        <h2 style={{ fontSize: "1rem", color: "#9a9791", marginTop: 0 }}>
          System status
        </h2>
        {checks.map((c) => (
          <div
            key={c.label}
            style={{
              display: "flex",
              alignItems: "baseline",
              gap: "0.75rem",
              padding: "0.5rem 0",
            }}
          >
            <span style={{ fontSize: "1.1rem" }}>
              {c.ok === null ? "…" : c.ok ? "✅" : "❌"}
            </span>
            <span style={{ fontWeight: 600 }}>{c.label}</span>
            <code style={{ color: "#6f6c66", fontSize: "0.8rem" }}>
              {c.detail}
            </code>
          </div>
        ))}
      </section>
    </main>
  );
}
