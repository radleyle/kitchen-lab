"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { FeatureGuide } from "@/components/FeatureGuide";
import { RecipeView } from "@/components/RecipeView";
import {
  generateRecipe,
  getRecipe,
  listMyRecipes,
  type GeneratedRecipe,
  type RecipeSummary,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { FOOD_IMAGES, imageForId } from "@/lib/images";

const EXAMPLES = [
  "Crispy-skin salmon for 2 with a simple pan sauce",
  "Weeknight stir-fried chicken, velveted, with broccoli",
  "No-knead bread for beginners",
  "Vegetarian chili that actually tastes deep",
];

export default function RecipesPage() {
  const { user, loading: authLoading } = useAuth();
  const [request, setRequest] = useState("");
  const [servings, setServings] = useState("2");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recipe, setRecipe] = useState<GeneratedRecipe | null>(null);
  const [savedNote, setSavedNote] = useState<string | null>(null);
  const [library, setLibrary] = useState<RecipeSummary[]>([]);
  const [libraryError, setLibraryError] = useState<string | null>(null);

  async function refreshLibrary() {
    if (!user) {
      setLibrary([]);
      return;
    }
    try {
      setLibrary(await listMyRecipes());
      setLibraryError(null);
    } catch (err) {
      setLibraryError(
        err instanceof Error ? err.message : "Could not load saved recipes",
      );
    }
  }

  useEffect(() => {
    if (authLoading) return;
    void refreshLibrary();
  }, [user, authLoading]);

  async function onGenerate(e: FormEvent) {
    e.preventDefault();
    const q = request.trim();
    if (!q || busy) return;
    setBusy(true);
    setError(null);
    setSavedNote(null);
    setRecipe(null);
    try {
      const servingsN = Number(servings);
      const result = await generateRecipe({
        request: q,
        servings:
          Number.isFinite(servingsN) && servingsN >= 1 ? servingsN : undefined,
      });
      setRecipe(result);
      if (result.feasible && result.recipe_id != null) {
        if (user) {
          setSavedNote(
            `Saved to your cookbook as recipe #${result.recipe_id}.`,
          );
          await refreshLibrary();
        } else {
          setSavedNote(
            "Generated (not kept in a personal cookbook). Sign in on My kitchen, then generate again to save.",
          );
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setBusy(false);
    }
  }

  async function openSaved(id: number) {
    setError(null);
    setSavedNote(`Loaded saved recipe #${id}.`);
    try {
      setRecipe(await getRecipe(id));
      document.getElementById("generate")?.scrollIntoView({ behavior: "smooth" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open recipe");
    }
  }

  return (
    <main className="recipes-page">
      <header className="page-banner">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/images/pasta.jpg" alt="" className="page-banner-media" />
        <div className="page-banner-scrim" aria-hidden />
        <div className="page-banner-content shell">
          <h1>Recipes</h1>
          <p className="lede">
            Science-annotated recipes from the knowledge base — every step
            explains why, not just what.
          </p>
        </div>
      </header>

      <div className="shell">
        <FeatureGuide
          title="How recipe generation works"
          summary="Not a random blog recipe. KitchenLab drafts a plan, grounds step science in cited passages, and enforces USDA internal-temp safety in code."
          when="Use this when you want a full dish with teaching built in — not just Ask’s short answer."
          steps={[
            "Sign in (My kitchen) if you want recipes kept in your cookbook.",
            "Describe the dish, constraints, or ingredients you have.",
            "Read each step’s Why + Science before you cook.",
            "Open saved recipes anytime from Your cookbook below.",
          ]}
          terms={[
            {
              term: "Why vs Science",
              meaning:
                "Why = practical kitchen reason. Science = the mechanism (Maillard, protein coagulation, starch gelatinization…).",
            },
            {
              term: "Safety floor",
              meaning:
                "If a step’s internal temperature is below USDA guidance, Python raises it. The model cannot override that.",
            },
            {
              term: "Save",
              meaning:
                "When you’re signed in, every successful generate is stored under your account automatically.",
            },
          ]}
        />

        <section id="generate" className="lab-section">
          <h2>Generate</h2>
          <form className="ask-form recipe-form" onSubmit={onGenerate}>
            <label htmlFor="recipe-req" className="sr-only">
              What do you want to cook?
            </label>
            <textarea
              id="recipe-req"
              rows={4}
              value={request}
              onChange={(e) => setRequest(e.target.value)}
              placeholder="e.g. Juicy roast chicken for 4, crispy skin, weeknight-friendly…"
              disabled={busy}
            />
            <label className="servings-field">
              Servings
              <input
                type="number"
                min={1}
                max={50}
                value={servings}
                onChange={(e) => setServings(e.target.value)}
                disabled={busy}
              />
            </label>
            <button type="submit" disabled={busy || request.trim().length < 5}>
              {busy ? "Generating…" : "Generate recipe"}
            </button>
          </form>

          {!user && !authLoading && (
            <p className="auth-hint muted">
              Tip: <Link href="/kitchen">Sign in</Link> so generated recipes
              land in your cookbook.
            </p>
          )}

          {error && <p className="error">{error}</p>}

          {recipe && (
            <div className="recipe-result">
              <RecipeView recipe={recipe} savedNote={savedNote} />
            </div>
          )}

          {!recipe && (
            <div className="prompt-mosaic" aria-label="Example prompts">
              {EXAMPLES.map((ex, i) => (
                <button
                  key={ex}
                  type="button"
                  className="mosaic-tile"
                  disabled={busy}
                  onClick={() => setRequest(ex)}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={FOOD_IMAGES[i % FOOD_IMAGES.length]} alt="" />
                  <span>{ex}</span>
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="lab-section cookbook" aria-labelledby="cookbook-h">
          <h2 id="cookbook-h">Your cookbook</h2>
          {!user && (
            <p className="muted">
              <Link href="/kitchen">Sign in</Link> to keep and browse generated
              recipes here.
            </p>
          )}
          {user && libraryError && <p className="error">{libraryError}</p>}
          {user && library.length === 0 && !libraryError && (
            <p className="muted">No saved recipes yet — generate one above.</p>
          )}
          {user && library.length > 0 && (
            <ul className="recipe-grid">
              {library.map((r) => (
                <li key={r.id}>
                  <button
                    type="button"
                    className="recipe-card"
                    onClick={() => openSaved(r.id)}
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={imageForId(r.id)} alt="" />
                    <span className="recipe-card-body">
                      <strong>{r.title}</strong>
                      <span className="muted">
                        {r.servings != null
                          ? `Serves ${r.servings}`
                          : "Saved recipe"}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </main>
  );
}
