# SWASTHYA — PROJECT CONTEXT

> Master source of truth for the Swasthya project.
> All developers and AI agents must read this document before making implementation decisions.

---

## 1. PROJECT IDENTITY

**Project Name:** Swasthya

**Meaning:** Swasthya (स्वास्थ्य) refers to health and well-being.

**Project Type:** Agentic AI Nutrition Tracker

**Repository:** `Swasthya`

**Repository Visibility:** Public

**Primary IDE:** Cursor

**Development Model:** Four specialized Claude agents working under centralized coordination.

---

## 2. PRODUCT VISION

Swasthya is an intelligent nutrition tracker that allows users to record what they eat using natural language, voice, and eventually images, while relying on a verified nutrition dataset for nutritional truth.

The system combines:

- personalized nutrition targets
- verified food nutrition data
- intelligent food identification and resolution
- deterministic nutrition calculation
- agentic workflow orchestration
- meal logging and history
- daily nutrition progress
- weekly streaks
- monthly streaks
- multilingual interaction

The system must behave like a real functioning application, not merely a chatbot demonstration.

The agent is responsible for understanding user input and orchestrating actions.

The verified nutrition dataset remains the authority for nutritional facts.

---

## 3. CORE USER FLOW

A user should be able to provide input such as:

> "I ate 2 idlis for breakfast."

or:

> "I had 250 grams of rice."

or eventually:

> Voice input

or eventually:

> Food image

The system should:

1. understand the user's intent
2. identify the food
3. resolve the food to a stable `food_code`
4. determine and validate quantity
5. obtain verified nutrition data
6. deterministically calculate nutrition for the requested quantity
7. persist the meal
8. confirm that persistence succeeded
9. return the result to the user
10. update the user's progress

The LLM must never invent nutrition facts.

---

# 4. FINAL TECHNOLOGY STACK

## Backend

- Django
- Django REST Framework
- PostgreSQL
- Django ORM
- JWT authentication through DRF
- drf-spectacular / OpenAPI

## Vector / Retrieval

- PostgreSQL + pgvector
- multilingual embeddings
- vector retrieval for food identification and search

## Agent Layer

- LangGraph
- Gemini initially as the LLM / multimodal provider
- provider abstraction so the provider can be replaced later

## Frontend

- React
- TypeScript
- React Router

## Async / Background Processing

- Celery
- Redis

## Infrastructure

- Docker
- Docker Compose
- Git
- GitHub

## Testing

- Pytest / Django / DRF testing
- frontend testing
- integration testing

## Storage

Use a storage abstraction for uploaded media.

The exact cloud/object-storage vendor is not finalized.

---

# 5. HIGH-LEVEL ARCHITECTURE

