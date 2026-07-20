"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import {
  askAgent,
  concludeDiagnosis,
  deleteConversation,
  getConversation,
  listConversations,
  syncConversationMessages,
  type AgentResponse,
  type ConversationSummary,
  type ConversationTurn,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useConfirm } from "@/lib/confirm";
import { ResultView } from "./ResultView";

type Turn = {
  id: string;
  question: string;
  response: AgentResponse | null;
  error: string | null;
  /** Symptom slug from first diagnose pass, for conclude. */
  diagnoseSlug?: string;
};

const EXAMPLES: { mode: string; q: string }[] = [
  { mode: "Learn", q: "Why does bread get crusty?" },
  { mode: "Diagnose", q: "My roast chicken is dry — what went wrong?" },
  { mode: "Cook", q: "Generate a recipe for pan-seared salmon for 2" },
  { mode: "Cook", q: "I have eggs and butter — what can I make?" },
  { mode: "Substitute", q: "Substitute buttermilk in pancakes" },
];

function turnsToMessages(turns: Turn[]): ConversationTurn[] {
  return turns.map((t) => ({
    id: t.id,
    question: t.question,
    response: t.response,
    diagnose_slug: t.diagnoseSlug ?? null,
    error: t.error,
  }));
}

function messagesToTurns(messages: ConversationTurn[]): Turn[] {
  return messages.map((m, i) => ({
    id: m.id || `hist-${i}`,
    question: m.question,
    response: m.response ?? null,
    error: m.error ?? null,
    diagnoseSlug: m.diagnose_slug || undefined,
  }));
}

/**
 * Ask station: type a question, get a routed answer.
 * When signed in, chats save to history (like a shelf of past tickets).
 */
export function AgentChat() {
  const { user, loading: authLoading } = useAuth();
  const confirm = useConfirm();
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [diagnosing, setDiagnosing] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [history, setHistory] = useState<ConversationSummary[]>([]);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyBusy, setHistoryBusy] = useState(false);

  async function refreshHistory() {
    if (!user) {
      setHistory([]);
      return;
    }
    try {
      setHistory(await listConversations());
      setHistoryError(null);
    } catch (err) {
      setHistoryError(
        err instanceof Error ? err.message : "Could not load Ask history",
      );
    }
  }

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      setHistory([]);
      setConversationId(null);
      return;
    }
    void refreshHistory();
  }, [user, authLoading]);

  function startNewChat() {
    setConversationId(null);
    setTurns([]);
    setInput("");
  }

  async function openConversation(id: number) {
    if (historyBusy) return;
    setHistoryBusy(true);
    setHistoryError(null);
    try {
      const detail = await getConversation(id);
      setConversationId(detail.id);
      setTurns(messagesToTurns(detail.messages ?? []));
    } catch (err) {
      setHistoryError(
        err instanceof Error ? err.message : "Could not open conversation",
      );
    } finally {
      setHistoryBusy(false);
    }
  }

  async function onDeleteConversation(id: number) {
    const ok = await confirm({
      title: "Delete this chat?",
      message: "This Ask history thread will be removed permanently.",
      confirmLabel: "Delete",
      danger: true,
    });
    if (!ok) return;
    try {
      await deleteConversation(id);
      if (conversationId === id) startNewChat();
      await refreshHistory();
    } catch (err) {
      setHistoryError(
        err instanceof Error ? err.message : "Could not delete conversation",
      );
    }
  }

  async function submit(question: string) {
    const q = question.trim();
    if (!q || loading) return;

    const id = `${Date.now()}`;
    setTurns((t) => [{ id, question: q, response: null, error: null }, ...t]);
    setInput("");
    setLoading(true);

    try {
      const response = await askAgent(q, conversationId);
      const result = response.result;
      const diagnoseSlug =
        response.mode === "diagnose" &&
        result &&
        typeof result === "object" &&
        (result as { symptom?: { slug?: string } }).symptom?.slug;

      if (typeof response.conversation_id === "number") {
        setConversationId(response.conversation_id);
      }

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
      if (user) void refreshHistory();
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
      const nextTurns = turns.map((turn) =>
        turn.id === turnId && turn.response
          ? {
              ...turn,
              response: {
                ...turn.response,
                result,
              },
            }
          : turn,
      );
      setTurns(nextTurns);
      if (user && conversationId != null) {
        try {
          await syncConversationMessages(
            conversationId,
            turnsToMessages(nextTurns),
          );
          void refreshHistory();
        } catch {
          /* history sync is best-effort after conclude */
        }
      }
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
          <Link href="/kitchen">kitchen profile</Link>, and chats save to
          history.
        </p>
      ) : (
        <p className="auth-hint muted">
          Anonymous mode.{" "}
          <Link href="/kitchen">Sign in</Link> to personalize and keep Ask
          history.
        </p>
      )}

      <div className={user ? "ask-layout" : undefined}>
        {user && (
          <aside className="ask-history" aria-label="Ask history">
            <div className="ask-history-head">
              <h2>History</h2>
              <button
                type="button"
                className="text-btn"
                onClick={startNewChat}
                disabled={loading}
              >
                New chat
              </button>
            </div>
            {historyError && <p className="error">{historyError}</p>}
            {history.length === 0 && !historyError && (
              <p className="muted ask-history-empty">
                No saved chats yet — ask something and it will show up here.
              </p>
            )}
            <ul className="ask-history-list">
              {history.map((c) => {
                const open = conversationId === c.id;
                return (
                  <li key={c.id} className="ask-history-item">
                    <button
                      type="button"
                      className={open ? "tech-btn active" : "tech-btn"}
                      disabled={historyBusy}
                      onClick={() => void openConversation(c.id)}
                    >
                      <strong>{c.title || "Untitled chat"}</strong>
                      <span className="muted">
                        {c.mode}
                        {" · "}
                        {new Date(c.updated_at).toLocaleString()}
                      </span>
                    </button>
                    <button
                      type="button"
                      className="text-btn ask-history-delete"
                      aria-label={`Delete ${c.title || "chat"}`}
                      onClick={() => void onDeleteConversation(c.id)}
                    >
                      Delete
                    </button>
                  </li>
                );
              })}
            </ul>
          </aside>
        )}

        <div className="ask-main">
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
              <p className="examples-label">Not sure what to ask? Try one</p>
              <ul>
                {EXAMPLES.map((ex) => (
                  <li key={ex.q}>
                    <button
                      type="button"
                      className="example-btn"
                      onClick={() => submit(ex.q)}
                      disabled={loading}
                    >
                      <span className="ex-mode">{ex.mode}</span>
                      <span className="ex-q">{ex.q}</span>
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
      </div>
    </div>
  );
}
