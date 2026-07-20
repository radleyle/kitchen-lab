"use client";

import { FormEvent, useEffect, useState } from "react";
import { FeatureGuide } from "@/components/FeatureGuide";
import {
  calcBakersPercentages,
  calcBrine,
  calcEquilibriumSalt,
  calcScale,
  calcVolumeToGrams,
} from "@/lib/api";

const SALT_TYPES = [
  { id: "table_salt", label: "Table salt" },
  { id: "morton_kosher_salt", label: "Morton kosher" },
  { id: "diamond_kosher_salt", label: "Diamond Crystal kosher" },
] as const;

const VOLUME_UNITS = ["cup", "tbsp", "tsp", "ml", "fl_oz"] as const;

const INGREDIENTS = [
  "water",
  "milk",
  "all_purpose_flour",
  "bread_flour",
  "granulated_sugar",
  "brown_sugar_packed",
  "butter",
  "vegetable_oil",
  "honey",
  "table_salt",
  "morton_kosher_salt",
  "diamond_kosher_salt",
  "cornstarch",
  "baking_soda",
] as const;

type ScaleRow = { name: string; amount: string; unit: string };

export default function CalculatorsPage() {
  // Brine (live slider)
  const [waterG, setWaterG] = useState("1000");
  const [brinePct, setBrinePct] = useState(5);
  const [saltType, setSaltType] = useState("table_salt");
  const [brineResult, setBrineResult] = useState<string | null>(null);
  const [brineError, setBrineError] = useState<string | null>(null);

  // Equilibrium / dry brine
  const [totalMassG, setTotalMassG] = useState("500");
  const [eqPct, setEqPct] = useState(2);
  const [eqResult, setEqResult] = useState<string | null>(null);
  const [eqError, setEqError] = useState<string | null>(null);

  // Scale
  const [origServings, setOrigServings] = useState("4");
  const [targetServings, setTargetServings] = useState(2);
  const [scaleRows, setScaleRows] = useState<ScaleRow[]>([
    { name: "flour", amount: "240", unit: "g" },
    { name: "water", amount: "180", unit: "g" },
    { name: "salt", amount: "5", unit: "g" },
  ]);
  const [scaleResult, setScaleResult] = useState<string | null>(null);
  const [scaleError, setScaleError] = useState<string | null>(null);

  // Baker's % (live hydration via water slider)
  const [flourG, setFlourG] = useState("500");
  const [waterBakeG, setWaterBakeG] = useState(375);
  const [saltBakeG, setSaltBakeG] = useState("10");
  const [bakersResult, setBakersResult] = useState<string | null>(null);
  const [bakersError, setBakersError] = useState<string | null>(null);

  // Volume → grams
  const [volAmount, setVolAmount] = useState("1");
  const [volUnit, setVolUnit] = useState("cup");
  const [volIngredient, setVolIngredient] = useState("all_purpose_flour");
  const [volResult, setVolResult] = useState<string | null>(null);
  const [volError, setVolError] = useState<string | null>(null);
  const [volBusy, setVolBusy] = useState(false);

  useEffect(() => {
    const w = Number(waterG);
    if (!Number.isFinite(w) || w <= 0) {
      setBrineResult(null);
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
        setBrineResult(
          `${r.salt_g} g salt (${r.salt_tbsp} tbsp ${r.salt_type.replace(/_/g, " ")})`,
        );
      })
      .catch((err) => {
        if (!cancelled) {
          setBrineResult(null);
          setBrineError(err instanceof Error ? err.message : "Brine failed");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [waterG, brinePct, saltType]);

  useEffect(() => {
    const m = Number(totalMassG);
    if (!Number.isFinite(m) || m <= 0) {
      setEqResult(null);
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
        setEqResult(
          `${r.salt_g} g salt (${r.salt_tbsp} tbsp) at ${r.target_percent}% of total mass`,
        );
      })
      .catch((err) => {
        if (!cancelled) {
          setEqResult(null);
          setEqError(
            err instanceof Error ? err.message : "Equilibrium calc failed",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [totalMassG, eqPct, saltType]);

  useEffect(() => {
    const ingredients = scaleRows
      .filter((r) => r.name.trim() && r.amount.trim())
      .map((r) => ({
        name: r.name.trim(),
        amount: Number(r.amount),
        unit: r.unit.trim() || "g",
      }));
    if (ingredients.length === 0) {
      setScaleResult(null);
      return;
    }
    const orig = Number(origServings);
    if (!Number.isFinite(orig) || orig <= 0) return;
    let cancelled = false;
    calcScale({
      ingredients,
      original_servings: orig,
      target_servings: targetServings,
    })
      .then((rows) => {
        if (cancelled) return;
        setScaleError(null);
        setScaleResult(
          rows
            .map(
              (r) =>
                `${r.name}: ${r.amount} ${r.unit}` +
                (r.note ? ` (${r.note})` : ""),
            )
            .join("\n"),
        );
      })
      .catch((err) => {
        if (!cancelled) {
          setScaleResult(null);
          setScaleError(err instanceof Error ? err.message : "Scale failed");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [scaleRows, origServings, targetServings]);

  useEffect(() => {
    const flour = Number(flourG);
    const salt = Number(saltBakeG);
    if (!Number.isFinite(flour) || flour <= 0) {
      setBakersResult(null);
      return;
    }
    let cancelled = false;
    calcBakersPercentages({
      ingredients_g: {
        "bread flour": flour,
        water: waterBakeG,
        salt: Number.isFinite(salt) ? salt : 0,
      },
    })
      .then((r) => {
        if (cancelled) return;
        setBakersError(null);
        const lines = Object.entries(r.percentages).map(
          ([name, pct]) => `${name}: ${pct}%`,
        );
        lines.push(`Hydration: ${r.hydration_percent}%`);
        setBakersResult(lines.join("\n"));
      })
      .catch((err) => {
        if (!cancelled) {
          setBakersResult(null);
          setBakersError(
            err instanceof Error ? err.message : "Baker’s % failed",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [flourG, waterBakeG, saltBakeG]);

  async function onVolume(e: FormEvent) {
    e.preventDefault();
    setVolBusy(true);
    setVolError(null);
    setVolResult(null);
    try {
      const r = await calcVolumeToGrams({
        amount: Number(volAmount),
        unit: volUnit,
        ingredient: volIngredient,
      });
      setVolResult(`${r.grams} g`);
    } catch (err) {
      setVolError(err instanceof Error ? err.message : "Conversion failed");
    } finally {
      setVolBusy(false);
    }
  }

  const flourNum = Number(flourG) || 500;
  const hydrationApprox =
    flourNum > 0 ? Math.round((waterBakeG / flourNum) * 1000) / 10 : 0;

  return (
    <main className="shell calc-page">
      <header className="page-header">
        <h1>Calculators</h1>
        <p className="lede">
          Punch in numbers, get exact amounts. This is the kitchen scale on the
          wall — not a chatbot guessing. Drag the sliders for live what-ifs.
        </p>
        <nav className="lab-jump" aria-label="Calculator sections">
          <a href="#brine">Brine</a>
          <a href="#equilibrium">Dry salt</a>
          <a href="#scale">Scale</a>
          <a href="#bakers">Baker’s %</a>
          <a href="#volume">Volume → g</a>
        </nav>
        <FeatureGuide
          title="Why these calculators exist"
          summary="Cooking science often talks in grams and percentages. These tools do the arithmetic so you don’t have to — and so an AI can’t invent a wrong number."
          when="Use them when a recipe or article says “5% brine” or “75% hydration” and you need real amounts for your kitchen."
          terms={[
            {
              term: "Grams (g)",
              meaning:
                "Weight. More reliable than cups for baking and brining. 1 liter of water ≈ 1000 g.",
            },
            {
              term: "Percent (%) in brine / baking",
              meaning:
                "Parts per hundred. A 5% brine means 5 g salt per 100 g water. Baker’s % means each ingredient relative to flour weight (flour = 100%).",
            },
            {
              term: "Hydration",
              meaning:
                "How wet a dough is: water weight ÷ flour weight × 100. Higher % = stickier, more open crumb (usually).",
            },
          ]}
        />
      </header>

      <section id="brine" className="lab-section panel">
        <h2>Brine (what-if)</h2>
        <p className="field-hint">
          <strong>When:</strong> You’re wet-brining chicken, turkey, or pork.
          Drag brine % — salt grams update from Python, instantly.
        </p>
        <div className="stack-form">
          <label>
            Water (grams)
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
          {brineResult && <p className="calc-result">{brineResult}</p>}
          <p className="muted trust-calc-note">
            Deterministic calculator · not an LLM estimate
          </p>
        </div>
      </section>

      <section id="equilibrium" className="lab-section panel">
        <h2>Dry / equilibrium salt</h2>
        <p className="field-hint">
          Salt as a percent of <em>total meat mass</em> (typical ~2%). Different
          math from a wet brine — used for dry-brining.
        </p>
        <div className="stack-form">
          <label>
            Meat mass (g)
            <input
              type="number"
              min={1}
              step="any"
              value={totalMassG}
              onChange={(e) => setTotalMassG(e.target.value)}
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
          {eqResult && <p className="calc-result">{eqResult}</p>}
        </div>
      </section>

      <section id="scale" className="lab-section panel">
        <h2>Scale a recipe</h2>
        <p className="field-hint">
          Drag target servings — amounts rescale live. Cook time and pan size
          often don’t scale the same way.
        </p>
        <div className="stack-form">
          <div className="calc-row-2">
            <label>
              Original servings
              <input
                type="number"
                min={1}
                value={origServings}
                onChange={(e) => setOrigServings(e.target.value)}
              />
            </label>
            <label className="what-if-label">
              Target: <strong>{targetServings}</strong>
              <input
                type="range"
                min={1}
                max={16}
                step={1}
                value={targetServings}
                onChange={(e) => setTargetServings(Number(e.target.value))}
              />
            </label>
          </div>
          {scaleRows.map((row, i) => (
            <div key={i} className="calc-ing-row">
              <input
                aria-label={`Ingredient ${i + 1} name`}
                placeholder="name"
                value={row.name}
                onChange={(e) =>
                  setScaleRows((rows) =>
                    rows.map((r, j) =>
                      j === i ? { ...r, name: e.target.value } : r,
                    ),
                  )
                }
              />
              <input
                aria-label={`Ingredient ${i + 1} amount`}
                type="number"
                min={0}
                step="any"
                placeholder="amount"
                value={row.amount}
                onChange={(e) =>
                  setScaleRows((rows) =>
                    rows.map((r, j) =>
                      j === i ? { ...r, amount: e.target.value } : r,
                    ),
                  )
                }
              />
              <input
                aria-label={`Ingredient ${i + 1} unit`}
                placeholder="unit"
                value={row.unit}
                onChange={(e) =>
                  setScaleRows((rows) =>
                    rows.map((r, j) =>
                      j === i ? { ...r, unit: e.target.value } : r,
                    ),
                  )
                }
              />
            </div>
          ))}
          <button
            type="button"
            className="text-btn"
            onClick={() =>
              setScaleRows((rows) => [
                ...rows,
                { name: "", amount: "", unit: "g" },
              ])
            }
          >
            + Add ingredient row
          </button>
          {scaleError && <p className="error">{scaleError}</p>}
          {scaleResult && (
            <pre className="calc-result pre">{scaleResult}</pre>
          )}
        </div>
      </section>

      <section id="bakers" className="lab-section panel">
        <h2>Baker’s percentages</h2>
        <p className="field-hint">
          Drag water to explore hydration. Flour stays the 100% baseline.
        </p>
        <div className="stack-form">
          <label>
            Bread flour (g)
            <input
              type="number"
              min={1}
              step="any"
              value={flourG}
              onChange={(e) => setFlourG(e.target.value)}
            />
          </label>
          <label className="what-if-label">
            Water (g): <strong>{waterBakeG}</strong>
            <span className="muted"> · ~{hydrationApprox}% hydration</span>
            <input
              type="range"
              min={Math.round(flourNum * 0.5)}
              max={Math.round(flourNum * 1.0)}
              step={5}
              value={waterBakeG}
              onChange={(e) => setWaterBakeG(Number(e.target.value))}
            />
          </label>
          <label>
            Salt (g)
            <input
              type="number"
              min={0}
              step="any"
              value={saltBakeG}
              onChange={(e) => setSaltBakeG(e.target.value)}
            />
          </label>
          {bakersError && <p className="error">{bakersError}</p>}
          {bakersResult && (
            <pre className="calc-result pre">{bakersResult}</pre>
          )}
        </div>
      </section>

      <section id="volume" className="lab-section panel">
        <h2>Volume → grams</h2>
        <p className="field-hint">
          <strong>When:</strong> A recipe says “1 cup flour” but you want to
          weigh it. Densities differ by ingredient — still approximate.
        </p>
        <form className="stack-form" onSubmit={onVolume}>
          <div className="calc-row-2">
            <label>
              Amount
              <input
                type="number"
                min={0.01}
                step="any"
                value={volAmount}
                onChange={(e) => setVolAmount(e.target.value)}
                required
              />
            </label>
            <label>
              Unit
              <select
                value={volUnit}
                onChange={(e) => setVolUnit(e.target.value)}
              >
                {VOLUME_UNITS.map((u) => (
                  <option key={u} value={u}>
                    {u}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label>
            Ingredient
            <select
              value={volIngredient}
              onChange={(e) => setVolIngredient(e.target.value)}
            >
              {INGREDIENTS.map((ing) => (
                <option key={ing} value={ing}>
                  {ing.replace(/_/g, " ")}
                </option>
              ))}
            </select>
          </label>
          {volError && <p className="error">{volError}</p>}
          {volResult && <p className="calc-result">{volResult}</p>}
          <button type="submit" disabled={volBusy}>
            {volBusy ? "Calculating…" : "Convert to grams"}
          </button>
        </form>
      </section>
    </main>
  );
}