```text
React
  |
  | REST / JSON
  v
Django + Django REST Framework
  |
  +-------------------+
  |                   |
  v                   v
PostgreSQL        Application Services
  |
  +-- pgvector
  |
  +-- Agent Layer
  |      |
  |      +-- LangGraph
  |
  +-- Celery / Redis

More precise trust boundary:

User
  |
  v
React
  |
  v
Django / DRF
  |
  v
Authenticated Agent Workflow (LangGraph)
  |
  v
Controlled Tools / Services
  |
  v
Django Validation / Business Logic
  |
  v
Django ORM
  |
  v
PostgreSQL
Critical architecture rule

The LLM/agent must NEVER directly execute arbitrary SQL against PostgreSQL.

The agent must interact with controlled tools/services.

Django remains the application's trust boundary.

6. IMPORTANT ARCHITECTURAL PRINCIPLES
6.1 Nutrition truth

The verified nutrition dataset is authoritative.

The LLM must never fabricate nutrition values.

The LLM may interpret user language, but must obtain nutritional values from the verified structured dataset.

6.2 RAG purpose

RAG / vector search is primarily used to answer:

"Which food does the user mean?"

RAG is NOT the authority for nutrition values.

The structured nutrition data answers:

"What nutrition does this food contain?"

The deterministic calculation engine answers:

"How much nutrition corresponds to this quantity?"

The application database answers:

"What has this user actually logged?"

6.3 Separation of concerns
Food identity
    -> RAG / search / resolution

Nutrition facts
    -> verified structured dataset

Quantity calculation
    -> deterministic calculation service

User records
    -> PostgreSQL application data

Agent orchestration
    -> LangGraph
7. NON-NEGOTIABLE RULES

These rules apply to the entire project.

Nutrition
Never invent nutrition values.
Never treat missing values as zero.
A known zero and a missing value are different.
The LLM must not independently produce authoritative nutrition values.
Nutrition calculations must be deterministic.
The verified dataset is the source of truth.
Food identity should resolve to a stable food_code.
Historical nutrition records must remain interpretable through dataset/calculation versioning.
Quantity
Quantity is mandatory when required for calculation.
Missing quantity must result in clarification.
Supported weight units include grams and kilograms.
Serving and piece units are allowed only when their nutrition basis is verified by the dataset.
Do not invent conversions for units such as bowl, plate, handful, glass, spoon, etc. unless a verified dataset basis exists.
Never silently invent serving weights.
Agent
The agent must use controlled tools/services.
The agent must not directly access PostgreSQL.
The authenticated user's identity comes from the backend/security context, not from LLM-generated input.
The agent must not claim an action succeeded until the backend confirms success.
Ambiguous food identification requires clarification.
Unsupported quantity/unit requires clarification.
Image-based food identification is probabilistic.
An image must never cause the agent to invent an exact quantity.
Authorization / Security
Users may access only their own private data.
Never trust a client-supplied user_id.
Django must enforce authentication and authorization.
Agent tools must execute under an authenticated user context.
Secrets must never be committed.
.env files must not be committed.
Sensitive tokens and private data must not be unnecessarily written to logs.
Uploaded media must be access-controlled and validated.
Targets
User-customized targets must never be silently overwritten by newly generated suggestions.
Suggested/system targets and user-customized targets must remain distinguishable.
Target history must be preserved.
Repository
main is the stable branch.
No direct uncontrolled development on main.
Work should happen in focused branches.
Changes must be reviewed before integration.
No destructive or unrelated changes.
Avoid duplicate implementations between Claude workstreams.
8. VERIFIED NUTRITION DATASET
Dataset

File: Anuvaad_INDB_2024.11.xlsx

This is the authoritative nutrition dataset selected for the project.

The original source artifact must remain read-only.

The application should use a repeatable, validated, versioned ingestion process to load data into PostgreSQL.

Known dataset characteristics

Approximate current inspection:

~1,014 food records
82 columns
no duplicate food_code
source categories:
asc_manual
bfp_manual
open_source_recipes
some foods do not have servings_unit
some records contain serving-level nutrient data despite missing serving-unit metadata

Missing values must remain missing.

9. NUTRITION DATA ARCHITECTURE

Nutrition-domain ownership belongs to Claude 2.

NutritionDatasetVersion

Tracks the source and version of the nutrition dataset.

Conceptual fields:

id
name / version
source
created_at
is_active
Food

Represents stable food identity.

Conceptual fields:

id
food_code
food_name
primary_source
serving_unit

food_code is the stable food identity.

FoodNutrition

Stores nutrient values associated with a food and dataset version.

MVP fields include:

id
food_id
dataset_version_id

energy_kcal
carb_g
protein_g
fat_g
fibre_g

calcium_mg
iron_mg
magnesium_mg
potassium_mg
sodium_mg
zinc_mg

vita_ug
vitb1_mg
vitb2_mg
vitb3_mg
vitb6_mg
folate_ug
vitc_mg
vitd2_ug
vitd3_ug
vite_mg
vitk1_ug
vitk2_ug
FoodServingNutrition

Stores serving-level nutrition only when a verified serving basis exists.

FoodEmbedding

Conceptual fields:

id
food_id
embedding
text_representation
language

Used for search and resolution.

10. NUTRITION SCOPE
Core nutrition calculations

The MVP focuses primarily on:

energy / calories
carbohydrates
protein
fat
fibre
Selected minerals for display
calcium
iron
magnesium
potassium
sodium
zinc
Selected vitamins for display
vitamin A
vitamin B1
vitamin B2
vitamin B3
vitamin B6
folate
vitamin C
vitamin D2
vitamin D3
vitamin E
vitamin K1
vitamin K2
Explicitly excluded from MVP focus

Detailed fat subcolumns are not a core requirement:

SFA
MUFA
PUFA
individual fatty acids

Other non-MVP nutrient fields include:

cholesterol
free sugar
phosphorus
copper
selenium
chromium
manganese
molybdenum
vitamin B5
vitamin B7
carotenoids
other non-MVP fields

Do not merge folate with another field simply because they are chemically related.

Keep D2 and D3 distinct when the dataset distinguishes them.

11. QUANTITY MODEL

Canonical normalized representation:

{
  "food_code": "XXXXX",
  "quantity": 250,
  "unit": "g"
}

Multiple foods should be represented as an array of normalized food items.

A richer internal representation may include:

{
  "food_code": "XXXXX",
  "quantity": 2,
  "unit": "piece",
  "input_source": "voice",
  "confidence": 0.94
}

Possible input_source values include:

text
voice
image
manual UI
IoT / future scale
12. DETERMINISTIC NUTRITION CALCULATION

For weight-based nutrition:

multiplier = quantity_in_grams / 100

Then:

calculated_nutrient = base_nutrient * multiplier

For verified serving-based nutrition:

calculated_nutrient = per_serving_nutrient * number_of_servings

Each food is calculated independently.

For multiple foods:

meal_total = sum(each calculated food item)

The calculation engine must not rely on LLM arithmetic for authoritative nutrition.

13. PERSONALIZED TARGET ENGINE

Inputs:

date of birth
age derived from date of birth
sex
height
weight
activity level
goal
Activity factors
SEDENTARY          = 1.20
LIGHTLY_ACTIVE     = 1.375
MODERATELY_ACTIVE  = 1.55
VERY_ACTIVE        = 1.725
Mifflin-St Jeor

Men:

RMR = (10 * kg) + (6.25 * cm) - (5 * age) + 5

Women:

RMR = (10 * kg) + (6.25 * cm) - (5 * age) - 161

Then:

TDEE = RMR * activity_factor
Goal defaults

Maintenance:

calories = TDEE

Weight loss:

calories = TDEE - 500

Weight gain:

calories = TDEE + 300
Protein defaults

Maintenance:

0.8 g/kg

Weight loss:

1.2 g/kg

Weight gain:

1.0 g/kg
Fat

Default:

fat calories = target calories * 0.30
fat grams = fat calories / 9
Carbohydrates
protein calories = protein grams * 4
fat calories = fat grams * 9

remaining calories =
target calories - protein calories - fat calories

carb grams = remaining calories / 4
Fibre
fibre target =
target calories / 1000 * 14

These are application policy defaults, not medical prescriptions.

The rules should be implemented in backend/business logic and kept configurable.

The LLM must not independently calculate authoritative targets.

14. TARGET DATA MODEL

Conceptual structure:

NutritionTarget

id
user
source
effective_from
effective_until

calories
protein
carbohydrates
fat
fibre
...

Possible target source values:

SYSTEM_SUGGESTED
USER_CUSTOMIZED

Target history must be preserved.

A new system suggestion must not silently overwrite an active custom target.

15. APPLICATION DATA MODEL

Django authentication provides the primary User entity.

User

Conceptual fields:

id
email
password
name
created_at
updated_at
UserProfile
user_id
date_of_birth
sex
height
weight
activity_level
goal
Meal
id
user
timestamp
meal_type
created_at
MealItem
id
meal
food
quantity
unit
input_source
confidence
nutrition_snapshot
dataset_version
calculation_version

MealItem must reference Claude 2's Food model.

Do not duplicate Food in Claude 1's workstream.

Conversation
id
user
created_at
updated_at
Message
id
conversation
role
content
timestamp
input_type
AgentAction
id
conversation
action_type
tool_name
input
output
status
timestamp

This is the persistence/audit record for agent actions.

16. OWNERSHIP MODEL
Claude 1 — Backend & Core Application

Owns:

Django / DRF
authentication
JWT
user profile
targets
meals
meal history
dashboard
progress
streaks
authorization
serializers
URLs
backend services
API documentation
backend testing
Conversation persistence
Message persistence
AgentAction persistence

Claude 1 must reference Claude 2's Food model.

Claude 1 must not create a duplicate Food model.

Claude 2 — Nutrition Data & RAG

Owns:

Anuvaad INDB ingestion
validation
normalization / mapping
NutritionDatasetVersion
Food
FoodNutrition
FoodServingNutrition
FoodEmbedding
pgvector
embeddings
multilingual food search
food resolution
deterministic nutrition calculation
nutrition testing

Claude 2 must not build the main application backend, frontend, or LangGraph orchestration.

Claude 3 — React Frontend

Owns:

React
TypeScript
routing
authentication UI
onboarding
profile
dashboard
meal views
progress
targets
streaks
chat UI
settings
responsive frontend
frontend API layer
frontend tests

Claude 3 must consume backend contracts.

React must not independently become the authority for:

nutrition calculations
target calculations
daily totals
food resolution
Claude 4 — Agentic AI & Integration

Owns:

LangGraph
graph state
agent workflow
intent extraction
entity extraction
food-resolution orchestration
tool orchestration
Gemini/provider abstraction
clarification workflow
voice integration
future image integration
agent integration tests
agent behavior
determining which agent actions should be audited

Claude 4 must consume Claude 1 and Claude 2 through controlled interfaces.

Claude 4 must not create duplicate backend persistence models.

Claude 4 must not create a second conversation or audit database.

17. CONVERSATION / AGENT ACTION OWNERSHIP

Claude 1 owns the Django persistence layer for:

Conversation
Message
AgentAction

Claude 4 owns:

agent behavior
LangGraph workflow
tool orchestration
deciding which agent action should be recorded

Claude 4 must use Claude 1's persistence/services rather than creating another conversation or audit database.

18. FOOD OWNERSHIP

Claude 2 owns:

Food
FoodNutrition
FoodServingNutrition
FoodEmbedding
NutritionDatasetVersion
nutrition-domain logic

Claude 1 owns:

Meal
MealItem
application persistence

MealItem references Claude 2's Food model.

There must be only one canonical Food model.

19. AGENT ARCHITECTURE

Typical workflow:

User text / voice / image
        |
        v
Input processing
        |
        v
Intent / entity extraction
        |
        v
Food resolution
        |
        v
Quantity / unit validation
        |
        v
Nutrition lookup
        |
        v
Deterministic calculation
        |
        v
Backend persistence
        |
        v
Confirmed response

Potential tools/services:

search_food()
resolve_food()
get_food_nutrition()
calculate_nutrition()
create_food_log()
get_daily_progress()
get_remaining_targets()

Exact internal organization may evolve, but the trust boundaries must remain intact.

20. AGENT RESULT STATES

Conceptual statuses:

NEEDS_CLARIFICATION
PREVIEW
SUCCESS
ERROR
MVP logging behavior

For an unambiguous, valid input:

food confidently resolved
quantity available
unit supported
nutrition successfully calculated
backend persistence succeeds

the system should log the entry immediately.

A separate confirmation step is not mandatory for every input.

Example:

"I ate 2 idlis."

If the conditions above are satisfied, the result may be:

SUCCESS

Clarification is required when:

food is ambiguous
quantity is missing
unit is unsupported
the food cannot be confidently resolved
validation fails

PREVIEW remains available as an optional/future interaction state.

21. IMAGE INPUT

Image input is planned for a later phase.

Potential flow:

Image
  |
  v
Vision model
  |
  v
Probable food identification
  |
  v
Verified dataset resolution
  |
  v
Quantity determination
  |
  v
Deterministic nutrition calculation
  |
  v
Persistence

An image alone cannot establish an exact quantity unless a reliable quantity source exists.

The system must never fabricate an exact weight.

22. FUTURE IOT SUPPORT

The software architecture must remain compatible with a future weighing scale.

Future flow:

Weighing scale
       +
Food identity from voice / image / text
       |
       v
Same food-resolution pipeline
       |
       v
Same deterministic nutrition engine
       |
       v
Same meal logging pipeline

The future hardware must not require a completely separate nutrition pipeline.

IoT is future scope, not MVP.

23. VOICE INPUT

Voice input is part of the intended application scope.

Conceptual flow:

Audio
  |
  v
Speech-to-text
  |
  v
Agent workflow
  |
  v
Food resolution
  |
  v
Quantity validation
  |
  v
Nutrition
  |
  v
Meal logging

The exact speech-to-text implementation is replaceable.

24. MULTILINGUAL SUPPORT

The application should support multilingual food interaction.

Multilingual handling may involve:

language detection
multilingual embeddings
multilingual food search/resolution
multilingual LLM/provider support

Translations must not be fabricated as authoritative food identities.

Resolved food identity must ultimately map to a verified dataset food / food_code.

25. FRONTEND SCOPE

Core React screens:

authentication
onboarding/profile
dashboard
meal history
meal detail
targets
progress
streaks
chat
settings

The frontend must consume backend API contracts.

React must not be the authority for:

nutrition calculations
target calculations
daily nutrition totals
food resolution

These belong to backend/domain services.

26. API CONTRACTS

Initial REST API prefix:

/api/

not /api/v1/.

Communication format:

REST / JSON

Use standard HTTP status codes and structured error responses.

Authentication
POST /api/auth/register/
POST /api/auth/login/
POST /api/auth/refresh/
POST /api/auth/logout/
GET  /api/auth/me/
Profile
GET   /api/profile/
PUT   /api/profile/
PATCH /api/profile/
Targets
GET  /api/targets/
GET  /api/targets/history/
POST /api/targets/suggest/
POST /api/targets/customize/
POST /api/targets/accept-suggestion/
Foods
GET /api/foods/search/?q=...
GET /api/foods/{food_code}/
Meals
POST   /api/meals/
GET    /api/meals/
GET    /api/meals/{id}/
PATCH  /api/meals/{id}/
DELETE /api/meals/{id}/
Dashboard
GET /api/dashboard/
Daily progress
GET /api/progress/daily/?date=YYYY-MM-DD
Streaks
GET /api/streaks/
Agent
POST /api/agent/chat/
POST /api/agent/voice/
POST /api/agent/image/

The image endpoint is reserved/planned and does not need to be implemented in the initial MVP.

Conversations
GET /api/conversations/
GET /api/conversations/{id}/
API documentation

Use drf-spectacular / OpenAPI.

27. FRONTEND AGENT RESPONSE CONTRACT

Chat responses must clearly communicate the result state.

Possible states:

SUCCESS
NEEDS_CLARIFICATION
PREVIEW
ERROR

Critical rule:

SUCCESS must only be returned when the backend confirms that the requested action succeeded.

The frontend must not infer successful persistence simply because an API request was sent.

28. STREAKS

Streaks are derived from actual user activity.

They are not a separate source of truth.

The source of truth is logged meal/activity data.

The application should support:

weekly streak
monthly streak

The exact streak calculation will be implemented centrally in backend logic.

29. MVP SCOPE

The MVP includes:

authentication
user profile/onboarding
personalized target generation
target customization
verified nutrition dataset
food search/resolution
deterministic nutrition calculation
meal logging
meal history
dashboard
daily progress
weekly streaks
monthly streaks
text-based agentic food logging
conversation history

Voice is intended scope and may be implemented immediately after stable text-agent integration.

30. FUTURE SCOPE

Future capabilities include:

image food input
IoT weighing scale integration
richer recommendation engine
additional input modalities
additional nutrition capabilities
31. EXCLUDED FROM CURRENT SCOPE

The following are not current core requirements:

pantry/inventory management
detailed fatty-acid analysis
highly granular micronutrient calculation

Do not expand project scope without an explicit project decision.

32. GIT / BRANCHING MODEL

Primary branch:

main

Planned work branches:

claude/backend
claude/nutrition
claude/frontend
claude/agent

The exact naming may be refined when branch setup begins.

main represents stable, reviewed, accepted work.

No Claude should directly make uncontrolled changes to main.

Prefer focused commits and pull requests.

33. CRITICAL DEVELOPMENT WORKFLOW

This is a project-level non-negotiable.

No Claude receives permission to implement its entire roadmap upfront.

The workflow is:

PLAN
  |
  v
AUTHORIZE ONE PHASE
  |
  v
CLAUDE IMPLEMENTS ONLY THAT PHASE
  |
  v
CLAUDE STOPS
  |
  v
INSPECT
  |
  v
TEST
  |
  v
REVIEW
  |
  +----> FIX IF NECESSARY
  |
  v
ACCEPT
  |
  v
INTEGRATE
  |
  v
AUTHORIZE NEXT PHASE

Understanding the entire roadmap does NOT constitute authorization to implement it.

34. CENTRAL COORDINATION MODEL

The project owner/coordinator centrally manages all four Claude workstreams.

The coordinator decides:

which Claude works next
which phase is authorized
what exact changes are permitted
whether the implementation is correct
whether the implementation respects architecture
whether it conflicts with another workstream
whether interfaces remain compatible
whether tests are sufficient
whether a phase is accepted
when the next phase can begin

Individual Claudes must not independently redefine:

product architecture
ownership boundaries
project scope
non-negotiable rules

# 34A. ENVIRONMENT CONFIGURATION

Swasthya uses a **single root `.env` file as the canonical local environment configuration** for the entire repository.

The intended structure is:

```text
Swasthya/
├── .env.example
├── .env
├── docker-compose.yml
├── backend/
├── frontend/
└── docs/

