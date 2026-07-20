"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { FeatureGuide } from "@/components/FeatureGuide";
import { RecipeView } from "@/components/RecipeView";
import {
  deleteRecipe,
  generateRecipe,
  getRecipe,
  listMyRecipes,
  saveRecipe,
  type GeneratedRecipe,
  type RecipeSummary,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useConfirm } from "@/lib/confirm";
import { recipeCoverUrl } from "@/lib/images";

/** Example prompts with matched local photos (not random stock). */
const EXAMPLES = [
  {
    prompt: "Crispy-skin salmon for 2 with a simple pan sauce",
    image: "/images/salmon.jpg",
  },
  {
    prompt: "Weeknight stir-fried chicken, velveted, with broccoli",
    image: "/images/stirfry.jpg",
  },
  {
    prompt: "No-knead bread for beginners",
    image: "/images/bread.jpg",
  },
  {
    prompt: "Vegetarian chili that actually tastes deep",
    image: "/images/chili.jpg",
  },
] as const;

export default function RecipesPage() {
  const { user, loading: authLoading } = useAuth();
  const confirm = useConfirm();
  const [request, setRequest] = useState("");
  const [servings, setServings] = useState("2");
  const [busy, setBusy] = useState(false);
  const [saveBusy, setSaveBusy] = useState(false);
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
      if (result.feasible) {
        setSavedNote(
          user
            ? "Draft ready — click Save to cookbook if you want to keep it."
            : "Draft ready. Sign in on My kitchen, then Save to keep it in your cookbook.",
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setBusy(false);
    }
  }

  async function onSave() {
    if (!recipe?.feasible || !recipe.title || saveBusy) return;
    if (!user) {
      setError("Sign in on My kitchen to save recipes to your cookbook.");
      return;
    }
    setSaveBusy(true);
    setError(null);
    try {
      const saved = await saveRecipe({
        title: recipe.title,
        description: recipe.description,
        servings: recipe.servings,
        ingredients: recipe.ingredients,
        steps: recipe.steps,
        image_url: recipe.image_url,
        image_credit: recipe.image_credit,
        image_credit_url: recipe.image_credit_url,
      });
      setRecipe({
        ...recipe,
        recipe_id: saved.id,
        saved: true,
        image_url: saved.image_url ?? recipe.image_url,
        image_credit: saved.image_credit ?? recipe.image_credit,
        image_credit_url: saved.image_credit_url ?? recipe.image_credit_url,
      });
      setSavedNote(`Saved to your cookbook as recipe #${saved.id}.`);
      await refreshLibrary();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save recipe");
    } finally {
      setSaveBusy(false);
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

  async function onDelete(id: number) {
    if (!user) return;
    const ok = await confirm({
      title: "Delete recipe?",
      message:
        "This removes the recipe from your cookbook. You can’t undo this.",
      confirmLabel: "Delete",
      danger: true,
    });
    if (!ok) return;
    setError(null);
    try {
      await deleteRecipe(id);
      if (recipe?.recipe_id === id) {
        setRecipe((r) => (r ? { ...r, recipe_id: null, saved: false } : r));
        setSavedNote("Removed from your cookbook.");
      }
      await refreshLibrary();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete recipe");
    }
  }

  const canSave =
    !!recipe?.feasible &&
    !recipe.saved &&
    recipe.recipe_id == null &&
    !!recipe.title;

  return (
    <main className="shell recipes-page">
      <header className="page-header">
        <h1>Recipes</h1>
        <p className="lede">
          Science-annotated recipes from the knowledge base — every step
          explains why, not just what.
        </p>
      </header>

      <FeatureGuide
        title="How recipe generation works"
        summary="Not a random blog recipe. KitchenLab drafts a plan, grounds step science in cited passages, and enforces USDA internal-temp safety in code."
        when="Use this when you want a full dish with teaching built in — not just Ask’s short answer."
        steps={[
          "Describe the dish, constraints, or ingredients you have.",
          "Read each step’s Why + Science before you cook.",
          "Sign in, then click Save to cookbook only if you want to keep it.",
          "Open or delete saved recipes anytime from Your cookbook below.",
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
              "Generate creates a draft. Save (signed in) puts it on your cookbook shelf. Delete removes it.",
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
            Tip: <Link href="/kitchen">Sign in</Link> so you can save drafts to
            your cookbook.
          </p>
        )}

        {error && <p className="error">{error}</p>}

        {recipe && (
          <div className="recipe-result">
            <RecipeView
              recipe={recipe}
              savedNote={savedNote}
              actions={
                <>
                  {canSave && user && (
                    <button
                      type="button"
                      className="btn"
                      disabled={saveBusy}
                      onClick={() => void onSave()}
                    >
                      {saveBusy ? "Saving…" : "Save to cookbook"}
                    </button>
                  )}
                  {canSave && !user && (
                    <Link href="/kitchen" className="btn">
                      Sign in to save
                    </Link>
                  )}
                  {recipe.saved && recipe.recipe_id != null && (
                    <button
                      type="button"
                      className="btn btn-ghost"
                      onClick={() => void onDelete(recipe.recipe_id!)}
                    >
                      Delete from cookbook
                    </button>
                  )}
                </>
              }
            />
          </div>
        )}

        {!recipe && (
          <div className="prompt-mosaic" aria-label="Example prompts">
            {EXAMPLES.map((ex) => (
              <button
                key={ex.prompt}
                type="button"
                className="mosaic-tile"
                disabled={busy}
                onClick={() => setRequest(ex.prompt)}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={ex.image} alt="" />
                <span>{ex.prompt}</span>
              </button>
            ))}
          </div>
        )}
      </section>

      <section className="lab-section cookbook" aria-labelledby="cookbook-h">
        <h2 id="cookbook-h">Your cookbook</h2>
        {!user && (
          <p className="muted">
            <Link href="/kitchen">Sign in</Link> to keep and browse saved
            recipes here.
          </p>
        )}
        {user && libraryError && <p className="error">{libraryError}</p>}
        {user && library.length === 0 && !libraryError && (
          <p className="muted">
            No saved recipes yet — generate one above, then click Save.
          </p>
        )}
        {user && library.length > 0 && (
          <ul className="recipe-grid">
            {library.map((r) => (
              <li key={r.id} className="recipe-card-wrap">
                <button
                  type="button"
                  className="recipe-card"
                  onClick={() => openSaved(r.id)}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={recipeCoverUrl({
                      id: r.id,
                      image_url: r.image_url,
                      title: r.title,
                    })}
                    alt=""
                  />
                  <span className="recipe-card-body">
                    <strong>{r.title}</strong>
                    <span className="muted">
                      {r.servings != null
                        ? `Serves ${r.servings}`
                        : "Saved recipe"}
                    </span>
                  </span>
                </button>
                <button
                  type="button"
                  className="text-btn recipe-card-delete"
                  onClick={() => void onDelete(r.id)}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
