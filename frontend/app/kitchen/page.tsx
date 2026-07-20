"use client";

import { FormEvent, useEffect, useState } from "react";
import { FeatureGuide } from "@/components/FeatureGuide";
import {
  addEquipment,
  deleteEquipment,
  getKitchen,
  register,
  upsertProfile,
  type Equipment,
  type KitchenProfile,
  type ProfileUpsert,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useConfirm } from "@/lib/confirm";

const EQUIPMENT_KINDS = [
  "skillet",
  "dutch_oven",
  "sheet_pan",
  "thermometer",
  "scale",
  "mixer",
  "other",
] as const;

/** Keys must match backend `ALLERGEN_KEYWORDS` in safety/allergens.py. */
const ALLERGENS: { id: string; label: string }[] = [
  { id: "milk", label: "Milk" },
  { id: "eggs", label: "Eggs" },
  { id: "fish", label: "Fish" },
  { id: "crustacean_shellfish", label: "Shellfish" },
  { id: "tree_nuts", label: "Tree nuts" },
  { id: "peanuts", label: "Peanuts" },
  { id: "wheat", label: "Wheat" },
  { id: "soybeans", label: "Soy" },
  { id: "sesame", label: "Sesame" },
];

/** General home-cuisine tags — not Vietnam-only. */
const HOME_CUISINES: { id: string; label: string }[] = [
  { id: "vietnamese", label: "Vietnamese" },
  { id: "korean", label: "Korean" },
  { id: "japanese", label: "Japanese" },
  { id: "chinese", label: "Chinese" },
  { id: "thai", label: "Thai" },
  { id: "indian", label: "Indian" },
  { id: "italian", label: "Italian" },
  { id: "mexican", label: "Mexican" },
  { id: "french", label: "French" },
  { id: "middle_eastern", label: "Middle Eastern" },
  { id: "american", label: "American" },
];

type AuthenticityMode = "home" | "adapted" | "flexible";

type FormState = {
  oven_offset_f: number;
  cooktop_type: string;
  elevation_m: string;
  measurement_system: "us" | "metric";
  allergens: string[];
  home_cuisines: string[];
  authenticity_mode: AuthenticityMode;
  /** Keep other preference keys we don't edit in this form. */
  otherPreferences: Record<string, unknown>;
};

const emptyForm: FormState = {
  oven_offset_f: 0,
  cooktop_type: "",
  elevation_m: "",
  measurement_system: "us",
  allergens: [],
  home_cuisines: [],
  authenticity_mode: "flexible",
  otherPreferences: {},
};

function profileToForm(p: KitchenProfile | null): FormState {
  if (!p) return emptyForm;
  const allergens = Array.isArray(p.dietary_restrictions?.allergens)
    ? p.dietary_restrictions.allergens.map(String)
    : [];
  const prefs = p.preferences ?? {};
  const home_cuisines = Array.isArray(prefs.home_cuisines)
    ? prefs.home_cuisines.map(String)
    : [];
  const mode = String(prefs.authenticity_mode || "flexible");
  const authenticity_mode: AuthenticityMode =
    mode === "home" || mode === "adapted" || mode === "flexible"
      ? mode
      : "flexible";
  const { home_cuisines: _hc, authenticity_mode: _am, ...otherPreferences } =
    prefs;
  return {
    oven_offset_f: p.oven_offset_f,
    cooktop_type: p.cooktop_type ?? "",
    elevation_m: p.elevation_m != null ? String(p.elevation_m) : "",
    measurement_system:
      p.measurement_system === "metric" ? "metric" : "us",
    allergens,
    home_cuisines,
    authenticity_mode,
    otherPreferences,
  };
}

