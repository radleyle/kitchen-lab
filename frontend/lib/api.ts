/**
 * Tiny client for the FastAPI backend.
 * NEXT_PUBLIC_API_URL is baked in at build time (Compose sets it for local).
 *
 * Auth: we store a JWT (JSON Web Token — a signed “wristband” that proves
 * who you are) in localStorage and send it as Authorization: Bearer …
 * on protected routes. The agent endpoint is optional-auth: with a token
 * it personalizes; without one it still answers anonymously.
 */

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const TOKEN_KEY = "kitchenlab_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function apiFetch(
  path: string,
  init: RequestInit = {},
  auth = false,
): Promise<Response> {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  if (auth) {
    const token = getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }
  return fetch(`${API_URL}${path}`, { ...init, headers });
}

async function readError(res: Response): Promise<string> {
  const text = await res.text();
  try {
    const json = JSON.parse(text) as { detail?: unknown };
    if (typeof json.detail === "string") return json.detail;
    if (Array.isArray(json.detail)) {
      return json.detail
        .map((d) =>
          typeof d === "object" && d && "msg" in d
            ? String((d as { msg: string }).msg)
            : JSON.stringify(d),
        )
        .join("; ");
    }
  } catch {
    /* plain text */
  }
  return text || `Request failed (${res.status})`;
}

export type User = {
  id: number;
  email: string;
  display_name: string | null;
};

export type AgentResponse = {
  mode: string;
  classification_confidence?: string;
  personalized?: boolean;
  entities?: Record<string, string | null>;
  result: Record<string, unknown>;
  /** Present when signed-in ask was persisted to history. */
  conversation_id?: number;
};

export type ConversationSummary = {
  id: number;
  title: string | null;
  mode: string;
  created_at: string;
  updated_at: string;
};

export type ConversationTurn = {
  id: string;
  question: string;
  response?: AgentResponse | null;
  diagnose_slug?: string | null;
  error?: string | null;
  ts?: string;
};

export type ConversationDetail = ConversationSummary & {
  messages: ConversationTurn[];
};

export type KitchenProfile = {
  id: number;
  oven_offset_f: number;
  cooktop_type: string | null;
  elevation_m: number | null;
  measurement_system: string;
  dietary_restrictions: { allergens?: string[] } & Record<string, unknown>;
  preferences: Record<string, unknown>;
};

export type Equipment = {
  id: number;
  kind: string;
  name: string;
  details: Record<string, unknown>;
};

export type KitchenSnapshot = {
  profile: KitchenProfile | null;
  equipment: Equipment[];
};

export type ProfileUpsert = {
  oven_offset_f: number;
  cooktop_type: string | null;
  elevation_m: number | null;
  measurement_system: "us" | "metric";
  dietary_restrictions: { allergens: string[] };
  preferences: Record<string, unknown>;
};

