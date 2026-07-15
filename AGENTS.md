# Agent instructions for KitchenLab

## Teaching contract (important)

The project owner is using this project to learn. They are a beginner with
AWS, Docker, databases/SQL, and FastAPI. For every meaningful step:

- Explain **before doing**: a short plain-language "what is this and why do we
  need it here", using everyday analogies (kitchen analogies fit the theme).
- Narrate the code after writing it: walk through the important lines.
- Define jargon on first use (ORM, migration, container, endpoint, etc.).
- Pause at natural checkpoints so the owner can run things themselves.
- Prefer clarity over cleverness; note where production practice would differ.

## Architecture principles

- Single FastAPI backend (Python), Next.js frontend (TypeScript),
  Postgres 16 + pgvector, Docker Compose locally, AWS for production.
- **The LLM never calculates or invents critical values or safety facts.**
  Deterministic code (calculators, safety tables) and the curated, cited
  knowledge base produce the substance; the LLM only phrases, personalizes,
  and layers explanations (Action / Reason / Science).
- Every science claim carries claim-level citations (source, passage, dates,
  scope, confidence).

See `.cursor/plans/` or the project plan for the full roadmap.
