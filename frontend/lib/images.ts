/** Local stock food photos (Wikimedia Commons — see public/images/CREDITS.md). */

export const FOOD_IMAGES = [
  "/images/hero.jpg",
  "/images/pasta.jpg",
  "/images/bread.jpg",
  "/images/veggies.jpg",
] as const;

/** Stable pick so the same recipe id always gets the same thumbnail. */
export function imageForId(id: number | string): string {
  const n = typeof id === "number" ? id : hash(id);
  return FOOD_IMAGES[Math.abs(n) % FOOD_IMAGES.length];
}

/** Prefer Unsplash (or other) URL from the API; else local stock. */
export function recipeCoverUrl(opts: {
  id?: number | string | null;
  image_url?: string | null;
  title?: string | null;
}): string {
  if (opts.image_url) return opts.image_url;
  if (opts.id != null) return imageForId(opts.id);
  if (opts.title) return imageForId(opts.title);
  return FOOD_IMAGES[0];
}

function hash(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return h;
}