export default function KitchenPage() {
  const { user, loading: authLoading, login, refresh } = useAuth();
  const confirm = useConfirm();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);
  const [authBusy, setAuthBusy] = useState(false);

  const [form, setForm] = useState<FormState>(emptyForm);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileMsg, setProfileMsg] = useState<string | null>(null);
  const [profileBusy, setProfileBusy] = useState(false);
  const [loadingKitchen, setLoadingKitchen] = useState(false);
  const [equipment, setEquipment] = useState<Equipment[]>([]);
  const [eqKind, setEqKind] = useState<string>("skillet");
  const [eqName, setEqName] = useState("");
  const [eqError, setEqError] = useState<string | null>(null);
  const [eqMsg, setEqMsg] = useState<string | null>(null);
  const [eqBusy, setEqBusy] = useState(false);

  useEffect(() => {
    if (!user) {
      setForm(emptyForm);
      setEquipment([]);
      return;
    }
    let cancelled = false;
    setLoadingKitchen(true);
    getKitchen()
      .then((snap) => {
        if (cancelled) return;
        setForm(profileToForm(snap.profile));
        setEquipment(snap.equipment);
      })
      .catch((err) => {
        if (!cancelled) {
          setProfileError(
            err instanceof Error ? err.message : "Could not load kitchen",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingKitchen(false);
      });
    return () => {
      cancelled = true;
    };
  }, [user]);

  async function onAuth(e: FormEvent) {
    e.preventDefault();
    setAuthError(null);
    setAuthBusy(true);
    try {
      if (mode === "register") {
        await register({
          email,
          password,
          display_name: displayName.trim() || undefined,
        });
      }
      await login(email, password);
      await refresh();
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : "Auth failed");
    } finally {
      setAuthBusy(false);
    }
  }

  async function onSaveProfile(e: FormEvent) {
    e.preventDefault();
    setProfileError(null);
    setProfileMsg(null);
    setProfileBusy(true);
    try {
      const body: ProfileUpsert = {
        oven_offset_f: Number(form.oven_offset_f) || 0,
        cooktop_type: form.cooktop_type.trim() || null,
        elevation_m:
          form.elevation_m.trim() === ""
            ? null
            : Number(form.elevation_m),
        measurement_system: form.measurement_system,
        dietary_restrictions: { allergens: form.allergens },
        preferences: {
          ...form.otherPreferences,
          home_cuisines: form.home_cuisines,
          authenticity_mode: form.authenticity_mode,
        },
      };
      await upsertProfile(body);
      setProfileMsg(
        "Kitchen profile saved. Recipes and Ask will use your home-cuisine preference when you’re signed in.",
      );
    } catch (err) {
      setProfileError(
        err instanceof Error ? err.message : "Could not save profile",
      );
    } finally {
      setProfileBusy(false);
    }
  }

  function toggleAllergen(name: string) {
    setForm((f) => ({
      ...f,
      allergens: f.allergens.includes(name)
        ? f.allergens.filter((a) => a !== name)
        : [...f.allergens, name],
    }));
  }

  function toggleCuisine(id: string) {
    setForm((f) => ({
      ...f,
      home_cuisines: f.home_cuisines.includes(id)
        ? f.home_cuisines.filter((c) => c !== id)
        : [...f.home_cuisines, id],
    }));
  }

  async function reloadEquipment() {
    const snap = await getKitchen();
    setEquipment(snap.equipment);
  }

  async function onAddEquipment(e: FormEvent) {
    e.preventDefault();
    e.stopPropagation();
    const name = eqName.trim();
    if (!name) {
      setEqError("Enter a name for this piece of equipment.");
      return;
    }
    if (eqBusy) return;
    setEqBusy(true);
    setEqError(null);
    setEqMsg(null);
    try {
      await addEquipment({ kind: eqKind, name });
      setEqName("");
      await reloadEquipment();
      setEqMsg(`Added “${name}”. You can add another below.`);
    } catch (err) {
      setEqError(
        err instanceof Error ? err.message : "Could not add equipment",
      );
    } finally {
      setEqBusy(false);
    }
  }

  async function onDeleteEquipment(id: number) {
    if (eqBusy) return;
    const ok = await confirm({
      title: "Remove equipment?",
      message: "This gear will be removed from your kitchen profile.",
      confirmLabel: "Remove",
      danger: true,
    });
    if (!ok) return;
    setEqError(null);
    setEqMsg(null);
    setEqBusy(true);
    try {
      await deleteEquipment(id);
      await reloadEquipment();
      setEqMsg("Removed.");
    } catch (err) {
      setEqError(
        err instanceof Error ? err.message : "Could not remove equipment",
      );
    } finally {
      setEqBusy(false);
    }
  }

  return (
    <main className="shell kitchen-page">
      <header className="page-header">
        <h1>My kitchen</h1>
        <p className="lede">
          Tell KitchenLab about your real setup. Signed-in answers can adjust to
          your oven, diet, and gear — not a generic kitchen.
        </p>
        <FeatureGuide
          title="Why set up a kitchen profile?"
          summary="Anonymous Ask still works. Signing in is optional — but it’s how personalization happens (cold ovens, allergies, cast iron, etc.)."
          when="Set this up once if you cook here often. Skip it if you’re just exploring."
          steps={[
            "Create an account or sign in.",
            "Save oven offset, elevation (optional), and allergens.",
            "List equipment you actually own.",
            "Go back to Ask — look for the “personalized” badge on answers.",
          ]}
          terms={[
            {
              term: "Oven offset (°F)",
              meaning:
                "How wrong your oven dial is. Measure with an oven thermometer. If dial 350 is really 335, enter +15. Leave 0 if you don’t know.",
            },
            {
              term: "Elevation (meters)",
              meaning:
                "How high above sea level you live. Higher = water boils cooler. Optional; leave blank at sea level or if unsure.",
            },
            {
              term: "Equipment",
              meaning:
                "Pans and tools you own. Helps recipes prefer methods that match your gear (e.g. cast-iron sear).",
            },
            {
              term: "Home cuisines + authenticity",
              meaning:
                "Which food cultures are “home” for you (Vietnamese, Korean, Italian…). Home/traditional steers recipes toward homeland flavor; Adapted allows diaspora/weeknight shortcuts — for every cuisine, not just one.",
            },
          ]}
        />
      </header>

      {authLoading && <p className="muted">Checking sign-in…</p>}

      {!authLoading && !user && (
        <section className="auth-panel panel">
          <div className="mode-tabs">
            <button
              type="button"
              className={mode === "login" ? "active" : undefined}
              onClick={() => setMode("login")}
            >
              Sign in
            </button>
            <button
              type="button"
              className={mode === "register" ? "active" : undefined}
              onClick={() => setMode("register")}
            >
              Create account
            </button>
          </div>
          <form className="stack-form" onSubmit={onAuth}>
            {mode === "register" && (
              <label>
                Display name
                <input
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  autoComplete="nickname"
                />
              </label>
            )}
            <label>
              Email
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
              />
            </label>
            <label>
              Password
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete={
                  mode === "login" ? "current-password" : "new-password"
                }
              />
            </label>
            {authError && <p className="error">{authError}</p>}
            <button type="submit" disabled={authBusy}>
              {authBusy
                ? "Working…"
                : mode === "login"
                  ? "Sign in"
                  : "Create account"}
            </button>
          </form>
        </section>
      )}

      {!authLoading && user && (
        <section className="profile-panel">
          <p className="signed-in">
            Signed in as <strong>{user.display_name || user.email}</strong>
          </p>
          {loadingKitchen ? (
            <p className="muted">Loading profile…</p>
          ) : (
            <form className="stack-form panel" onSubmit={onSaveProfile}>
              <label>
                Oven offset (°F)
                <span className="field-hint">
                  If your oven runs cold, enter a positive number (e.g. 15 means
                  dial 350 → treat as 335, so recipes bump the dial up).
                </span>
                <input
                  type="number"
                  min={-50}
                  max={50}
                  value={form.oven_offset_f}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      oven_offset_f: Number(e.target.value),
                    }))
                  }
                />
              </label>
              <label>
                Elevation (meters)
                <span className="field-hint">
                  Higher altitude → water boils cooler; useful for boiling /
                  baking notes.
                </span>
                <input
                  type="number"
                  min={0}
                  max={6000}
                  placeholder="e.g. 1600"
                  value={form.elevation_m}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, elevation_m: e.target.value }))
                  }
                />
              </label>
              <label>
                Cooktop
                <input
                  placeholder="gas, induction, electric…"
                  value={form.cooktop_type}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, cooktop_type: e.target.value }))
                  }
                />
              </label>
              <label>
                Measurements
                <select
                  value={form.measurement_system}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      measurement_system: e.target.value as "us" | "metric",
                    }))
                  }
                >
                  <option value="us">US customary</option>
                  <option value="metric">Metric</option>
                </select>
              </label>
              <fieldset className="allergen-set">
                <legend>Allergens to avoid</legend>
                <div className="allergen-grid">
                  {ALLERGENS.map((a) => (
                    <label key={a.id} className="check">
                      <input
                        type="checkbox"
                        checked={form.allergens.includes(a.id)}
                        onChange={() => toggleAllergen(a.id)}
                      />
                      {a.label}
                    </label>
                  ))}
                </div>
              </fieldset>

              <fieldset className="allergen-set">
                <legend>Home cuisines</legend>
                <p className="field-hint">
                  Cuisines where you care about taste-of-home — Vietnamese,
                  Korean, Italian, Indian, and so on. Pick as many as you want.
                </p>
                <div className="allergen-grid">
                  {HOME_CUISINES.map((c) => (
                    <label key={c.id} className="check">
                      <input
                        type="checkbox"
                        checked={form.home_cuisines.includes(c.id)}
                        onChange={() => toggleCuisine(c.id)}
                      />
                      {c.label}
                    </label>
                  ))}
                </div>
              </fieldset>

              <fieldset className="allergen-set">
                <legend>When cooking those cuisines</legend>
                <p className="field-hint">
                  Same idea for every cuisine: home flavor vs adapted for where
                  you live now.
                </p>
                <div className="authenticity-options">
                  {(
                    [
                      {
                        id: "home" as const,
                        label: "Home / traditional",
                        hint: "Prefer homeland home-kitchen practice, not restaurant-abroad shortcuts.",
                      },
                      {
                        id: "adapted" as const,
                        label: "Adapted for where I live",
                        hint: "Keep the spirit, allow practical pantry substitutions — and say when you shortcut.",
                      },
                      {
                        id: "flexible" as const,
                        label: "No strong preference",
                        hint: "Don’t steer authenticity either way.",
                      },
                    ] as const
                  ).map((opt) => (
                    <label key={opt.id} className="authenticity-option">
                      <input
                        type="radio"
                        name="authenticity_mode"
                        checked={form.authenticity_mode === opt.id}
                        onChange={() =>
                          setForm((f) => ({
                            ...f,
                            authenticity_mode: opt.id,
                          }))
                        }
                      />
                      <span>
                        <strong>{opt.label}</strong>
                        <span className="field-hint">{opt.hint}</span>
                      </span>
                    </label>
                  ))}
                </div>
              </fieldset>

              {profileError && <p className="error">{profileError}</p>}
              {profileMsg && <p className="ok">{profileMsg}</p>}
              <button type="submit" disabled={profileBusy}>
                {profileBusy ? "Saving…" : "Save kitchen profile"}
              </button>
            </form>
          )}

          {!loadingKitchen && (
            <section className="equipment-panel" aria-labelledby="equip-heading">
              <h2 id="equip-heading">Equipment</h2>
              <p className="field-hint">
                What’s in your drawer — cast-iron skillet, probe thermometer,
                scale. The agent can prefer methods that use what you own.
              </p>
              <ul className="equip-list">
                {equipment.map((item) => (
                  <li key={item.id} className="equip-item">
                    <div>
                      <strong>{item.name}</strong>
                      <span className="muted">
                        {" "}
                        · {item.kind.replace(/_/g, " ")}
                      </span>
                    </div>
                    <button
                      type="button"
                      className="text-btn"
                      disabled={eqBusy}
                      onClick={() => onDeleteEquipment(item.id)}
                    >
                      Remove
                    </button>
                  </li>
                ))}
              </ul>
              {equipment.length === 0 && (
                <p className="muted">No equipment listed yet.</p>
              )}
              <form className="stack-form" onSubmit={onAddEquipment}>
                <label>
                  Kind
                  <select
                    value={eqKind}
                    disabled={eqBusy}
                    onChange={(e) => setEqKind(e.target.value)}
                  >
                    {EQUIPMENT_KINDS.map((k) => (
                      <option key={k} value={k}>
                        {k.replace(/_/g, " ")}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Name
                  <input
                    value={eqName}
                    disabled={eqBusy}
                    onChange={(e) => {
                      setEqName(e.target.value);
                      setEqError(null);
                    }}
                    placeholder="e.g. 12-inch cast iron"
                  />
                </label>
                {eqError && <p className="error">{eqError}</p>}
                {eqMsg && <p className="ok">{eqMsg}</p>}
                <button type="submit" disabled={eqBusy}>
                  {eqBusy ? "Working…" : "Add equipment"}
                </button>
              </form>
            </section>
          )}
        </section>
      )}
    </main>
  );
}
