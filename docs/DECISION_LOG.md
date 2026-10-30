# SWASTHYA — DECISION LOG

> Record of finalized project decisions.
> This document preserves the reasoning and implementation implications of important architectural and project decisions.

---

## Decision 001 — Canonical Environment Configuration

**Date:** 2026-10-08

**Section:** Environment Configuration

**Status:** DECIDED

### Decision

Swasthya will use a **single root `.env` file as the canonical local environment configuration** for the entire repository.

The repository will contain:

```text
Swasthya/
├── .env.example
├── .env
├── docker-compose.yml
├── backend/
├── frontend/
└── docs/

The actual .env file is local-only and must never be committed.

.env.example is the committed, public-safe configuration template.

There will be no separate backend/.env or backend/.env.example as an independent configuration source.

Reason / Rationale

The project is a single repository containing the backend, frontend, agent layer, infrastructure, and supporting services.

Maintaining multiple environment files creates ambiguity about which configuration is authoritative and can cause Docker Compose and Django to read different values.

A single root environment configuration gives the project one clear source for local configuration and reduces configuration drift.

Implementation Implications
Move the canonical environment template to the repository root.
Django configuration will use the root environment configuration.
Docker Compose will use the root environment configuration.
The backend must not maintain a competing environment template.
Claude 1's existing backend/.env.example must be removed or replaced as part of the approved correction.
Docker Compose configuration must be corrected so that environment-variable interpolation behaves consistently.
Environment configuration must remain compatible with both local development and Docker-based development.
The exact production environment mechanism may be decided separately later.
Constraints / Non-Negotiable Rules
Never commit .env.
Never put real API keys, passwords, tokens, or secrets in .env.example.
.env.example must contain placeholders only.
Do not create duplicate environment configuration sources.
Do not silently introduce new environment variables without documenting them.
Environment configuration must not change the ownership boundaries between Claude workstreams.
Supersedes

Claude 1's initial Phase 1 implementation, which contains:

/backend/.env.example

and a separate backend environment arrangement.

That implementation is frozen and will be corrected before integration.

Related Sections
Project Security
Git Repository
Docker / Infrastructure
Backend Configuration
Claude 1 Workstream
Claude 2 Workstream
Claude 4 Workstream

---

## Decision 002 — Cursor Implementation Environment

**Date:** 2026-10-08

**Section:** Development model

**Status:** DECIDED

### Decision

Swasthya is implemented in Cursor. When an AI model is used inside Cursor for this project, use an available Grok or Composer model.

Backend, nutrition, frontend, and agent remain logical ownership boundaries inside one codebase. They are not separate implementation conversations.

### Reason

The project is no longer developed through four separate Claude conversations. One repository and one implementation environment avoid duplicate models and conflicting changes.

### Implementation implications

Do not create a second implementation of a responsibility that already has an owner.
Do not rebuild the existing backend foundation.
Do not change the technology stack.
Do not start the next product phase until the current phase is verified.

### Constraints

Refresh-token browser storage, timezone handling, speech-to-text for uploaded audio, object storage, and image processing remain open. The first client stores tokens in session storage, and the first embedding model is `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`. Both are replaceable. See Decision 004.
Host port 5433 for PostgreSQL is a local development accommodation so Compose can run beside an existing PostgreSQL install. It does not change the database or the in-network port.

---

## Decision 003 — Text Agent Provider Fallback

**Date:** 2026-10-08

**Section:** Agent

**Status:** DECIDED

### Decision

The text agent runs as a LangGraph workflow inside Django. If `GEMINI_API_KEY` is set, Gemini extracts the foods and quantities. If it is empty, a rules provider reads clear sentences such as "I ate 2 idlis for breakfast."

The verified dataset and the calculation service still produce the nutrition numbers. The provider only identifies the food, quantity, and unit.

Access and refresh tokens are returned in the JSON body. How a browser stores them is still undecided.

### Reason

Local development has to log a clear meal without an external key, and the provider has to be replaceable.

### Constraints

Do not treat the rules provider as a general nutrition expert.
Do not invent a gram weight for bowl, plate, or glass.

---

## Decision 004 — Initial Embeddings, Voice Transcripts, and Temporary Token Storage

**Date:** 2026-10-08

**Section:** Search, voice, and the browser client

**Status:** DECIDED for the first usable version. Each piece stays replaceable.

### Decision

Food-name search may use `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` through fastembed. Vectors are 384 dimensions and are stored with pgvector. This model does not use retrieval prefixes. A vector neighbor is only a clarification candidate. It never becomes a logged food by itself.

Voice logging accepts a transcript produced by the device speech recognizer and sends it through the same text workflow with `input_type` voice. The server does not transcribe uploaded audio.

Image identification stays unavailable. The API returns `not_available` and does not guess a food or a quantity.

The React client keeps access and refresh tokens in `sessionStorage`. That is a temporary client choice so the app can be used in this tab. It is not the final browser-storage decision, and it is not an httpOnly cookie design.

### Reason

The product needs search beyond exact names, a voice path that does not pretend to hear audio, and a client that can call the API. The vision provider and the permanent token design are still open.

### Constraints

Do not treat a vector neighbor as a confirmed food.
Do not transcribe audio on the server until a speech-to-text provider is chosen.
Do not infer nutrition from an image.
Do not describe `sessionStorage` as the settled storage design.

## Decision 005 — Recipes, Weekly Plans, Groceries, and Grounded Suggestions

**Date:** 2026-10-22

**Section:** Product scope and nutrition authority

**Status:** DECIDED

### Decision

Swasthya now includes a curated recipe collection, a weekly meal planner, a private grocery list, and a suggestions page. These sit beside meal logging. They do not replace it.

The recipe text is an original Swasthya collection stored in the application. It is not scraped and it is not taken from Anuvaad. Anuvaad INDB 2024.11 remains the only nutrition authority. An ingredient counts toward recipe nutrition only when it maps to a verified food and a supported quantity. If it does not, the recipe nutrition is incomplete and the nutrient totals are omitted.

A planned meal is not a consumed meal. Daily and weekly eaten totals continue to come only from logged meals.

Grocery generation may add quantities together only when the verified food is the same and the units match, or when both amounts are weights in grams or kilograms. Unmapped ingredients stay on their own lines. Refreshing a week replaces that week's generated rows and leaves manually added rows in place.

Suggestions may show today's remaining targets and calculated recipe figures. They must not claim a recipe meets a goal unless the stored numbers establish that, and this version does not make that claim.

Pantry stock, expiry, and inventory forecasting stay out of scope.

### Reason

The product needs planning and shopping without inventing nutrition or mixing a plan into what was eaten. The Anuvaad workbook does not contain ingredient lists or cooking steps, so the catalogue has to be a documented original collection.

### Constraints

Do not let a model invent ingredient quantities or nutrient values.
Do not add planned recipes into consumed dashboard totals.
Do not delete manual grocery items when a week is regenerated.
Do not describe an incomplete recipe calculation as verified.

## Decision 006 — Narrow the immediate product to logging, profile, and targets

**Date:** 2026-10-22

**Section:** MVP scope

**Status:** DECIDED. This narrows what the website shows now. It does not delete Decision 005’s backend work.

### Decision

The immediate Swasthya website is a landing page, registration and login, a profile that holds body details and nutrition targets, manual meal logging, and chat meal logging.

Recipes, the weekly planner, grocery lists, the suggestions page, and a separate today dashboard are deferred. Their backend models and APIs stay in the repository. They are not linked from the primary navigation.

The navbar is Home, Log Meal, and either Login and Sign Up or Profile.

### Reason

The visible product had grown past the workflow that needs to be reliable: discover the app, create an account, set a profile, and log a meal that is actually saved.

### Constraints

Do not treat a deferred page as part of the current navigation.
Do not delete the recipe, plan, or grocery backend unless a later decision says to.
Do not count a meal as saved until the backend confirms it.

## Decision 007 — Goal range, allergen filters, languages, and speech-to-text

**Date:** 2026-10-26

**Section:** Progress, profile, conversation, voice

**Status:** DECIDED

### Decision

A calorie day is `met` when saved-meal intake is within `GOAL_CALORIE_TOLERANCE` (default 5%) of the active calorie target. Zero saved meals is `no_data`, not a miss. Intake above the band is `above`, not success. Dashboard, celebrations, and suggestions use `apps.progress.goal`.

Anuvaad food records have no ingredient lists. Allergy exclusions match declared allergens and aliases against food names in backend code, before and after ranking. Remaining catalogue items are never described as allergy-safe. Suggestions are not meals.

User messages stay in the original script. OpenRouter remains the conversational model. Internal English translation is metadata only. Speech uses Sarvam Saaras v4 through Django (`SARVAM_API_KEY`); the browser does not receive that key. Transcripts are not auto-submitted.

### Constraints

Do not invent nutrient values or allergen-free claims.
Do not celebrate drafts, failed saves, or dashboard loads.
Do not store raw audio after transcription.
Do not put Sarvam or OpenRouter keys in the frontend.