"use client";

import type { GeneratedRecipe } from "@/lib/api";

function CitationList({ citations }: { citations: unknown }) {
  if (!Array.isArray(citations) || citations.length === 0) return null;
  return (
    <div className="citations">
      <h4>Sources for this step</h4>
      <ul>
        {citations.map((c, i) => {
          const cit = c as {
            claim?: string;
            confidence?: string;
            source?: { title?: string };
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

/** Science-first recipe display: every step shows why + the science. */
export function RecipeView({
  recipe,
  savedNote,
}: {
  recipe: GeneratedRecipe;
  savedNote?: string | null;
}) {
  if (!recipe.feasible) {
    return (
      <p className="error">
        {recipe.message || "Could not build a feasible recipe from that request."}
      </p>
    );
  }

  const steps = recipe.steps ?? [];
  const ingredients = recipe.ingredients ?? [];
  const overrides = recipe.safety_overrides;

  return (
    <article className="recipe-view">
      <header className="recipe-view-head">
        <h2 className="recipe-title">{recipe.title}</h2>
        {recipe.servings != null && (
          <p className="muted">Serves {recipe.servings}</p>
        )}
        {recipe.description && <p>{recipe.description}</p>}
        {savedNote && <p className="ok">{savedNote}</p>}
      </header>

      {Array.isArray(overrides) && overrides.length > 0 && (
        <p className="safety-banner">
          Safety floor applied — an internal temperature was raised to meet USDA
          guidance (deterministic rule, not an AI guess).
        </p>
      )}

      <section>
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
      </section>

      <section>
        <h3>Method — with the science</h3>
        <p className="field-hint">
          Each step has an Action, a Why (practical reason), and Science (the
          mechanism). Follow the Action; the rest teaches your instincts.
        </p>
        <ol className="science-steps">
          {steps.map((s, i) => {
            const temp = s.target_internal_temp_c ?? s.critical_temp_c;
            return (
              <li key={i} className="science-step">
                <p className="step-num">Step {s.position ?? i + 1}</p>
                <p className="step-action">{s.instruction}</p>
                {s.why && (
                  <div className="step-layer">
                    <span className="step-layer-label">Why</span>
                    <p>{s.why}</p>
                  </div>
                )}
                {s.science && (
                  <div className="step-layer science">
                    <span className="step-layer-label">Science</span>
                    <p>{s.science}</p>
                  </div>
                )}
                {s.visual_cues && (
                  <p className="muted">Look for: {s.visual_cues}</p>
                )}
                {temp != null && (
                  <p className="temp-chip">Target internal: {temp}°C</p>
                )}
                <CitationList citations={s.citations} />
              </li>
            );
          })}
        </ol>
      </section>

      {recipe.kitchen?.notes && recipe.kitchen.notes.length > 0 && (
        <section>
          <h3>Adjusted for your kitchen</h3>
          <ul>
            {recipe.kitchen.notes.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </section>
      )}

      {recipe.grounding_note && (
        <p className="muted grounding">{recipe.grounding_note}</p>
      )}
    </article>
  );
}
