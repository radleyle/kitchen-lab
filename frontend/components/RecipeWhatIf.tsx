"use client";

import { useEffect, useMemo, useState } from "react";
import {
  calcBrine,
  calcEquilibriumSalt,
  calcScale,
  type GeneratedRecipe,
} from "@/lib/api";

const SALT_TYPES = [
  { id: "table_salt", label: "Table salt" },
  { id: "morton_kosher_salt", label: "Morton kosher" },
  { id: "diamond_kosher_salt", label: "Diamond Crystal" },
] as const;

function waterGramsFromRecipe(recipe: GeneratedRecipe): number | null {
  const hit = (recipe.ingredients ?? []).find((ing) => {
    const name = ing.ingredient.toLowerCase();
    return name === "water" || name.includes("water");
  });
  if (hit?.grams != null && hit.grams > 0) return hit.grams;
  return null;
}

function scaleableIngredients(recipe: GeneratedRecipe) {
  return (recipe.ingredients ?? [])
    .filter((ing) => ing.grams != null && ing.grams > 0)
    .map((ing) => ({
      name: ing.ingredient,
      amount: Number(ing.grams),
      unit: "g",
    }));
}

/**
 * What-if panel: sliders call the same Python calculators as /calculators.
 * Analogy: turning the oven dial and watching the thermometer — numbers are
 * measured by code, not guessed by the chat model.
 */
export function RecipeWhatIf({ recipe }: { recipe: GeneratedRecipe }) {
  const baseServings = recipe.servings && recipe.servings > 0 ? recipe.servings : 2;
  const scalable = useMemo(() => scaleableIngredients(recipe), [recipe]);
  const recipeWater = waterGramsFromRecipe(recipe);

  const [targetServings, setTargetServings] = useState(baseServings);
  const [scaledLines, setScaledLines] = useState<string[] | null>(null);
  const [scaleError, setScaleError] = useState<string | null>(null);

  const [waterG, setWaterG] = useState(String(recipeWater ?? 1000));
  const [brinePct, setBrinePct] = useState(5);
  const [saltType, setSaltType] = useState<string>("table_salt");
  const [brineLine, setBrineLine] = useState<string | null>(null);
  const [brineError, setBrineError] = useState<string | null>(null);

  const [meatG, setMeatG] = useState("500");
  const [eqPct, setEqPct] = useState(2);
  const [eqLine, setEqLine] = useState<string | null>(null);
  const [eqError, setEqError] = useState<string | null>(null);

  useEffect(() => {
    setTargetServings(baseServings);
  }, [baseServings, recipe.title]);

  useEffect(() => {
    if (scalable.length === 0) {
      setScaledLines(null);
      return;
    }
    let cancelled = false;
    calcScale({
      ingredients: scalable,
      original_servings: baseServings,
      target_servings: targetServings,
    })
      .then((rows) => {
        if (cancelled) return;
        setScaleError(null);
        setScaledLines(
          rows.map(
            (r) =>
              `${r.name}: ${r.amount} ${r.unit}` +
              (r.note ? ` (${r.note})` : ""),
          ),
        );
      })
      .catch((err) => {
        if (!cancelled) {
          setScaledLines(null);
          setScaleError(
            err instanceof Error ? err.message : "Scale failed",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [scalable, baseServings, targetServings]);

  useEffect(() => {
    const w = Number(waterG);
    if (!Number.isFinite(w) || w <= 0) {
      setBrineLine(null);
      return;
    }
    let cancelled = false;
    calcBrine({
      water_g: w,
      brine_percent: brinePct,
      salt_type: saltType,
    })
      .then((r) => {
        if (cancelled) return;
        setBrineError(null);
        setBrineLine(
          `${r.salt_g} g salt (${r.salt_tbsp} tbsp ${r.salt_type.replace(/_/g, " ")})`,
        );
      })
      .catch((err) => {
        if (!cancelled) {
          setBrineLine(null);
          setBrineError(
            err instanceof Error ? err.message : "Brine calc failed",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [waterG, brinePct, saltType]);

  useEffect(() => {
    const m = Number(meatG);
    if (!Number.isFinite(m) || m <= 0) {
      setEqLine(null);
      return;
    }
    let cancelled = false;
    calcEquilibriumSalt({
      total_mass_g: m,
      target_percent: eqPct,
      salt_type: saltType,
    })
      .then((r) => {
        if (cancelled) return;
        setEqError(null);
        setEqLine(
          `${r.salt_g} g salt (${r.salt_tbsp} tbsp) at ${r.target_percent}% of total mass`,
        );
      })
      .catch((err) => {
        if (!cancelled) {
          setEqLine(null);
          setEqError(
            err instanceof Error ? err.message : "Equilibrium calc failed",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [meatG, eqPct, saltType]);

  return (
    <section className="what-if" aria-labelledby="what-if-heading">
      <h3 id="what-if-heading">What if…</h3>
      <p className="field-hint">
        Drag a slider — salt and scaled grams update from KitchenLab’s
        calculators (Python math), not from the language model.
      </p>

      {scalable.length > 0 && (
        <div className="what-if-block">
          <label className="what-if-label">
            Servings: <strong>{targetServings}</strong>
            <span className="muted"> (was {baseServings})</span>
            <input
              type="range"
              min={1}
              max={Math.max(12, baseServings * 3)}
              step={1}
              value={targetServings}
              onChange={(e) => setTargetServings(Number(e.target.value))}
            />
          </label>
          {scaleError && <p className="error">{scaleError}</p>}
          {scaledLines && (
            <ul className="what-if-result">
              {scaledLines.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="what-if-block">
        <h4>Wet brine strength</h4>
        <label>
          Water (g)
          <input
            type="number"
            min={1}
            step="any"
            value={waterG}
            onChange={(e) => setWaterG(e.target.value)}
          />
        </label>
        <label className="what-if-label">
          Brine %: <strong>{brinePct}</strong>
          <input
            type="range"
            min={1}
            max={12}
            step={0.5}
            value={brinePct}
            onChange={(e) => setBrinePct(Number(e.target.value))}
          />
        </label>
        <label>
          Salt type
          <select
            value={saltType}
            onChange={(e) => setSaltType(e.target.value)}
          >
            {SALT_TYPES.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        {brineError && <p className="error">{brineError}</p>}
        {brineLine && <p className="calc-result">{brineLine}</p>}
      </div>

      <div className="what-if-block">
        <h4>Dry / equilibrium salt</h4>
        <p className="field-hint">
          Percent of total meat mass (typical ~2%) — different formula from
          wet brine.
        </p>
        <label>
          Meat mass (g)
          <input
            type="number"
            min={1}
            step="any"
            value={meatG}
            onChange={(e) => setMeatG(e.target.value)}
          />
        </label>
        <label className="what-if-label">
          Target %: <strong>{eqPct}</strong>
          <input
            type="range"
            min={0.5}
            max={3}
            step={0.1}
            value={eqPct}
            onChange={(e) => setEqPct(Number(e.target.value))}
          />
        </label>
        {eqError && <p className="error">{eqError}</p>}
        {eqLine && <p className="calc-result">{eqLine}</p>}
      </div>
    </section>
  );
}
