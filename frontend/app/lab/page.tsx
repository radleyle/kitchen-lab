"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import {
  createNotebookEntry,
  deleteNotebookEntry,
  getTechnique,
  listNotebook,
  listTechniques,
  type NotebookEntry,
  type TechniqueDetail,
  type TechniqueSummary,
} from "@/lib/api";
import { ExperimentsPanel } from "@/components/ExperimentsPanel";
import { useAuth } from "@/lib/auth";

function asTextList(items: unknown[]): string[] {
  return items.map((item) => {
    if (typeof item === "string") return item;
    if (item && typeof item === "object") {
      const o = item as Record<string, unknown>;
      if (typeof o.step === "string") return o.step;
      if (typeof o.text === "string") return o.text;
      if (typeof o.instruction === "string") return o.instruction;
      if (typeof o.mistake === "string") return o.mistake;
      return JSON.stringify(item);
    }
    return String(item);
  });
}

export default function LabPage() {
  const { user, loading: authLoading } = useAuth();
  const [techniques, setTechniques] = useState<TechniqueSummary[]>([]);
  const [techError, setTechError] = useState<string | null>(null);
  const [selected, setSelected] = useState<TechniqueDetail | null>(null);
  const [detailBusy, setDetailBusy] = useState(false);

  const [notes, setNotes] = useState<NotebookEntry[]>([]);
  const [noteError, setNoteError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [noteBusy, setNoteBusy] = useState(false);

  useEffect(() => {
    listTechniques()
      .then(setTechniques)
      .catch((err) =>
        setTechError(
          err instanceof Error ? err.message : "Could not load techniques",
        ),
      );
  }, []);

  useEffect(() => {
    if (!user) {
      setNotes([]);
      return;
    }
    listNotebook()
      .then(setNotes)
      .catch((err) =>
        setNoteError(
          err instanceof Error ? err.message : "Could not load notebook",
        ),
      );
  }, [user]);

  async function openTechnique(slug: string) {
    setDetailBusy(true);
    setTechError(null);
    try {
      setSelected(await getTechnique(slug));
    } catch (err) {
      setTechError(
        err instanceof Error ? err.message : "Could not load technique",
      );
    } finally {
      setDetailBusy(false);
    }
  }

  async function onCreateNote(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setNoteBusy(true);
    setNoteError(null);
    try {
      const entry = await createNotebookEntry({
        title: title.trim(),
        body: body.trim() || undefined,
      });
      setNotes((n) => [entry, ...n]);
      setTitle("");
      setBody("");
    } catch (err) {
      setNoteError(err instanceof Error ? err.message : "Could not save note");
    } finally {
      setNoteBusy(false);
    }
  }

  async function onDeleteNote(id: number) {
    setNoteError(null);
    try {
      await deleteNotebookEntry(id);
      setNotes((n) => n.filter((e) => e.id !== id));
    } catch (err) {
      setNoteError(
        err instanceof Error ? err.message : "Could not delete note",
      );
    }
  }

  return (
    <main className="shell lab-page">
      <header className="page-header">
        <h1>Lab</h1>
        <p className="lede">
          Three stations in one room: techniques (textbook), experiments
          (science fair for dinner), and your notebook (sticky notes).
        </p>
        <nav className="lab-jump" aria-label="Lab sections">
          <a href="#techniques">Techniques</a>
          <a href="#experiments">Experiments</a>
          <a href="#notebook">Notebook</a>
        </nav>
      </header>

      <section
        id="techniques"
        className="lab-section"
        aria-labelledby="tech-heading"
      >
        <h2 id="tech-heading">Techniques</h2>
        {techError && <p className="error">{techError}</p>}
        {techniques.length === 0 && !techError && (
          <p className="muted">Loading techniques…</p>
        )}
        <ul className="tech-list">
          {techniques.map((t) => (
            <li key={t.slug}>
              <button
                type="button"
                className={
                  selected?.slug === t.slug ? "tech-btn active" : "tech-btn"
                }
                onClick={() => openTechnique(t.slug)}
                disabled={detailBusy}
              >
                <strong>{t.name}</strong>
                <span className="muted">{t.summary}</span>
              </button>
            </li>
          ))}
        </ul>

        {selected && (
          <article className="tech-detail">
            <h3>{selected.name}</h3>
            <p>{selected.summary}</p>
            {selected.mechanism && (
              <section>
                <h4>Science: {selected.mechanism.name}</h4>
                <p>{selected.mechanism.explanation}</p>
              </section>
            )}
            {selected.procedure?.length > 0 && (
              <section>
                <h4>Procedure</h4>
                <ol>
                  {asTextList(selected.procedure).map((step, i) => (
                    <li key={i}>{step}</li>
                  ))}
                </ol>
              </section>
            )}
            {selected.common_mistakes?.length > 0 && (
              <section>
                <h4>Common mistakes</h4>
                <ul>
                  {asTextList(selected.common_mistakes).map((m, i) => (
                    <li key={i}>{m}</li>
                  ))}
                </ul>
              </section>
            )}
            {selected.applicable_foods?.length > 0 && (
              <p className="muted">
                Foods: {selected.applicable_foods.join(", ")}
              </p>
            )}
          </article>
        )}
      </section>

      <section
        id="experiments"
        className="lab-section"
        aria-labelledby="exp-heading"
      >
        <h2 id="exp-heading">Experiments</h2>
        <ExperimentsPanel />
      </section>

      <section
        id="notebook"
        className="lab-section"
        aria-labelledby="note-heading"
      >
        <h2 id="note-heading">Notebook</h2>
        {authLoading && <p className="muted">Checking sign-in…</p>}
        {!authLoading && !user && (
          <p className="muted">
            <Link href="/kitchen">Sign in</Link> to keep personal cooking notes.
          </p>
        )}
        {!authLoading && user && (
          <>
            <form className="stack-form" onSubmit={onCreateNote}>
              <label>
                Title
                <input
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. First reverse-sear steak"
                />
              </label>
              <label>
                Notes
                <textarea
                  rows={4}
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  placeholder="What you tried, temps, what you’d change…"
                />
              </label>
              {noteError && <p className="error">{noteError}</p>}
              <button type="submit" disabled={noteBusy}>
                {noteBusy ? "Saving…" : "Add note"}
              </button>
            </form>

            <ul className="note-list">
              {notes.map((n) => (
                <li key={n.id} className="note-item">
                  <div>
                    <strong>{n.title}</strong>
                    <span className="muted note-date">
                      {new Date(n.created_at).toLocaleString()}
                    </span>
                    {n.body && <p>{n.body}</p>}
                  </div>
                  <button
                    type="button"
                    className="text-btn"
                    onClick={() => onDeleteNote(n.id)}
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>
            {notes.length === 0 && (
              <p className="muted">No notes yet — add one above.</p>
            )}
          </>
        )}
      </section>
    </main>
  );
}
