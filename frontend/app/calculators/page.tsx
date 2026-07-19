"use client";

import { FormEvent, useState } from "react";
import { FeatureGuide } from "@/components/FeatureGuide";
import {
  calcBakersPercentages,
  calcBrine,
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
  // Brine
  const [waterG, setWaterG] = useState("1000");
  const [brinePct, setBrinePct] = useState("5");
  const [saltType, setSaltType] = useState("table_salt");
  const [brineResult, setBrineResult] = useState<string | null>(null);
  const [brineError, setBrineError] = useState<string | null>(null);
  const [brineBusy, setBrineBusy] = useState(false);

  // Scale
  const [origServings, setOrigServings] = useState("4");
  const [targetServings, setTargetServings] = useState("2");
  const [scaleRows, setScaleRows] = useState<ScaleRow[]>([
    { name: "flour", amount: "240", unit: "g" },
    { name: "water", amount: "180", unit: "g" },
    { name: "salt", amount: "5", unit: "g" },
  ]);
  const [scaleResult, setScaleResult] = useState<string | null>(null);
  const [scaleError, setScaleError] = useState<string | null>(null);
  const [scaleBusy, setScaleBusy] = useState(false);

  // Baker's %
  const [flourG, setFlourG] = useState("500");
  const [waterBakeG, setWaterBakeG] = useState("375");
  const [saltBakeG, setSaltBakeG] = useState("10");
  const [bakersResult, setBakersResult] = useState<string | null>(null);
  const [bakersError, setBakersError] = useState<string | null>(null);
  const [bakersBusy, setBakersBusy] = useState(false);

  // Volume → grams
  const [volAmount, setVolAmount] = useState("1");
  const [volUnit, setVolUnit] = useState("cup");
  const [volIngredient, setVolIngredient] = useState("all_purpose_flour");
  const [volResult, setVolResult] = useState<string | null>(null);
  const [volError, setVolError] = useState<string | null>(null);
  const [volBusy, setVolBusy] = useState(false);

  async function onBrine(e: FormEvent) {
    e.preventDefault();
    setBrineBusy(true);
    setBrineError(null);
    setBrineResult(null);
    try {
      const r = await calcBrine({
        water_g: Number(waterG),
        brine_percent: Number(brinePct),
        salt_type: saltType,
      });
      setBrineResult(
        `${r.salt_g} g salt (${r.salt_tbsp} tbsp ${r.salt_type.replace(/_/g, " ")})`,
      );
    } catch (err) {
      setBrineError(err instanceof Error ? err.message : "Brine failed");
    } finally {
      setBrineBusy(false);
    }
  }

  async function onScale(e: FormEvent) {
    e.preventDefault();
    setScaleBusy(true);
    setScaleError(null);
    setScaleResult(null);
    try {
      const ingredients = scaleRows
        .filter((r) => r.name.trim() && r.amount.trim())
        .map((r) => ({
          name: r.name.trim(),
          amount: Number(r.amount),
          unit: r.unit.trim() || "g",
        }));
      if (ingredients.length === 0) {
        setScaleError("Add at least one ingredient.");
        return;
      }
      const rows = await calcScale({
        ingredients,
        original_servings: Number(origServings),
        target_servings: Number(targetServings),
      });
      setScaleResult(
        rows
          .map(
            (r) =>
              `${r.name}: ${r.amount} ${r.unit}` +
              (r.note ? ` (${r.note})` : ""),
          )
          .join("\n"),
      );
    } catch (err) {
      setScaleError(err instanceof Error ? err.message : "Scale failed");
    } finally {
      setScaleBusy(false);
    }
  }

  async function onBakers(e: FormEvent) {
    e.preventDefault();
    setBakersBusy(true);
    setBakersError(null);
    setBakersResult(null);
    try {
      const r = await calcBakersPercentages({
        ingredients_g: {
          "bread flour": Number(flourG),
          water: Number(waterBakeG),
          salt: Number(saltBakeG),
        },
      });
      const lines = Object.entries(r.percentages).map(
        ([name, pct]) => `${name}: ${pct}%`,
      );
      lines.push(`Hydration: ${r.hydration_percent}%`);
      setBakersResult(lines.join("\n"));
    } catch (err) {
      setBakersError(err instanceof Error ? err.message : "Baker’s % failed");
    } finally {
      setBakersBusy(false);
    }
  }

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

  return (
    <main className="shell calc-page">
      <header className="page-header">
        <h1>Calculators</h1>
        <p className="lede">
          Punch in numbers, get exact amounts. This is the kitchen scale on the
          wall — not a chatbot guessing.
        </p>
        <nav className="lab-jump" aria-label="Calculator sections">
          <a href="#brine">Brine</a>
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
        <h2>Brine</h2>
        <p className="field-hint">
          <strong>When:</strong> You’re wet-brining chicken, turkey, or pork and
          need “how much salt for this much water.” Typical dinner brines are
          often around 5–8%. (1 L water ≈ 1000 g.)
        </p>
        <form className="stack-form" onSubmit={onBrine}>
          <label>
            Water (grams)
            <input
              type="number"
              min={1}
              step="any"
              value={waterG}
              onChange={(e) => setWaterG(e.target.value)}
              required
            />
          </label>
          <label>
            Brine %
            <input
              type="number"
              min={0.1}
              max={26}
              step="any"
              value={brinePct}
              onChange={(e) => setBrinePct(e.target.value)}
              required
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
          <button type="submit" disabled={brineBusy}>
            {brineBusy ? "Calculating…" : "Calculate salt"}
          </button>
        </form>
      </section>

      <section id="scale" className="lab-section panel">
        <h2>Scale a recipe</h2>
        <p className="field-hint">
          <strong>When:</strong> The recipe feeds 4 and you’re cooking for 2 (or
          a crowd). Amounts scale linearly; cook time and pan size often don’t —
          we’ll flag salt/leavening when the jump is big.
        </p>
        <form className="stack-form" onSubmit={onScale}>
          <div className="calc-row-2">
            <label>
              Original servings
              <input
                type="number"
                min={1}
                value={origServings}
                onChange={(e) => setOrigServings(e.target.value)}
                required
              />
            </label>
            <label>
              Target servings
              <input
                type="number"
                min={1}
                value={targetServings}
                onChange={(e) => setTargetServings(e.target.value)}
                required
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
          <button type="submit" disabled={scaleBusy}>
            {scaleBusy ? "Calculating…" : "Scale recipe"}
          </button>
        </form>
      </section>

      <section id="bakers" className="lab-section panel">
        <h2>Baker’s percentages</h2>
        <p className="field-hint">
          <strong>When:</strong> You’re comparing bread/pizza doughs or
          following a formula written as “flour 100%, water 70%…”. Enter your
          gram weights; we translate to baker’s % and hydration.
        </p>
        <form className="stack-form" onSubmit={onBakers}>
          <label>
            Bread flour (g)
            <input
              type="number"
              min={1}
              step="any"
              value={flourG}
              onChange={(e) => setFlourG(e.target.value)}
              required
            />
          </label>
          <label>
            Water (g)
            <input
              type="number"
              min={0}
              step="any"
              value={waterBakeG}
              onChange={(e) => setWaterBakeG(e.target.value)}
              required
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
              required
            />
          </label>
          {bakersError && <p className="error">{bakersError}</p>}
          {bakersResult && (
            <pre className="calc-result pre">{bakersResult}</pre>
          )}
          <button type="submit" disabled={bakersBusy}>
            {bakersBusy ? "Calculating…" : "Calculate percentages"}
          </button>
        </form>
      </section>

      <section id="volume" className="lab-section panel">
        <h2>Volume → grams</h2>
        <p className="field-hint">
          <strong>When:</strong> A recipe says “1 cup flour” but you want to
          weigh it. Densities differ by ingredient — still approximate (scooping
          style matters).
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
