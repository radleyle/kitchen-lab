"use client";

import type { Citation, SafetyFact } from "@/lib/api";

/** Normalize whatever the API sent into typed citations. */
export function parseCitations(raw: unknown): Citation[] {
  if (!Array.isArray(raw)) return [];
  const out: Citation[] = [];
  for (const c of raw) {
    if (!c || typeof c !== "object") continue;
    const o = c as Record<string, unknown>;
    const source =
      o.source && typeof o.source === "object"
        ? (o.source as Record<string, unknown>)
        : null;
    out.push({
      claim: typeof o.claim === "string" ? o.claim : undefined,
      confidence: typeof o.confidence === "string" ? o.confidence : undefined,
      scope: typeof o.scope === "string" ? o.scope : undefined,
      source: source
        ? {
            title: typeof source.title === "string" ? source.title : undefined,
            author:
              typeof source.author === "string" ? source.author : undefined,
            url: typeof source.url === "string" ? source.url : undefined,
            authority_level:
              typeof source.authority_level === "string"
                ? source.authority_level
                : undefined,
          }
        : undefined,
    });
  }
  return out;
}

export function parseSafety(raw: unknown): SafetyFact | null {
  if (!raw || typeof raw !== "object") return null;
  const o = raw as Record<string, unknown>;
  if (typeof o.food !== "string" && o.min_internal_temp_c == null) return null;
  const source =
    o.source && typeof o.source === "object"
      ? (o.source as Record<string, unknown>)
      : null;
  return {
    food: typeof o.food === "string" ? o.food : "food",
    min_internal_temp_c:
      typeof o.min_internal_temp_c === "number" ? o.min_internal_temp_c : null,
    min_internal_temp_f:
      typeof o.min_internal_temp_f === "number" ? o.min_internal_temp_f : null,
    rest_time_min:
      typeof o.rest_time_min === "number" ? o.rest_time_min : null,
    source: source
      ? {
          title: typeof source.title === "string" ? source.title : undefined,
          url: typeof source.url === "string" ? source.url : undefined,
          authority_level:
            typeof source.authority_level === "string"
              ? source.authority_level
              : undefined,
          reviewed_at:
            typeof source.reviewed_at === "string"
              ? source.reviewed_at
              : undefined,
        }
      : undefined,
  };
}

function countCitations(steps: { citations?: unknown }[] | undefined): number {
  if (!steps) return 0;
  return steps.reduce((n, s) => n + parseCitations(s.citations).length, 0);
}

export type TrustSignals = {
  citationCount?: number;
  hasSafety?: boolean;
  safetyEnforced?: boolean;
  personalized?: boolean;
  kitchenNotes?: number;
  grounded?: boolean;
  calculatorHint?: boolean;
};

/** Badges that make the non-wrapper nature visible at a glance. */
export function TrustStrip({ signals }: { signals: TrustSignals }) {
  const badges: { key: string; label: string; title: string; kind: string }[] =
    [];

  if (signals.hasSafety || signals.safetyEnforced) {
    badges.push({
      key: "safety",
      label: signals.safetyEnforced
        ? "Code-enforced temp"
        : "Safety table",
      title:
        "Internal temperatures come from a deterministic USDA-backed table — the AI cannot invent them.",
      kind: "trust-badge--safety",
    });
  }
  if (signals.citationCount != null && signals.citationCount > 0) {
    badges.push({
      key: "citations",
      label: `${signals.citationCount} citation${signals.citationCount === 1 ? "" : "s"}`,
      title: "Science claims point back to curated passages with confidence.",
      kind: "trust-badge--cite",
    });
  }
  if (signals.calculatorHint) {
    badges.push({
      key: "calc",
      label: "Calculator math",
      title:
        "Amounts below are recomputed by deterministic Python calculators, not guessed by the model.",
      kind: "trust-badge--calc",
    });
  }
  if (signals.personalized || (signals.kitchenNotes ?? 0) > 0) {
    badges.push({
      key: "personal",
      label: "Your kitchen",
      title: "Adjusted using your profile (oven, diet, elevation, preferences).",
      kind: "trust-badge--personal",
    });
  }
  if (signals.grounded) {
    badges.push({
      key: "grounded",
      label: "KB-grounded",
      title: "Answer was checked against the curated knowledge base.",
      kind: "trust-badge--grounded",
    });
  }

  if (badges.length === 0) return null;

  return (
    <ul className="trust-strip" aria-label="Trust signals">
      {badges.map((b) => (
        <li key={b.key} className={`trust-badge ${b.kind}`} title={b.title}>
          {b.label}
        </li>
      ))}
    </ul>
  );
}