35. CURRENT AUTHENTICATION DECISION STATUS

Authentication architecture is partially finalized at the backend/API level.

JWT is the selected authentication mechanism.

However, the following are NOT yet independently finalized:

exact refresh-token storage strategy
refresh-token security policy
browser token-storage implementation details
httpOnly-cookie strategy, if used

Claude 3 must not independently decide these without explicit project approval.

36. DECISIONS NOT YET FINALIZED

Do not independently finalize these without explicit project approval:

exact embedding model
exact voice/STT provider
exact cloud/object-storage provider
detailed timezone policy
production deployment provider
exact image-processing pipeline
final API response schemas where not already explicitly defined
refresh-token storage mechanism
other architecture-affecting implementation details
Timezone

Do not add a timezone field to the user/profile schema unless separately approved.

Timezone handling will be addressed as a separate project decision.

37. SECURITY EXPECTATIONS

The application must:

authenticate users
authorize access to user-owned data
avoid trusting client-supplied ownership identifiers
validate all agent tool input
validate uploaded files
restrict file size/type where appropriate
protect uploaded media
keep secrets in environment variables
exclude secrets from Git
avoid leaking sensitive information in logs
use secure production configuration
preserve auditability of agent actions
38. TESTING EXPECTATIONS

Testing should cover the following areas.

