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
import { FeatureGuide } from "@/components/FeatureGuide";
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
    <main className="lab-page">
      <header className="page-banner">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/images/bread.jpg" alt="" className="page-banner-media" />
        <div className="page-banner-scrim" aria-hidden />
        <div className="page-banner-content shell">
          <h1>Lab</h1>
          <p className="lede">
            Practice room: proven methods, fair kitchen tests, and your notes.
          </p>
        </div>
      </header>

      <div className="shell">
        <nav className="lab-jump" aria-label="Lab sections">
          <a href="#techniques">Techniques</a>
          <a href="#experiments">Experiments</a>
          <a href="#notebook">Notebook</a>
        </nav>
        <FeatureGuide
          title="What is the Lab?"
          summary="Ask is for conversation. Lab is for reference and practice — like a cookbook chapter plus a notebook."
          when="Come here when you want to study a method, compare two ways of cooking, or write down what worked at home."
          steps={[
            "Techniques — browse curated methods (velveting, dry-brining…). Click one to see steps + the science idea.",
            "Experiments — describe a question; we draft a fair test. You cook, log notes/photos, then conclude.",
            "Notebook — free-form notes for yourself (sign-in required).",
          ]}
          terms={[
            {
              term: "Mechanism",
              meaning:
                "The science idea behind a technique (e.g. Maillard browning = the browning/flavor reaction on a hot, dry surface).",
            },
            {
              term: "Independent variable",
              meaning:
                "The one thing you change in an experiment (rest time, salt timing…). Everything else stays the same so the comparison is fair.",
            },
          ]}
        />

      <section
        id="techniques"
        className="lab-section"
        aria-labelledby="tech-heading"
      >
        <h2 id="tech-heading">Techniques</h2>
        <FeatureGuide
          title="How to use Techniques"
          summary="A shared textbook of cooking methods with procedure steps and common mistakes."
          when="Before trying something new, or when a recipe name-drops a method you’ve never heard of."
          steps={[
            "Scan the list and click a technique.",
            "Read the procedure top to bottom.",
            "Check “common mistakes” before you cook.",
          ]}
        />
        {techError && <p className="error">{techError}</p>}
        {techniques.length === 0 && !techError && (
          <p className="muted">Loading techniques…</p>
        )}
        <div className="tech-layout">
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
        </div>
      </section>

      <section
        id="experiments"
        className="lab-section"
        aria-labelledby="exp-heading"
      >
        <h2 id="exp-heading">Experiments</h2>
        <FeatureGuide
          title="How to use Experiments"
          summary="A mini science fair for dinner: change one thing, keep everything else equal, write what happened."
          when="When you’re arguing with yourself (“Does resting steak matter?”) and want a clear A vs B answer — not vibes."
          steps={[
            "Describe what you want to test in plain English.",
            "Open the saved experiment, cook each trial, log observations (and optional photos).",
            "Click Save on photo changes before closing.",
            "Write a short conclusion and mark done.",
          ]}
        />
        <ExperimentsPanel />
      </section>

      <section
        id="notebook"
        className="lab-section"
        aria-labelledby="note-heading"
      >
        <h2 id="note-heading">Notebook</h2>
        <FeatureGuide
          title="How to use the Notebook"
          summary="Private sticky notes for temps, tweaks, and “never again” lessons."
          when="After a cook, when something surprising worked (or failed) and you don’t want to forget."
          steps={[
            "Sign in on My kitchen if you haven’t.",
            "Add a title + what you observed.",
            "Come back later when you remake the dish.",
          ]}
        />
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
      </div>
    </main>
  );
}
