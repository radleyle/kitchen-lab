"use client";

type Props = {
  mode: string;
  result: Record<string, unknown>;
  personalized?: boolean;
  onDiagnoseAnswers?: (
    answers: { question: string; answer: string }[],
  ) => void;
  diagnosing?: boolean;
};

function asString(v: unknown): string {
  return typeof v === "string" ? v : "";
}

function CitationList({ citations }: { citations: unknown }) {
  if (!Array.isArray(citations) || citations.length === 0) return null;
  return (
    <div className="citations">
      <h4>Sources</h4>
      <ul>
        {citations.map((c, i) => {
          const cit = c as {
            claim?: string;
            confidence?: string;
            source?: { title?: string; author?: string };
          };
          return (
            <li key={i}>
              <span className="cit-claim">{cit.claim}</span>
              {cit.source?.title && (
                <span className="cit-src">
                  — {cit.source.title}
                  {cit.confidence ? ` (${cit.confidence})` : ""}
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function Layers({
  action,
  reason,
  science,
  caveats,
  citations,
}: {
  action: string;
  reason: string;
  science: string;
  caveats?: string;
  citations?: unknown;
}) {
  return (
    <div className="layers">
      {action && (
        <section>
          <h3>Action</h3>
          <p>{action}</p>
        </section>
      )}
      {reason && (
        <section>
          <h3>Reason</h3>
          <p>{reason}</p>
        </section>
      )}
      {science && (
        <section>
          <h3>Science</h3>
          <p>{science}</p>
        </section>
      )}
      {caveats && (
        <section className="caveats">
          <h3>Caveats</h3>
          <p>{caveats}</p>
        </section>
      )}
      <CitationList citations={citations} />
    </div>
  );
}

function Meta({
  mode,
  handler,
  personalized,
}: {
  mode: string;
  handler?: string;
  personalized?: boolean;
}) {
  return (
    <header className="result-meta">
      <span className="mode-pill">{mode}</span>
      {handler ? <span className="handler">{handler}</span> : null}
      {personalized ? (
        <span className="personal-pill">personalized</span>
      ) : null}
    </header>
  );
}

export function ResultView({
  mode,
  result,
  personalized,
  onDiagnoseAnswers,
  diagnosing,
}: Props) {
  const handler = asString(result.handler);

  // Grounded learn / fallback answers
  if (
    typeof result.action === "string" ||
    typeof result.sufficient === "boolean"
  ) {
    return (
      <div className="result-block">
        <Meta mode={mode} handler={handler} personalized={personalized} />
        <Layers
          action={asString(result.action)}
          reason={asString(result.reason)}
          science={asString(result.science)}
          caveats={asString(result.caveats)}
          citations={result.citations}
        />
      </div>
    );
  }

  // Diagnosis: no taxonomy match
  if (result.matched === false && typeof result.message === "string") {
    return (
      <div className="result-block">
        <Meta mode={mode} personalized={personalized} />
        <p>{result.message}</p>
      </div>
    );
  }

  // Diagnosis round 1 — questions
  if (result.matched === true && Array.isArray(result.questions)) {
    const symptom = result.symptom as { slug?: string; description?: string };
    const questions = result.questions as {
      cause_id: number;
      question: string;
    }[];
    return (
      <DiagnoseForm
        mode={mode}
        handler={handler}
        personalized={personalized}
        symptomDescription={symptom?.description ?? ""}
        questions={questions}
        causes={result.candidate_causes as { cause: string; prior_score: number }[]}
        onSubmit={onDiagnoseAnswers}
        busy={diagnosing}
      />
    );
  }

  // Diagnosis round 2
  if (result.diagnosis && typeof result.diagnosis === "object") {
    const diagnosis = result.diagnosis as {
      most_likely_cause?: string;
      explanation?: string;
      confidence?: string;
      key_evidence?: string;
    };
    const fix = (result.fix as Record<string, unknown>) || {};
    const ranked = (result.ranked_causes as { cause: string; score: number }[]) || [];
    return (
      <div className="result-block">
        <Meta mode={mode} handler="diagnosis" personalized={personalized} />
        <section className="diagnosis-verdict">
          <h3>Most likely</h3>
          <p className="verdict-cause">{diagnosis.most_likely_cause}</p>
          <p>{diagnosis.explanation}</p>
          <p className="muted">
            Confidence: {diagnosis.confidence}
            {diagnosis.key_evidence
              ? ` · Evidence: “${diagnosis.key_evidence}”`
              : ""}
          </p>
        </section>
        {ranked.length > 0 && (
          <section>
            <h3>Ranked causes</h3>
            <ol className="ranked">
              {ranked.map((r) => (
                <li key={r.cause}>
                  <strong>{r.cause}</strong>
                  <span className="muted"> · score {r.score}</span>
                </li>
              ))}
            </ol>
          </section>
        )}
        <Layers
          action={asString(fix.action)}
          reason={asString(fix.reason)}
          science={asString(fix.science)}
          caveats={asString(fix.caveats)}
          citations={fix.citations}
        />
      </div>
    );
  }

  // Recipe generate / adapt
  if (result.feasible === true && Array.isArray(result.steps)) {
    const steps = result.steps as {
      instruction: string;
      why?: string;
      science?: string;
      visual_cues?: string;
      target_internal_temp_c?: number | null;
      citations?: unknown;
    }[];
    const ingredients = (result.ingredients as {
      ingredient: string;
      grams?: number | null;
      amount?: string;
    }[]) || [];
    const kitchen = result.kitchen as { notes?: string[]; dietary_conflicts?: unknown[] } | undefined;
    const overrides = result.safety_overrides as unknown[];

    return (
      <div className="result-block">
        <Meta mode={mode} handler={handler} personalized={personalized} />
        <h2 className="recipe-title">{asString(result.title)}</h2>
        <p>{asString(result.description)}</p>
        {Array.isArray(overrides) && overrides.length > 0 && (
          <p className="safety-banner">
            Safety floor applied — an internal temperature was raised to meet
            USDA guidance.
          </p>
        )}
        <h3>Ingredients</h3>
        <ul className="ingredients">
          {ingredients.map((ing, i) => (
            <li key={i}>
              {ing.ingredient}
              {ing.grams != null
                ? ` — ${ing.grams} g`
                : ing.amount
                  ? ` — ${ing.amount}`
                  : ""}
            </li>
          ))}
        </ul>
        <h3>Steps</h3>
        <ol className="steps">
          {steps.map((s, i) => (
            <li key={i}>
              <p className="step-action">{s.instruction}</p>
              {s.why && <p className="muted">Why: {s.why}</p>}
              {s.science && <p className="muted">Science: {s.science}</p>}
              {s.visual_cues && (
                <p className="muted">Look for: {s.visual_cues}</p>
              )}
              <CitationList citations={s.citations} />
            </li>
          ))}
        </ol>
        {kitchen?.notes && kitchen.notes.length > 0 && (
          <section>
            <h3>Your kitchen</h3>
            <ul>
              {kitchen.notes.map((n) => (
                <li key={n}>{n}</li>
              ))}
            </ul>
          </section>
        )}
        <p className="muted grounding">{asString(result.grounding_note)}</p>
      </div>
    );
  }

  // Substitution
  if (result.found === true && (result.options || result.options_by_function)) {
    const options = (result.options as {
      substitute: string;
      ratio: number;
      texture_notes?: string;
      procedure_adjustments?: string;
      confidence?: string;
      excluded_by_diet?: unknown;
    }[]) || [];
    const fn = result.function as { name?: string; description?: string } | null;
    return (
      <div className="result-block">
        <Meta mode={mode} handler="substitution" personalized={personalized} />
        <p>
          Replacing <strong>{asString(result.ingredient)}</strong>
          {fn?.name ? (
            <>
              {" "}
              as <strong>{fn.name}</strong>
            </>
          ) : null}
        </p>
        {result.needs_clarification ? (
          <p className="caveats">{asString(result.question)}</p>
        ) : null}
        {options.length > 0 && (
          <ul className="sub-options">
            {options.map((o) => (
              <li key={o.substitute}>
                <strong>{o.substitute}</strong>
                <span className="muted">
                  {" "}
                  · ratio {o.ratio} · {o.confidence}
                  {o.excluded_by_diet ? " · conflicts with diet profile" : ""}
                </span>
                {o.texture_notes && <p>{o.texture_notes}</p>}
                {o.procedure_adjustments && (
                  <p className="muted">{o.procedure_adjustments}</p>
                )}
              </li>
            ))}
          </ul>
        )}
        {typeof result.options_by_function === "object" &&
          result.options_by_function !== null && (
            <div>
              {Object.entries(
                result.options_by_function as Record<string, unknown[]>,
              ).map(([name, opts]) => (
                <div key={name}>
                  <h3>{name}</h3>
                  <ul>
                    {(opts as { substitute: string }[]).map((o) => (
                      <li key={o.substitute}>{o.substitute}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
      </div>
    );
  }

  // Experiment design
  if (result.feasible === true && Array.isArray(result.trials)) {
    const trials = result.trials as {
      label: string;
      variable_value: string;
    }[];
    return (
      <div className="result-block">
        <Meta mode={mode} handler="experiment" personalized={personalized} />
        <h3>Question</h3>
        <p>{asString(result.question)}</p>
        <h3>Hypothesis</h3>
        <p>{asString(result.hypothesis)}</p>
        <h3>Independent variable</h3>
        <p>{asString(result.independent_variable)}</p>
        <h3>Trials</h3>
        <ul>
          {trials.map((t) => (
            <li key={t.label}>
              <strong>{t.label}</strong> — {t.variable_value}
            </li>
          ))}
        </ul>
        {result.persisted ? (
          <p className="muted">Saved as experiment #{String(result.experiment_id)}</p>
        ) : (
          <p className="muted">{asString(result.note)}</p>
        )}
      </div>
    );
  }

  return (
    <div className="result-block">
      <Meta mode={mode} personalized={personalized} />
      <pre className="raw">{JSON.stringify(result, null, 2)}</pre>
    </div>
  );
}

function DiagnoseForm({
  mode,
  handler,
  personalized,
  symptomDescription,
  questions,
  causes,
  onSubmit,
  busy,
}: {
  mode: string;
  handler: string;
  personalized?: boolean;
  symptomDescription: string;
  questions: { cause_id: number; question: string }[];
  causes?: { cause: string; prior_score: number }[];
  onSubmit?: (answers: { question: string; answer: string }[]) => void;
  busy?: boolean;
}) {
  return (
    <div className="result-block">
      <Meta mode={mode} handler={handler} personalized={personalized} />
      <h3>Matched: {symptomDescription}</h3>
      {causes && causes.length > 0 && (
        <p className="muted">
          Starting suspects:{" "}
          {causes.map((c) => `${c.cause} (${c.prior_score})`).join(" · ")}
        </p>
      )}
      <form
        className="diagnose-form"
        onSubmit={(e) => {
          e.preventDefault();
          if (!onSubmit) return;
          const fd = new FormData(e.currentTarget);
          const answers = questions.map((q) => ({
            question: q.question,
            answer: String(fd.get(`q-${q.cause_id}`) ?? "").trim(),
          }));
          onSubmit(answers.filter((a) => a.answer));
        }}
      >
        {questions.map((q) => (
          <label key={q.cause_id} className="q-field">
            <span>{q.question}</span>
            <textarea
              name={`q-${q.cause_id}`}
              rows={2}
              placeholder="Your answer…"
              disabled={busy}
            />
          </label>
        ))}
        <button type="submit" disabled={busy}>
          {busy ? "Ranking causes…" : "Conclude diagnosis"}
        </button>
      </form>
    </div>
  );
}
