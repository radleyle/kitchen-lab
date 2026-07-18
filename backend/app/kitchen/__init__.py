"""Kitchen profile: the facts about a user's real kitchen.

Personalization is mostly deterministic Python (oven dial math, boiling
point at elevation, dietary conflict checks). The LLM only sees a short
KITCHEN CONTEXT block so it can prefer methods that fit the equipment --
it never invents oven offsets or allergy facts.
"""
