"use client";

import type { ReactNode } from "react";
import type { GeneratedRecipe } from "@/lib/api";
import { recipeCoverUrl } from "@/lib/images";
import { RecipeWhatIf } from "@/components/RecipeWhatIf";
import {
  CitationList,
  SafetyPanel,
  TrustStrip,
  parseSafety,
  trustFromRecipe,
} from "@/components/trust";

/** Science-first recipe display: every step shows why + the science. */
export function RecipeView({
  recipe,
  savedNote,
  actions,
  showWhatIf = true,
}: {
  recipe: GeneratedRecipe;
  savedNote?: string | null;
  actions?: ReactNode;
  showWhatIf?: boolean;
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
  const safety = parseSafety(recipe.safety);
  const cover = recipeCoverUrl({
    id: recipe.recipe_id,
    image_url: recipe.image_url,
    title: recipe.title,
  });
  const kitchen = recipe.kitchen;
  const conflicts = Array.isArray(kitchen?.dietary_conflicts)
    ? kitchen.dietary_conflicts
    : [];
  const ovenAdj = Array.isArray(kitchen?.oven_adjustments)
    ? kitchen.oven_adjustments
    : [];

  return (
    <article className="recipe-view">
      <figure className="recipe-cover">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={cover} alt="" />
        {recipe.image_credit && (
          <figcaption className="recipe-cover-credit">
            {recipe.image_credit_url ? (
              <a
                href={recipe.image_credit_url}
                target="_blank"
                rel="noreferrer noopener"
              >
                {recipe.image_credit}
              </a>
            ) : (
              recipe.image_credit
            )}
          </figcaption>
        )}
      </figure>

      <header className="recipe-view-head">
        <h2 className="recipe-title">{recipe.title}</h2>
        {recipe.servings != null && (
          <p className="muted">Serves {recipe.servings}</p>
        )}
        {recipe.description && <p>{recipe.description}</p>}
        <TrustStrip
          signals={{
            ...trustFromRecipe(recipe),
            calculatorHint: showWhatIf,
          }}
        />
        {savedNote && <p className="ok">{savedNote}</p>}
        {actions && <div className="recipe-actions">{actions}</div>}
      </header>

      <SafetyPanel safety={safety} overrides={recipe.safety_overrides} />

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
                  <p className="temp-chip" title="From safety table / step target">
                    Target internal: {temp}°C · code-checked
                  </p>
                )}
                <CitationList citations={s.citations} />
              </li>
            );
          })}
        </ol>
      </section>

      {showWhatIf && <RecipeWhatIf recipe={recipe} />}

      {(kitchen?.notes?.length || conflicts.length > 0 || ovenAdj.length > 0) && (
        <section>
          <h3>Adjusted for your kitchen</h3>
          {kitchen?.notes && kitchen.notes.length > 0 && (
            <ul>
              {kitchen.notes.map((n) => (
                <li key={n}>{n}</li>
              ))}
            </ul>
          )}
          {ovenAdj.length > 0 && (
            <ul>
              {ovenAdj.map((a, i) => (
                <li key={i}>{typeof a === "string" ? a : JSON.stringify(a)}</li>
              ))}
            </ul>
          )}
          {conflicts.length > 0 && (
            <div className="diet-conflicts">
              <h4>Dietary conflicts flagged</h4>
              <ul>
                {conflicts.map((c, i) => (
                  <li key={i}>
                    {typeof c === "string" ? c : JSON.stringify(c)}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      {recipe.grounding_note && (
        <p className="muted grounding">{recipe.grounding_note}</p>
      )}
    </article>
  );
}