Nutrition
nutrition calculations
serving calculations
weight conversions
missing values
food-code uniqueness
dataset validation
dataset versioning
Targets
age calculation
Mifflin-St Jeor calculations
activity factors
goal calculations
macro calculations
custom-target preservation
target history
Application
authentication
authorization
meal ownership
validation
API behavior
dashboard/progress
streak calculations
Agent
intent extraction
food resolution
ambiguity handling
missing quantity
unsupported units
tool invocation
persistence confirmation
SUCCESS / ERROR / CLARIFICATION behavior
end-to-end agent → tool → backend → persistence pipeline
Frontend
authentication states
loading states
error states
empty states
API integration
protected views
chat states
responsive behavior
39. DOCUMENTATION STRUCTURE

The project documentation will include:

docs/
├── PROJECT_CONTEXT.md
├── ARCHITECTURE.md
├── API_CONTRACTS.md
└── DECISION_LOG.md

PROJECT_CONTEXT.md is the master source of truth.

ARCHITECTURE.md will contain more detailed architecture documentation.

API_CONTRACTS.md will contain concrete API schemas and examples.

DECISION_LOG.md will record important finalized decisions.

When a major decision changes, update this file and the relevant detailed document.

40. PROJECT DECISION UPDATE FORMAT

Every newly finalized project decision should be recorded using:

