"use client";

import { AgentChat } from "@/components/AgentChat";
import { FeatureGuide } from "@/components/FeatureGuide";

export default function AskPage() {
  return (
    <main className="shell ask-page">
      <header className="page-header">
        <h1>Ask</h1>
        <p className="lede">
          Type like you’d text a thoughtful cook. We’ll route you to the right
          station — learn, diagnose, cook, substitute, and more.
        </p>
      </header>

      <AgentChat />

      <FeatureGuide
        title="How Ask works"
        summary="Type a cooking question in everyday language. KitchenLab figures out what you need, then uses the right tool — like stations in a kitchen."
        when="Use Ask whenever you’re curious, stuck, planning dinner, or diagnosing a failed dish. You don’t need science vocabulary."
        steps={[
          "Type a question or tap an example below the box.",
          "Read Action (what to do), Reason (why), and Science (the idea behind it).",
          "Check Sources — claims point back to cited knowledge when available.",
          "Sign in under My kitchen to personalize answers and keep Ask history (reopen past chats from the sidebar).",
        ]}
        terms={[
          {
            term: "Modes (behind the scenes)",
            meaning:
              "Learn = explain science. Cook = invent a recipe. Adapt = fix a recipe you paste. Diagnose = troubleshoot a failure. Substitute = swap an ingredient. Experiment = design a fair kitchen test.",
          },
          {
            term: "Why not just ChatGPT?",
            meaning:
              "Critical numbers and safety (like meat temperatures) come from code and curated sources. The AI only explains and personalizes — it doesn’t invent food-safety facts.",
          },
          {
            term: "Want a full recipe?",
            meaning:
              "Use the Recipes page for a complete dish with Why + Science on every step, plus a personal cookbook when you’re signed in.",
          },
        ]}
      />
    </main>
  );
}
