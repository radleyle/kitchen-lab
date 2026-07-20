# KitchenLab

Cook better through science. An AI cooking agent that **teaches**, **generates and adapts recipes**, **diagnoses failures**, **suggests substitutions**, and helps you run **small kitchen experiments** — with every answer grounded in a cited food-science knowledge base and deterministic calculators.

**Trust split (the product idea):** the LLM phrases and personalizes. It never invents temperatures, gram conversions, or safety facts. Those come from code, USDA tables, and curated passages with claim-level citations.

**Live demo:** [kitchen-lab-tau.vercel.app](https://kitchen-lab-tau.vercel.app/)

## Architecture

| Piece    | Tech                   | Role                                      |
| -------- | ---------------------- | ----------------------------------------- |
| Frontend | Next.js + TypeScript   | UI (port **3001**)                        |
| Backend  | Python + FastAPI       | API, agent, RAG, calculators (port 8000)  |
| Database | Postgres 16 + pgvector | Relational data + semantic search (5432)  |
| Photos   | Local disk or S3       | Experiment/notebook attachments           |

## Tech stack

### Local (what runs today)

| Layer | Choices | Why it’s here |
| ----- | ------- | ------------- |
| Containers | Docker + Docker Compose | Same pantry/kitchen/dining-room stack on every machine |
| Frontend | Next.js, TypeScript, React | Typed UI; port **3001** locally |
| Backend | Python 3.12, FastAPI, Uvicorn | HTTP API + auto `/docs` playground |
| Validation | Pydantic / pydantic-settings | Request shapes + env config |
| ORM & migrations | SQLAlchemy 2, Alembic | Models as Python; schema versioned like code |
| Database | PostgreSQL 16 + **pgvector** | Tables for users/recipes/etc.; vectors for RAG |
| Auth | JWT (PyJWT) + bcrypt | Stateless login; passwords stored as hashes only |
| LLM / embeddings | OpenAI API (`gpt-4o-mini`, `text-embedding-3-small`) | Phrasing + semantic search — **not** facts or math |
| Tests | pytest | Unit tests + deterministic eval scenarios |
| CI | GitHub Actions | Runs tests/evals on push and PRs |
| Photo storage | Local filesystem (`STORAGE_BACKEND=local`) | Same key shape as S3 |

### Production (live)

| Piece | Service | Role |
| ----- | ------- | ---- |
| Frontend | **Vercel** | Builds and serves the Next.js application |
| Backend | **Render** (Docker) | Runs FastAPI, migrations, calculators, and agent workflows |
| Database | **Neon** Postgres + pgvector | Stores application data and vectors for semantic retrieval |
| LLM / embeddings | **OpenAI API** | Phrases grounded answers and embeds curated passages |
| Recipe photos | **Unsplash API** | Supplies relevant cover photos with attribution |
| CI | **GitHub Actions** | Runs tests and deterministic evaluations |

The repository also includes an AWS/Terraform reference architecture under
`infra/`. It maps the same roles to ECS Fargate, RDS, S3, ECR, and an
Application Load Balancer without creating those resources automatically.

## Agent modes

| Mode         | What it does                                                                 |
| ------------ | ---------------------------------------------------------------------------- |
| **learn**    | Grounded Q&A + technique library when a named technique matches              |
| **cook**     | Science-annotated recipe generation; USDA safety floor enforced in Python    |
| **adapt**    | Paste a recipe → standardize measures (Python does the math) + annotate      |
| **diagnose** | Symptom taxonomy → follow-ups → evidence-ranked causes + cited fix           |
| **substitute** | Function-aware swaps (egg-as-moisture ≠ egg-as-binder)                     |
| **experiment** | Designs a controlled trial; you log observations, photos, and conclusions |

Optional **kitchen profile** (oven offset, elevation, equipment, allergies) personalizes cook/adapt/substitute when you send a Bearer token.

## Run locally

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
# 1. Secrets (gitignored)
cp .env.example .env
# Edit .env and set OPENAI_API_KEY=...
# Optional: UNSPLASH_ACCESS_KEY=... for related recipe cover photos
# (without it, cookbook cards use local stock images).

# 2. Start the stack
docker compose up --build
```

Then open:

- http://localhost:3001 — frontend (port **3001** on the host; container logs may say 3000)
- http://localhost:8000/docs — interactive API playground
- http://localhost:8000/health — backend health check

### Frontend pages (Compose)

| Page | URL | What you do there |
| ---- | --- | ----------------- |
| **Home** | `/` | Marketing landing (hero + how KitchenLab is organized) |
| **Ask** | `/ask` | Chat with `POST /agent/ask` (learn / cook / diagnose / …) |
| **Recipes** | `/recipes` | Science-annotated generate + personal cookbook |
| **Lab** | `/lab` | Techniques library, experiments (+ draft photos), notebook |
| **Calculators** | `/calculators` | Brine, scale, baker’s %, volume→grams (Python math) |
| **My kitchen** | `/kitchen` | Register/login, profile (oven/allergens), equipment |

Sign in on **My kitchen** so Ask/Lab can send a Bearer token and personalize.

Stop with `Ctrl+C`, or `docker compose down`. Add `-v` to also wipe the database volume.

### First-time database setup

With the stack running, apply migrations and seed data:

```bash
docker compose exec backend alembic upgrade head

docker compose exec backend python -m app.seeds.safety_seed
docker compose exec backend python -m app.seeds.knowledge_seed
docker compose exec backend python -m app.rag.ingestion          # embed passages (needs OPENAI_API_KEY)
docker compose exec backend python -m app.seeds.symptoms_seed
docker compose exec backend python -m app.seeds.food_seed
docker compose exec backend python -m app.seeds.techniques_seed
```

Seeds are additively idempotent — safe to re-run.

## Useful API routes

Full list and try-it-out forms: http://localhost:8000/docs

| Area        | Endpoints (summary)                                      |
| ----------- | -------------------------------------------------------- |
| Auth        | `POST /auth/register`, `/auth/login`, `GET /auth/me`     |
| Agent       | `POST /agent/ask` (optional Bearer for personalization)  |
| Diagnose    | `POST /diagnose/start`, `/diagnose/conclude`             |
| Recipes     | `POST /recipes/generate`, `/recipes/adapt`, `GET /recipes/{id}` |
| Substitute  | `POST /substitute`                                       |
| Kitchen     | `GET /kitchen`, `PUT /kitchen/profile`, equipment CRUD   |
| Techniques  | `GET /techniques`, `GET /techniques/{slug}`              |
| Lab         | `/experiments`, `/notebook`, `/attachments/...`          |
| Calculators | `/calculators/...` (units, brine, scaling, baker’s %)    |
| Safety      | internal temps + allergen scan                           |
| Knowledge   | semantic search over cited passages                      |

## Tests & eval harness

```bash
# Unit tests + deterministic eval scenarios (CI)
docker compose exec backend pytest -v --ignore=tests/test_live_evals.py

# Human-readable eval report
docker compose exec backend python -m app.evals.report

# Optional live LLM checks (costs API credits; needs seeded DB + key)
LIVE_EVALS=1 docker compose exec -e LIVE_EVALS=1 backend pytest -v -m live
```

The **eval harness** encodes trust contracts as scenarios (e.g. marinade must not boost “no pre-salting”; chicken below 74°C is raised to the USDA floor; 1 tsp salt ≠ cup-scale grams). Deterministic scenarios always run in GitHub Actions; live tests are opt-in.

## Project layout

```
backend/
  app/
    agent/          # intent router + mode dispatch
    calculators/    # deterministic math
    diagnosis/      # cause ranking + hard evidence rules
    evals/          # scenario catalog + grader
    kitchen/        # profile personalization
    lab/            # experiment design helpers
    llm/            # OpenAI client (phrasing only)
    rag/            # embeddings + pgvector retrieval
    recipes/        # generate / adapt
    safety/         # temps + allergens
    seeds/          # idempotent seed scripts
    storage/        # local + S3 photo backends
    routers/        # FastAPI HTTP surface
  tests/
  alembic/          # DB migrations
  Dockerfile.prod
frontend/           # Next.js app (+ Dockerfile.prod)
infra/terraform/    # AWS: VPC, ECR, RDS, S3, ALB, ECS
render.yaml         # Live Render backend Blueprint
docker-compose.yml
```

## AWS reference deployment (optional)

Production images:

- `backend/Dockerfile.prod`
- `frontend/Dockerfile.prod` (Next.js `output: "standalone"`)

```bash
# See infra/README.md for the full three-phase flow:
# 1) terraform apply (ECR, RDS, S3, ALB, VPC) with images left empty
# 2) docker build/push to ECR  (or GitHub Actions deploy.yml)
# 3) set backend_image / frontend_image and terraform apply again
```

CD pushes images only; it does **not** auto-`terraform apply`, so CI cannot surprise-bill you.

## Notes for contributors / interviewers

- **Citations are claim-level** — passages carry scope, confidence, and source metadata.
- **Safety and arithmetic outrank the LLM** — internal temps, oven dial offsets, and volume→grams are enforced in Python after generation.
- **Diagnosis scoring is pure math**; the LLM only maps free-text answers to supports / contradicts / neutral (with keyword hard rules for known failure modes).