PROJECT DECISION UPDATE
Date: [YYYY-MM-DD]
Section: [section name]
Status: DECIDED
Decision: [exact decision]
Reason / rationale: [why this was chosen]
Implementation implications: [what this changes]
Constraints / non-negotiable rules: [rules]
Supersedes: [previous decision, if any]
Related sections: [sections affected]
END PROJECT DECISION UPDATE
41. HOW AI AGENTS MUST USE THIS FILE

Before making implementation changes, every Claude must:

read this document
understand its assigned ownership
understand what the other Claudes own
check the current implementation status
identify the exact phase it has been authorized to implement
make only the authorized changes
stop when the authorized phase is complete

An agent must not infer authorization from the existence of a roadmap.

42. CURRENT PROJECT CHECKPOINT
Project

Swasthya

GitHub

Public repository:

https://github.com/lipikahr/Swasthya.git
Local path
C:\Projects\Swasthya
Current branch
main
Current repository preparation status

Completed:

GitHub repository created
repository made public
local repository initialized
GitHub remote connected
main branch established
docs folder created
PROJECT_CONTEXT.md created

Not yet completed:

initial repository commit
.gitignore
.env.example
README.md
detailed architecture document
API contract document
decision log
integration of Claude-generated application code
43. CURRENT CLAUDE STATUS
Claude 1 — Backend

