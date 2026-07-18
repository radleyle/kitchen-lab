"""Deterministic personalization math and conflict checks.

These are pure functions: no database, no LLM. Oven offsets and boiling
points are physics/calibration, not opinions -- so they live here, not
in a prompt.
"""

import re

# Rough rule of thumb used by USDA/extension services: boiling point drops
# about 1C per 300 m of elevation (≈1F per 500 ft). Good enough for
# home-cooking guidance; not a lab-grade barometric formula.
METERS_PER_CELSIUS_DROP = 300.0
SEA_LEVEL_BOIL_C = 100.0

# Matches "350F", "350°F", "175 C", often after bake/roast/oven.
OVEN_TEMP_RE = re.compile(
    r"(?P<temp>\d{2,3})\s*°?\s*(?P<unit>[FfCc])\b"
)


def boiling_point_c(elevation_m: int | None) -> float | None:
    """Approximate water boiling point at the given elevation."""
    if elevation_m is None:
        return None
    if elevation_m < 0:
        elevation_m = 0
    return round(SEA_LEVEL_BOIL_C - elevation_m / METERS_PER_CELSIUS_DROP, 1)


def dial_for_desired_oven_f(desired_f: float, oven_offset_f: int) -> float:
    """What to set the dial to so the oven's actual temperature is desired_f.

    oven_offset_f is "how the oven misreads": -15 means it runs 15F cold,
    so actual = dial + offset. Solving for dial: dial = desired - offset.
    """
    return desired_f - oven_offset_f


def apply_oven_offset_to_text(text: str, oven_offset_f: int) -> tuple[str, list[dict]]:
    """Rewrite Fahrenheit oven temps in a step to dial temperatures.

    Only adjusts F (US ovens are dialed in F). Celsius figures are left
    alone -- converting them would invent precision we don't have.
    Returns (new_text, list of {original_f, dial_f} adjustments).
    """
    if not oven_offset_f or not text:
        return text, []

    adjustments: list[dict] = []

    def repl(match: re.Match) -> str:
        unit = match.group("unit").upper()
        if unit != "F":
            return match.group(0)
        original = float(match.group("temp"))
        dial = dial_for_desired_oven_f(original, oven_offset_f)
        if dial == original:
            return match.group(0)
        adjustments.append({"desired_f": original, "dial_f": dial})
        # Keep integers looking like integers.
        dial_str = f"{dial:.0f}" if dial == int(dial) else f"{dial:g}"
        return f"{dial_str}F (dial; oven runs {oven_offset_f:+d}F)"

    new_text = OVEN_TEMP_RE.sub(repl, text)
    return new_text, adjustments


def dietary_conflicts(
    ingredient_names: list[str], dietary_restrictions: dict | None
) -> list[dict]:
    """Flag ingredients that collide with the user's stated restrictions.

    dietary_restrictions shape (flexible JSONB):
      {"allergens": ["milk", "peanuts"], "diets": ["vegetarian"],
       "avoid": ["pork", "alcohol"]}
    """
    if not dietary_restrictions:
        return []

    from app.safety.allergens import detect_allergens

    conflicts: list[dict] = []
    allergens = [a.lower() for a in dietary_restrictions.get("allergens", [])]
    if allergens and ingredient_names:
        detected = detect_allergens(ingredient_names)
        for allergen, hits in detected.get("allergens_detected", {}).items():
            if allergen in allergens:
                conflicts.append(
                    {
                        "kind": "allergen",
                        "name": allergen,
                        "triggered_by": hits,
                    }
                )

    avoid = [a.lower() for a in dietary_restrictions.get("avoid", [])]
    for name in ingredient_names:
        lower = name.lower()
        for banned in avoid:
            if banned and banned in lower:
                conflicts.append(
                    {
                        "kind": "avoid",
                        "name": banned,
                        "triggered_by": [name],
                    }
                )

    diets = {d.lower() for d in dietary_restrictions.get("diets", [])}
    if "vegetarian" in diets or "vegan" in diets:
        meat_keywords = (
            "chicken", "beef", "pork", "lamb", "turkey", "bacon", "ham",
            "sausage", "fish", "salmon", "shrimp", "anchovy",
        )
        if "vegan" in diets:
            meat_keywords = meat_keywords + (
                "egg", "butter", "milk", "cream", "cheese", "honey", "yogurt",
            )
        for name in ingredient_names:
            lower = name.lower()
            for kw in meat_keywords:
                if kw in lower:
                    conflicts.append(
                        {
                            "kind": "diet",
                            "name": "vegan" if "vegan" in diets else "vegetarian",
                            "triggered_by": [name],
                        }
                    )
                    break

    # Deduplicate by (kind, name, triggered_by)
    seen: set[tuple] = set()
    unique = []
    for c in conflicts:
        key = (c["kind"], c["name"], tuple(c["triggered_by"]))
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