export async function register(body: {
  email: string;
  password: string;
  display_name?: string;
}): Promise<User> {
  const res = await apiFetch("/auth/register", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function login(body: {
  email: string;
  password: string;
}): Promise<string> {
  const res = await apiFetch("/auth/login", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  const data = (await res.json()) as { access_token: string };
  setToken(data.access_token);
  return data.access_token;
}

export async function fetchMe(): Promise<User | null> {
  if (!getToken()) return null;
  const res = await apiFetch("/auth/me", {}, true);
  if (res.status === 401) {
    setToken(null);
    return null;
  }
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function getKitchen(): Promise<KitchenSnapshot> {
  const res = await apiFetch("/kitchen", {}, true);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function upsertProfile(
  body: ProfileUpsert,
): Promise<KitchenProfile> {
  const res = await apiFetch(
    "/kitchen/profile",
    { method: "PUT", body: JSON.stringify(body) },
    true,
  );
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function addEquipment(body: {
  kind: string;
  name: string;
  details?: Record<string, unknown>;
}): Promise<Equipment> {
  const res = await apiFetch(
    "/kitchen/equipment",
    { method: "POST", body: JSON.stringify(body) },
    true,
  );
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function deleteEquipment(id: number): Promise<void> {
  const res = await apiFetch(
    `/kitchen/equipment/${id}`,
    { method: "DELETE" },
    true,
  );
  if (!res.ok) throw new Error(await readError(res));
}

export async function askAgent(
  message: string,
  conversationId?: number | null,
): Promise<AgentResponse> {
  // Send the token when present so cook/adapt/substitute can personalize
  // and Ask history can persist the turn.
  const body: { message: string; conversation_id?: number } = { message };
  if (conversationId != null) body.conversation_id = conversationId;
  const res = await apiFetch(
    "/agent/ask",
    { method: "POST", body: JSON.stringify(body) },
    true,
  );
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function listConversations(): Promise<ConversationSummary[]> {
  const res = await apiFetch("/agent/conversations", {}, true);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function getConversation(
  id: number,
): Promise<ConversationDetail> {
  const res = await apiFetch(`/agent/conversations/${id}`, {}, true);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function syncConversationMessages(
  id: number,
  messages: ConversationTurn[],
): Promise<ConversationDetail> {
  const res = await apiFetch(
    `/agent/conversations/${id}`,
    { method: "PUT", body: JSON.stringify({ messages }) },
    true,
  );
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function deleteConversation(id: number): Promise<void> {
  const res = await apiFetch(
    `/agent/conversations/${id}`,
    { method: "DELETE" },
    true,
  );
  if (!res.ok) throw new Error(await readError(res));
}

export async function startDiagnosis(body: {
  description: string;
}): Promise<Record<string, unknown>> {
  const res = await apiFetch(
    "/diagnose/start",
    { method: "POST", body: JSON.stringify(body) },
    false,
  );
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function concludeDiagnosis(body: {
  symptom_slug: string;
  description: string;
  answers: { question: string; answer: string }[];
}): Promise<Record<string, unknown>> {
  const res = await apiFetch(
    "/diagnose/conclude",
    { method: "POST", body: JSON.stringify(body) },
    false,
  );
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export type Citation = {
  claim?: string;
  confidence?: string;
  scope?: string;
  source?: {
    title?: string;
    author?: string;
    url?: string;
    authority_level?: string;
  };
};

export type SafetyFact = {
  food: string;
  min_internal_temp_c: number | null;
  min_internal_temp_f: number | null;
  rest_time_min: number | null;
  source?: {
    title?: string;
    url?: string;
    authority_level?: string;
    reviewed_at?: string;
  };
};

export type TechniqueSummary = {
  id: number;
  slug: string;
  name: string;
  summary: string;
  applicable_foods: string[];
};

export type TechniqueDetail = TechniqueSummary & {
  procedure: unknown[];
  common_mistakes: unknown[];
  mechanism: {
    slug: string;
    name: string;
    explanation: string;
  } | null;
};

export type MechanismSummary = {
  slug: string;
  name: string;
  explanation: string;
};

export type MechanismDetail = MechanismSummary & {
  techniques: TechniqueSummary[];
};

export type NotebookEntry = {
  id: number;
  title: string;
  body: string | null;
  recipe_id: number | null;
  experiment_id: number | null;
  created_at: string;
};

export async function listTechniques(): Promise<TechniqueSummary[]> {
  const res = await apiFetch("/techniques");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function getTechnique(slug: string): Promise<TechniqueDetail> {
  const res = await apiFetch(`/techniques/${encodeURIComponent(slug)}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function listMechanisms(): Promise<MechanismSummary[]> {
  const res = await apiFetch("/mechanisms");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function getMechanism(slug: string): Promise<MechanismDetail> {
  const res = await apiFetch(`/mechanisms/${encodeURIComponent(slug)}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function listNotebook(): Promise<NotebookEntry[]> {
  const res = await apiFetch("/notebook", {}, true);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function createNotebookEntry(body: {
  title: string;
  body?: string;
}): Promise<NotebookEntry> {
  const res = await apiFetch(
    "/notebook",
    { method: "POST", body: JSON.stringify(body) },
    true,
  );
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function deleteNotebookEntry(id: number): Promise<void> {
  const res = await apiFetch(`/notebook/${id}`, { method: "DELETE" }, true);
  if (!res.ok) throw new Error(await readError(res));
}

export type Observation = {
  id: number;
  metric: string;
  value: number | null;
  text_value: string | null;
  unit: string | null;
  recorded_at: string;
};

export type Attachment = {
  id: number;
  s3_key: string;
  kind: string;
  trial_id: number | null;
  notebook_entry_id: number | null;
  created_at: string;
};

export type Trial = {
  id: number;
  label: string;
  variable_value: string;
  notes: string | null;
  observations: Observation[];
  attachments?: Attachment[];
};

export type Experiment = {
  id: number;
  question: string;
  hypothesis: string | null;
  independent_variable: string;
  constants: string[];
  status: "planned" | "running" | "done" | string;
  conclusion: string | null;
  created_at: string;
  trials: Trial[];
};

export async function listExperiments(): Promise<Experiment[]> {
  const res = await apiFetch("/experiments", {}, true);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function designExperiment(
  message: string,
  persist = true,
): Promise<Record<string, unknown>> {
  const res = await apiFetch(
    "/experiments/design",
    {
      method: "POST",
      body: JSON.stringify({ message, persist }),
    },
    true,
  );
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function updateExperiment(
  id: number,
  body: {
    hypothesis?: string;
    status?: "planned" | "running" | "done";
    conclusion?: string;
  },
): Promise<Experiment> {
  const res = await apiFetch(
    `/experiments/${id}`,
    { method: "PATCH", body: JSON.stringify(body) },
    true,
  );
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function addObservation(
  experimentId: number,
  trialId: number,
  body: {
    metric: string;
    value?: number | null;
    text_value?: string | null;
    unit?: string | null;
  },
): Promise<Observation> {
  const res = await apiFetch(
    `/experiments/${experimentId}/trials/${trialId}/observations`,
    { method: "POST", body: JSON.stringify(body) },
    true,
  );
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function uploadTrialPhoto(
  experimentId: number,
  trialId: number,
  file: File,
): Promise<Attachment> {
  // multipart/form-data — do not set Content-Type; the browser adds the boundary.
  const form = new FormData();
  form.append("file", file);
  const headers = new Headers();
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(
    `${API_URL}/experiments/${experimentId}/trials/${trialId}/photos`,
    { method: "POST", headers, body: form },
  );
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

/** Fetch a protected image as a blob URL (img tags can't send Bearer headers). */
export async function fetchAttachmentObjectUrl(
  attachmentId: number,
): Promise<string> {
  const headers = new Headers();
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${API_URL}/attachments/${attachmentId}/content`, {
    headers,
  });
  if (!res.ok) throw new Error(await readError(res));
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export async function deleteAttachment(attachmentId: number): Promise<void> {
  const res = await apiFetch(
    `/attachments/${attachmentId}`,
    { method: "DELETE" },
    true,
  );
  if (!res.ok) throw new Error(await readError(res));
}

/** Calculators are public — no auth. Python owns the numbers. */

export async function calcBrine(body: {
  water_g: number;
  brine_percent: number;
  salt_type: string;
}): Promise<{ salt_g: number; salt_tbsp: number; salt_type: string }> {
  const res = await apiFetch("/calculators/brine", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function calcEquilibriumSalt(body: {
  total_mass_g: number;
  target_percent: number;
  salt_type: string;
}): Promise<{
  salt_g: number;
  salt_tbsp: number;
  salt_type: string;
  target_percent: number;
}> {
  const res = await apiFetch("/calculators/equilibrium-salt", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function calcScale(body: {
  ingredients: { name: string; amount: number; unit: string }[];
  original_servings: number;
  target_servings: number;
}): Promise<
  { name: string; amount: number; unit: string; note: string | null }[]
> {
  const res = await apiFetch("/calculators/scale", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function calcBakersPercentages(body: {
  ingredients_g: Record<string, number>;
}): Promise<{
  percentages: Record<string, number>;
  hydration_percent: number;
}> {
  const res = await apiFetch("/calculators/bakers-percentages", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function calcVolumeToGrams(body: {
  amount: number;
  unit: string;
  ingredient: string;
}): Promise<{ grams: number }> {
  const res = await apiFetch("/calculators/volume-to-grams", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export type RecipeStep = {
  position?: number;
  instruction: string;
  why?: string | null;
  science?: string | null;
  visual_cues?: string | null;
  critical_temp_c?: number | null;
  target_internal_temp_c?: number | null;
  citations?: Citation[] | unknown;
};

export type GeneratedRecipe = {
  feasible: boolean;
  recipe_id?: number | null;
  saved?: boolean;
  title?: string;
  description?: string;
  servings?: number | null;
  image_url?: string | null;
  image_credit?: string | null;
  image_credit_url?: string | null;
  ingredients?: {
    ingredient: string;
    grams?: number | null;
    amount?: string;
  }[];
  steps?: RecipeStep[];
  safety?: SafetyFact | null;
  safety_overrides?: unknown[];
  kitchen?: {
    notes?: string[];
    dietary_conflicts?: unknown[];
    oven_adjustments?: unknown[];
    boiling_point_c?: number | null;
    applied?: boolean;
  };
  grounding_note?: string;
  message?: string;
  personalized?: boolean;
};

export type RecipeSummary = {
  id: number;
  title: string;
  description: string | null;
  servings: number | null;
  image_url?: string | null;
  image_credit?: string | null;
  image_credit_url?: string | null;
};

export async function generateRecipe(body: {
  request: string;
  servings?: number | null;
}): Promise<GeneratedRecipe> {
  const res = await apiFetch(
    "/recipes/generate",
    { method: "POST", body: JSON.stringify(body) },
    true,
  );
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function saveRecipe(body: {
  title: string;
  description?: string | null;
  servings?: number | null;
  ingredients?: GeneratedRecipe["ingredients"];
  steps?: GeneratedRecipe["steps"];
  image_url?: string | null;
  image_credit?: string | null;
  image_credit_url?: string | null;
  source_url?: string | null;
}): Promise<{
  id: number;
  title: string;
  image_url?: string | null;
  image_credit?: string | null;
  image_credit_url?: string | null;
}> {
  const res = await apiFetch(
    "/recipes/save",
    { method: "POST", body: JSON.stringify(body) },
    true,
  );
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function deleteRecipe(id: number): Promise<void> {
  const res = await apiFetch(`/recipes/${id}`, { method: "DELETE" }, true);
  if (!res.ok) throw new Error(await readError(res));
}

export async function listMyRecipes(): Promise<RecipeSummary[]> {
  const res = await apiFetch("/recipes", {}, true);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function getRecipe(id: number): Promise<GeneratedRecipe> {
  const res = await apiFetch(`/recipes/${id}`);
  if (!res.ok) throw new Error(await readError(res));
  const data = await res.json();
  return { feasible: true, saved: true, ...data };
}