export function CitationList({ citations }: { citations: unknown }) {
  const items = parseCitations(citations);
  if (items.length === 0) return null;
  return (
    <div className="citations">
      <h4>Sources</h4>
      <ul>
        {items.map((cit, i) => {
          const title = cit.source?.title;
          const url = cit.source?.url;
          const authority = cit.source?.authority_level;
          return (
            <li key={i}>
              {cit.claim && <span className="cit-claim">{cit.claim}</span>}
              <span className="cit-src">
                {title && (
                  <>
                    —{" "}
                    {url ? (
                      <a href={url} target="_blank" rel="noreferrer noopener">
                        {title}
                      </a>
                    ) : (
                      title
                    )}
                  </>
                )}
                {authority ? ` · ${authority}` : ""}
                {cit.confidence ? ` · ${cit.confidence}` : ""}
                {cit.scope ? ` · scope: ${cit.scope}` : ""}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function SafetyPanel({
  safety,
  overrides,
}: {
  safety: SafetyFact | null;
  overrides?: unknown;
}) {
  const enforced = Array.isArray(overrides) && overrides.length > 0;
  if (!safety && !enforced) return null;

  return (
    <div className="safety-panel">
      {enforced && (
        <p className="safety-banner">
          Safety floor applied — an internal temperature was raised to meet
          USDA guidance (deterministic rule, not an AI guess).
        </p>
      )}
      {safety && (
        <div className="safety-fact">
          <h4>Safety table</h4>
          <p>
            <strong>{safety.food}</strong>
            {safety.min_internal_temp_c != null && (
              <>
                {" "}
                · min internal {safety.min_internal_temp_c}°C
                {safety.min_internal_temp_f != null
                  ? ` (${safety.min_internal_temp_f}°F)`
                  : ""}
              </>
            )}
            {safety.rest_time_min != null && safety.rest_time_min > 0 && (
              <> · rest {safety.rest_time_min} min</>
            )}
          </p>
          {safety.source?.title && (
            <p className="muted cit-src">
              Source:{" "}
              {safety.source.url ? (
                <a
                  href={safety.source.url}
                  target="_blank"
                  rel="noreferrer noopener"
                >
                  {safety.source.title}
                </a>
              ) : (
                safety.source.title
              )}
              {safety.source.authority_level
                ? ` · ${safety.source.authority_level}`
                : ""}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

/** Helpers for building TrustStrip from a recipe-shaped object. */
export function trustFromRecipe(recipe: {
  steps?: { citations?: unknown }[];
  safety?: unknown;
  safety_overrides?: unknown;
  kitchen?: { notes?: string[]; dietary_conflicts?: unknown[] } | null;
  personalized?: boolean;
  grounding_note?: string | null;
}): TrustSignals {
  const safety = parseSafety(recipe.safety);
  const notes = recipe.kitchen?.notes?.length ?? 0;
  const conflicts = Array.isArray(recipe.kitchen?.dietary_conflicts)
    ? recipe.kitchen.dietary_conflicts.length
    : 0;
  return {
    citationCount: countCitations(recipe.steps),
    hasSafety: safety != null,
    safetyEnforced:
      Array.isArray(recipe.safety_overrides) &&
      recipe.safety_overrides.length > 0,
    personalized: recipe.personalized || notes > 0 || conflicts > 0,
    kitchenNotes: notes,
    grounded: Boolean(recipe.grounding_note),
  };
}
