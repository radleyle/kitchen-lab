"use client";

import { AgentChat } from "@/components/AgentChat";

export default function Home() {
  return (
    <main className="shell">
      <header className="hero">
        <p className="brand">KitchenLab</p>
        <h1 className="tagline">Cook better through science.</h1>
        <p className="lede">
          Ask a question. Grounded answers — calculators and cited knowledge,
          not LLM guesswork.
        </p>
      </header>

      <section className="dining-room" aria-label="Ask KitchenLab">
        <AgentChat />
      </section>
    </main>
  );
}
