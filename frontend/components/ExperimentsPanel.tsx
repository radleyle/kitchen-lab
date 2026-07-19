"use client";

import Link from "next/link";
import { FormEvent, useEffect, useRef, useState } from "react";
import {
  addObservation,
  deleteAttachment,
  designExperiment,
  listExperiments,
  updateExperiment,
  uploadTrialPhoto,
  type Experiment,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AuthImage } from "./AuthImage";

type PendingPhoto = {
  localId: string;
  trialId: number;
  file: File;
  previewUrl: string;
};

export function ExperimentsPanel() {
  const { user, loading: authLoading } = useAuth();
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [prompt, setPrompt] = useState("");
  const [designBusy, setDesignBusy] = useState(false);
  const [conclusion, setConclusion] = useState("");
  const [obsMetric, setObsMetric] = useState("notes");
  const [obsText, setObsText] = useState("");
  const [obsTrialId, setObsTrialId] = useState<number | "">("");
  const [obsBusy, setObsBusy] = useState(false);
  const [photoTrialId, setPhotoTrialId] = useState<number | "">("");
  const [pendingPhotos, setPendingPhotos] = useState<PendingPhoto[]>([]);
  const [pendingDeletes, setPendingDeletes] = useState<number[]>([]);
  const [saveBusy, setSaveBusy] = useState(false);
  const detailRef = useRef<HTMLElement | null>(null);

  const selected =
    selectedId == null
      ? null
      : (experiments.find((e) => e.id === selectedId) ?? null);

  const photosDirty =
    pendingPhotos.length > 0 || pendingDeletes.length > 0;

  function clearPhotoDraft() {
    setPendingPhotos((prev) => {
      for (const p of prev) URL.revokeObjectURL(p.previewUrl);
      return [];
    });
    setPendingDeletes([]);
  }

  function confirmDiscardIfDirty(): boolean {
    if (!photosDirty) return true;
    return window.confirm(
      "You have unsaved photo changes. Leave without saving?",
    );
  }

  async function refresh(keepSelected = true) {
    const list = await listExperiments();
    setExperiments(list);
    if (!keepSelected) return;
    setSelectedId((id) => {
      if (id != null && list.some((e) => e.id === id)) return id;
      return null;
    });
  }

  useEffect(() => {
    if (!user) {
      setExperiments([]);
      setSelectedId(null);
      clearPhotoDraft();
      return;
    }
    let cancelled = false;
    listExperiments()
      .then((list) => {
        if (cancelled) return;
        setExperiments(list);
        setSelectedId((id) =>
          id != null && list.some((e) => e.id === id) ? id : null,
        );
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Could not load experiments",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [user]);

  const formSyncedFor = useRef<number | null>(null);
  useEffect(() => {
    if (selectedId == null) {
      formSyncedFor.current = null;
      return;
    }
    if (formSyncedFor.current === selectedId) return;
    const exp = experiments.find((e) => e.id === selectedId);
    if (!exp) return;
    formSyncedFor.current = selectedId;
    setConclusion(exp.conclusion ?? "");
    setObsTrialId(exp.trials[0]?.id ?? "");
    setPhotoTrialId(exp.trials[0]?.id ?? "");
    clearPhotoDraft();
  }, [selectedId, experiments]);

  useEffect(() => {
    if (selected && detailRef.current) {
      detailRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [selectedId]);

  // Warn on browser refresh / tab close while draft photos exist.
  useEffect(() => {
    if (!photosDirty) return;
    function onBeforeUnload(e: BeforeUnloadEvent) {
      e.preventDefault();
      e.returnValue = "";
    }
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [photosDirty]);

  function selectExperiment(id: number) {
    if (selectedId === id) {
      if (!confirmDiscardIfDirty()) return;
      clearPhotoDraft();
      setSelectedId(null);
      return;
    }
    if (selectedId != null && !confirmDiscardIfDirty()) return;
    clearPhotoDraft();
    formSyncedFor.current = null;
    setSelectedId(id);
  }

  function stagePhoto(file: File) {
    if (photoTrialId === "") {
      setError("Pick a trial first.");
      return;
    }
    const previewUrl = URL.createObjectURL(file);
    setPendingPhotos((prev) => [
      ...prev,
      {
        localId: `${Date.now()}-${file.name}`,
        trialId: Number(photoTrialId),
        file,
        previewUrl,
      },
    ]);
    setError(null);
  }

  function removePending(localId: string) {
    setPendingPhotos((prev) => {
      const next = prev.filter((p) => p.localId !== localId);
      const removed = prev.find((p) => p.localId === localId);
      if (removed) URL.revokeObjectURL(removed.previewUrl);
      return next;
    });
  }

  function toggleDeleteSaved(attachmentId: number) {
    setPendingDeletes((prev) =>
      prev.includes(attachmentId)
        ? prev.filter((id) => id !== attachmentId)
        : [...prev, attachmentId],
    );
  }

  async function savePhotoChanges() {
    if (!selected || !photosDirty) return;
    setSaveBusy(true);
    setError(null);
    try {
      for (const id of pendingDeletes) {
        await deleteAttachment(id);
      }
      for (const p of pendingPhotos) {
        await uploadTrialPhoto(selected.id, p.trialId, p.file);
      }
      clearPhotoDraft();
      await refresh();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not save photo changes",
      );
    } finally {
      setSaveBusy(false);
    }
  }

  async function onDesign(e: FormEvent) {
    e.preventDefault();
    if (!prompt.trim()) return;
    if (!confirmDiscardIfDirty()) return;
    setDesignBusy(true);
    setError(null);
    try {
      const draft = await designExperiment(prompt.trim(), true);
      if (draft.feasible === false) {
        setError(
          typeof draft.message === "string"
            ? draft.message
            : "Could not design a controlled experiment from that prompt.",
        );
        return;
      }
      setPrompt("");
      clearPhotoDraft();
      formSyncedFor.current = null;
      await refresh();
      if (typeof draft.experiment_id === "number") {
        setSelectedId(draft.experiment_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Design failed");
    } finally {
      setDesignBusy(false);
    }
  }

  async function onAddObservation(e: FormEvent) {
    e.preventDefault();
    if (!selected || obsTrialId === "" || !obsText.trim()) return;
    setObsBusy(true);
    setError(null);
    try {
      await addObservation(selected.id, Number(obsTrialId), {
        metric: obsMetric.trim() || "notes",
        text_value: obsText.trim(),
      });
      setObsText("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save observation");
    } finally {
      setObsBusy(false);
    }
  }

  async function markDone() {
    if (!selected || !conclusion.trim()) {
      setError("Write a conclusion before marking the experiment done.");
      return;
    }
    if (photosDirty) {
      setError("Save or discard photo changes before marking done.");
      return;
    }
    setError(null);
    try {
      const updated = await updateExperiment(selected.id, {
        status: "done",
        conclusion: conclusion.trim(),
      });
      setExperiments((list) =>
        list.map((e) => (e.id === updated.id ? updated : e)),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update status");
    }
  }

  if (authLoading) {
    return <p className="muted">Checking sign-in…</p>;
  }

  if (!user) {
    return (
      <p className="muted">
        <Link href="/kitchen">Sign in</Link> to design and run kitchen
        experiments (control one variable, compare trials).
      </p>
    );
  }

  return (
    <div className="experiments">
      <p className="field-hint">
        Click an experiment to open it. Photo adds/removes stay as a draft until
        you hit Save — closing with unsaved changes will warn you.
      </p>

      <form className="stack-form" onSubmit={onDesign}>
        <label>
          What do you want to test?
          <textarea
            rows={3}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g. Does resting steak 10 minutes vs slicing immediately keep it juicier?"
            disabled={designBusy}
          />
        </label>
        <button type="submit" disabled={designBusy || !prompt.trim()}>
          {designBusy ? "Designing…" : "Design & save experiment"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      {experiments.length === 0 && (
        <p className="muted">No experiments yet — design one above.</p>
      )}

      {experiments.length > 0 && (
        <ul className="exp-list">
          {experiments.map((exp) => {
            const open = selectedId === exp.id;
            return (
              <li key={exp.id} className="exp-item">
                <button
                  type="button"
                  className={open ? "tech-btn active" : "tech-btn"}
                  aria-expanded={open}
                  onClick={() => selectExperiment(exp.id)}
                >
                  <strong>{exp.question}</strong>
                  <span className="muted">
                    {exp.status} · {exp.trials.length} trials ·{" "}
                    {open ? "click to close" : "click to open"}
                    {open && photosDirty ? " · unsaved photos" : ""}
                  </span>
                </button>

                {open && selected && (
                  <article
                    ref={detailRef}
                    className="exp-detail"
                    aria-label="Experiment details"
                  >
                    <p className="mode-pill">{selected.status}</p>
                    {selected.hypothesis && (
                      <p>
                        <strong>Hypothesis:</strong> {selected.hypothesis}
                      </p>
                    )}
                    <p>
                      <strong>Variable:</strong>{" "}
                      {selected.independent_variable}
                    </p>
                    {selected.constants?.length > 0 && (
                      <p className="muted">
                        Constants: {selected.constants.join("; ")}
                      </p>
                    )}

                    <h4>Trials</h4>
                    <ul className="trial-list">
                      {selected.trials.map((t) => {
                        const saved = (t.attachments ?? []).filter(
                          (a) => !pendingDeletes.includes(a.id),
                        );
                        const marked = (t.attachments ?? []).filter((a) =>
                          pendingDeletes.includes(a.id),
                        );
                        const staged = pendingPhotos.filter(
                          (p) => p.trialId === t.id,
                        );
                        const hasPhotos =
                          saved.length + marked.length + staged.length > 0;

                        return (
                          <li key={t.id}>
                            <strong>
                              {t.label}: {t.variable_value}
                            </strong>
                            {t.notes && <p className="muted">{t.notes}</p>}
                            {(t.observations?.length ?? 0) > 0 ? (
                              <ul>
                                {t.observations.map((o) => (
                                  <li key={o.id}>
                                    {o.metric}
                                    {o.value != null
                                      ? `: ${o.value}${o.unit ? ` ${o.unit}` : ""}`
                                      : ""}
                                    {o.text_value ? ` — ${o.text_value}` : ""}
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <p className="muted">No observations yet.</p>
                            )}
                            {hasPhotos && (
                              <div className="photo-row">
                                {saved.map((a) => (
                                  <AuthImage
                                    key={a.id}
                                    attachmentId={a.id}
                                    alt={`Photo for ${t.label}`}
                                    onRemove={() => toggleDeleteSaved(a.id)}
                                  />
                                ))}
                                {marked.map((a) => (
                                  <AuthImage
                                    key={`del-${a.id}`}
                                    attachmentId={a.id}
                                    alt={`Marked for delete — ${t.label}`}
                                    markedForDelete
                                    onRemove={() => toggleDeleteSaved(a.id)}
                                  />
                                ))}
                                {staged.map((p) => (
                                  <div key={p.localId} className="photo-thumb">
                                    <img
                                      className="trial-photo"
                                      src={p.previewUrl}
                                      alt={`New photo for ${t.label}`}
                                    />
                                    <span className="photo-badge">new</span>
                                    <button
                                      type="button"
                                      className="photo-remove"
                                      aria-label="Remove staged photo"
                                      onClick={() => removePending(p.localId)}
                                    >
                                      ×
                                    </button>
                                  </div>
                                ))}
                              </div>
                            )}
                          </li>
                        );
                      })}
                    </ul>

                    {selected.status !== "done" && (
                      <>
                        <form
                          className="stack-form"
                          onSubmit={onAddObservation}
                        >
                          <h4>Log observation</h4>
                          <label>
                            Trial
                            <select
                              value={obsTrialId}
                              onChange={(e) =>
                                setObsTrialId(
                                  e.target.value
                                    ? Number(e.target.value)
                                    : "",
                                )
                              }
                            >
                              {selected.trials.map((t) => (
                                <option key={t.id} value={t.id}>
                                  {t.label}
                                </option>
                              ))}
                            </select>
                          </label>
                          <label>
                            Metric
                            <input
                              value={obsMetric}
                              onChange={(e) => setObsMetric(e.target.value)}
                              placeholder="juiciness, browning…"
                            />
                          </label>
                          <label>
                            What you saw
                            <textarea
                              rows={2}
                              value={obsText}
                              onChange={(e) => setObsText(e.target.value)}
                              required
                            />
                          </label>
                          <button type="submit" disabled={obsBusy}>
                            {obsBusy ? "Saving…" : "Add observation"}
                          </button>
                        </form>

                        <div className="stack-form conclude-block">
                          <h4>Conclude</h4>
                          <label>
                            Conclusion
                            <textarea
                              rows={3}
                              value={conclusion}
                              onChange={(e) => setConclusion(e.target.value)}
                              placeholder="Which trial won, and what you’ll do next cook…"
                            />
                          </label>
                          <button type="button" onClick={markDone}>
                            Mark done
                          </button>
                        </div>
                      </>
                    )}

                    <div className="stack-form photo-draft">
                      <h4>Photos</h4>
                      <p className="field-hint">
                        Stage adds/removes here, then Save. Closing with unsaved
                        changes asks for confirmation. Hover a photo for ×.
                      </p>
                      <label>
                        Trial
                        <select
                          value={photoTrialId}
                          onChange={(e) =>
                            setPhotoTrialId(
                              e.target.value ? Number(e.target.value) : "",
                            )
                          }
                        >
                          {selected.trials.map((t) => (
                            <option key={t.id} value={t.id}>
                              {t.label}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Add photo
                        <input
                          type="file"
                          accept="image/jpeg,image/png,image/webp"
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) stagePhoto(file);
                            e.target.value = "";
                          }}
                        />
                      </label>
                      <div className="photo-actions">
                        <button
                          type="button"
                          onClick={savePhotoChanges}
                          disabled={!photosDirty || saveBusy}
                        >
                          {saveBusy ? "Saving…" : "Save photo changes"}
                        </button>
                        <button
                          type="button"
                          className="text-btn"
                          disabled={!photosDirty || saveBusy}
                          onClick={() => {
                            if (
                              photosDirty &&
                              window.confirm("Discard unsaved photo changes?")
                            ) {
                              clearPhotoDraft();
                            }
                          }}
                        >
                          Discard
                        </button>
                      </div>
                      {photosDirty && (
                        <p className="unsaved-hint">
                          Unsaved: {pendingPhotos.length} new,{" "}
                          {pendingDeletes.length} to delete
                        </p>
                      )}
                    </div>

                    {selected.status === "done" && selected.conclusion && (
                      <section>
                        <h4>Conclusion</h4>
                        <p>{selected.conclusion}</p>
                      </section>
                    )}
                  </article>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