def personalize_recipe(recipe: dict, snapshot: dict | None) -> dict:
    """Apply deterministic kitchen adjustments to a finished recipe dict.

    Mutates steps in place for oven dial rewrites; adds a "kitchen" block
    describing what was applied. Safe no-op when snapshot is None/empty.
    """
    if not snapshot:
        return recipe

    profile = snapshot.get("profile") or {}
    offset = int(profile.get("oven_offset_f") or 0)
    elevation = profile.get("elevation_m")
    boil = boiling_point_c(elevation)

    oven_adjustments: list[dict] = []
    for i, step in enumerate(recipe.get("steps", []), start=1):
        instruction = step.get("instruction") or ""
        new_text, adj = apply_oven_offset_to_text(instruction, offset)
        if adj:
            step["instruction"] = new_text
            for a in adj:
                oven_adjustments.append({"step": i, **a})

    names = [
        i.get("ingredient", "")
        for i in recipe.get("ingredients", [])
        if isinstance(i, dict)
    ]
    conflicts = dietary_conflicts(names, profile.get("dietary_restrictions"))

    notes: list[str] = []
    if offset:
        notes.append(
            f"Oven dial temps adjusted for a {offset:+d}F calibration offset "
            "(positive = oven runs hot; negative = runs cold)."
        )
    if boil is not None and elevation:
        notes.append(
            f"At ~{elevation} m elevation, water boils around {boil}C "
            f"({boil * 9 / 5 + 32:.0f}F). Long simmer/boil times may need "
            "a few extra minutes."
        )
    salt = (profile.get("preferences") or {}).get("salt_type")
    if salt:
        notes.append(
            f"Preferred salt type: {salt.replace('_', ' ')}. "
            "Volume measures of salt differ by brand; prefer grams."
        )
    equipment = snapshot.get("equipment") or []
    if equipment:
        names_eq = ", ".join(e["name"] for e in equipment)
        notes.append(f"Available equipment on file: {names_eq}.")

    recipe["kitchen"] = {
        "applied": bool(notes or oven_adjustments or conflicts),
        "oven_adjustments": oven_adjustments,
        "dietary_conflicts": conflicts,
        "boiling_point_c": boil,
        "notes": notes,
    }
    return recipe


def kitchen_prompt_block(snapshot: dict | None) -> str:
    """Short context block for LLM prompts. Empty string if no profile."""
    if not snapshot or not snapshot.get("profile"):
        return ""

    p = snapshot["profile"]
    lines = ["KITCHEN CONTEXT (facts about this cook's kitchen -- honor them):"]
    if p.get("oven_offset_f"):
        lines.append(
            f"- Oven calibration offset: {p['oven_offset_f']:+d}F "
            "(do NOT adjust dial temps yourself; code will)."
        )
    if p.get("cooktop_type"):
        lines.append(f"- Cooktop: {p['cooktop_type']}")
    if p.get("elevation_m") is not None:
        boil = boiling_point_c(p["elevation_m"])
        lines.append(
            f"- Elevation: {p['elevation_m']} m "
            f"(water boils ~{boil}C). Prefer covered simmer / slightly longer boils."
        )
    if p.get("measurement_system"):
        lines.append(f"- Preferred measures: {p['measurement_system']}")

    diet = p.get("dietary_restrictions") or {}
    if diet.get("allergens"):
        lines.append(f"- Allergens to avoid: {', '.join(diet['allergens'])}")
    if diet.get("diets"):
        lines.append(f"- Diets: {', '.join(diet['diets'])}")
    if diet.get("avoid"):
        lines.append(f"- Also avoid: {', '.join(diet['avoid'])}")

    prefs = p.get("preferences") or {}
    if prefs.get("salt_type"):
        lines.append(f"- Salt on hand: {prefs['salt_type']}")
    if prefs.get("preferred_doneness"):
        lines.append(f"- Preferred doneness: {prefs['preferred_doneness']}")

    equipment = snapshot.get("equipment") or []
    if equipment:
        lines.append("- Equipment available:")
        for e in equipment:
            detail = e.get("details") or {}
            extra = f" ({detail})" if detail else ""
            lines.append(f"  - {e['kind']}: {e['name']}{extra}")
        lines.append(
            "  Prefer techniques that use this equipment. If a method needs "
            "something missing, say so and offer an alternative."
        )
    return "\n".join(lines)


def filter_substitutions_for_diet(
    options: list[dict], dietary_restrictions: dict | None
) -> list[dict]:
    """Drop substitute options that conflict with dietary restrictions."""
    if not dietary_restrictions or not options:
        return options
    kept = []
    for opt in options:
        name = opt.get("substitute", "")
        conflicts = dietary_conflicts([name], dietary_restrictions)
        if conflicts:
            opt = {**opt, "excluded_by_diet": conflicts}
            # Still surface it, but marked -- honesty over silent deletion.
            kept.append(opt)
        else:
            kept.append(opt)
    # Prefer non-conflicting options first.
    kept.sort(key=lambda o: 1 if o.get("excluded_by_diet") else 0)
    return kept