Status:

STOPPED

Claude 1 previously built a Phase 1 backend foundation in its own working context.

That work has NOT yet been blindly accepted into this Swasthya repository.

It must be inspected before integration.

Claude 1 must remain stopped until explicitly authorized.

Claude 2 — Nutrition

Status:

STOPPED

Claude 2's understanding and ownership have been approved.

The Anuvaad workbook must be available in Claude 2's working environment before actual ingestion.

Claude 2 must not begin ingestion without explicit authorization.

Claude 3 — Frontend

Status:

STOPPED

Claude 3 previously built an initial React foundation/auth work in its own working context.

That work has NOT yet been blindly accepted into this Swasthya repository.

It must be inspected before integration.

Claude 3 must remain stopped until explicitly authorized.

Claude 4 — Agent

Status:

STOPPED

Claude 4's architecture understanding has been approved.

Claude 4 has not yet been authorized to implement the agent layer.

Claude 4 must remain stopped until explicitly authorized.

44. IMMEDIATE PROJECT ROADMAP

The current sequence is:

1. Repository governance
2. Initial repository commit
3. Inspect Claude 1 existing backend foundation
4. Inspect Claude 3 existing frontend foundation
5. Verify Claude 2 dataset availability and environment
6. Review existing code against master architecture
7. Establish concrete cross-Claude interfaces
8. Authorize exactly one next implementation phase
9. Implement
10. Inspect
11. Test
12. Accept
13. Integrate
14. Repeat

No large workstream should be authorized in one step.

45. MASTER RULE

When there is a conflict between an AI-generated implementation and this document:

This project context takes precedence until an explicit project decision changes it.

No implementation may silently change:

architecture
ownership
scope
database authority
nutrition authority
security rules
API responsibilities
agent responsibilities
non-negotiable project constraints