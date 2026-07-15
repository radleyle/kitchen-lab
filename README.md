# KitchenLab

Cook better through science. A "cooking through science" AI agent that teaches,
generates and adapts recipes, diagnoses cooking failures, and recommends
substitutions -- with every answer grounded in a cited food-science knowledge
base and deterministic calculators (the LLM explains; it never invents numbers
or safety facts).

## Architecture

| Piece    | Tech                    | Role                                       |
| -------- | ----------------------- | ------------------------------------------ |
| Frontend | Next.js + TypeScript    | The website users see (port 3001)          |
| Backend  | Python + FastAPI        | API, calculators, RAG, agent (port 8000)   |
| Database | Postgres 16 + pgvector  | Relational data + semantic search (5432)   |

## Run locally

Requires Docker Desktop.

```bash
docker compose up --build
```

Then open:

- http://localhost:3001 -- the app
- http://localhost:8000/docs -- interactive API playground (auto-generated)

Stop with `Ctrl+C`, or `docker compose down` to also remove containers.
Add `-v` (`docker compose down -v`) to wipe the database volume too.
