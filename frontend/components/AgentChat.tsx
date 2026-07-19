"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import {
  askAgent,
  concludeDiagnosis,
  type AgentResponse,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ResultView } from "./ResultView";

type Turn = {
  id: string;
  question: string;
  response: AgentResponse | null;
  error: string | null;
  /** Symptom slug from first diagnose pass, for conclude. */
  diagnoseSlug?: string;
};

const EXAMPLES = [
  "Why does bread get crusty?",
  "My roast chicken is dry — what went wrong?",
  "Generate a recipe for pan-seared salmon for 2",
  "I have eggs and butter — what can I make?",
  "Substitute buttermilk in pancakes",
];

export function AgentChat() {
  const { user } = useAuth();
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [diagnosing, setDiagnosing] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);

  async function submit(question: string) {
    const q = question.trim();
    if (!q || loading) return;

    const id = `${Date.now()}`;
    setTurns((t) => [{ id, question: q, response: null, error: null }, ...t]);
    setInput("");
    setLoading(true);

    try {
      const response = await askAgent(q);
      const result = response.result;
      const diagnoseSlug =
        response.mode === "diagnose" &&
        result &&
        typeof result === "object" &&
        (result as { symptom?: { slug?: string } }).symptom?.slug;

      setTurns((t) =>
        t.map((turn) =>
          turn.id === id
            ? {
                ...turn,
                response,
                diagnoseSlug: diagnoseSlug || undefined,
              }
            : turn,
        ),
      );
    } catch (err) {
      setTurns((t) =>
        t.map((turn) =>
          turn.id === id
            ? {
                ...turn,
                error: err instanceof Error ? err.message : "Request failed",
              }
            : turn,
        ),
      );
    } finally {
      setLoading(false);
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    await submit(input);
  }

  async function onDiagnoseAnswers(
    turnId: string,
    slug: string,
    description: string,
    answers: { question: string; answer: string }[],
  ) {
    setDiagnosing(true);
    try {
      const result = await concludeDiagnosis({
        symptom_slug: slug,
        description,
        answers,
      });
      setTurns((t) =>
        t.map((turn) =>
          turn.id === turnId && turn.response
            ? {
                ...turn,
                response: {
                  ...turn.response,
                  result,
                },
              }
            : turn,
        ),
      );
    } catch (err) {
      setTurns((t) =>
        t.map((turn) =>
          turn.id === turnId
            ? {
                ...turn,
                error: err instanceof Error ? err.message : "Diagnosis failed",
              }
            : turn,
        ),
      );
    } finally {
      setDiagnosing(false);
    }
  }

  return (
    <div className="agent">
      {user ? (
        <p className="auth-hint">
          Signed in — answers can use your{" "}
          <Link href="/kitchen">kitchen profile</Link>.
        </p>
      ) : (
        <p className="auth-hint muted">
          Anonymous mode.{" "}
          <Link href="/kitchen">Sign in</Link> to personalize oven / diet.
        </p>
      )}
      <form className="ask-form" onSubmit={onSubmit}>
        <label htmlFor="q" className="sr-only">
          Ask KitchenLab
        </label>
        <textarea
          id="q"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about cooking science, a failed dish, a recipe…"
          rows={3}
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          {loading ? "Thinking…" : "Ask"}
        </button>
      </form>

      {turns.length === 0 && (
        <div className="examples">
          <p className="examples-label">Try one</p>
          <ul>
            {EXAMPLES.map((ex) => (
              <li key={ex}>
                <button
                  type="button"
                  className="example-btn"
                  onClick={() => submit(ex)}
                  disabled={loading}
                >
                  {ex}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="turns">
        {turns.map((turn) => (
          <article key={turn.id} className="turn">
            <p className="user-q">{turn.question}</p>
            {turn.error && <p className="error">{turn.error}</p>}
            {!turn.response && !turn.error && (
              <p className="muted loading-hint">
                Routing to the right kitchen station…
              </p>
            )}
            {turn.response && (
              <ResultView
                mode={turn.response.mode}
                result={turn.response.result}
                personalized={turn.response.personalized}
                diagnosing={diagnosing}
                onDiagnoseAnswers={
                  turn.diagnoseSlug
                    ? (answers) =>
                        onDiagnoseAnswers(
                          turn.id,
                          turn.diagnoseSlug!,
                          turn.question,
                          answers,
                        )
                    : undefined
                }
              />
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
