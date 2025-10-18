1. Overview & Objectives
1.1 Problem Statement

XYZ Capital is an investment management firm that manages portfolios for multiple clients.
Analysts and relationship managers regularly need to answer complex portfolio-related and market-impact questions from clients in natural language.

While structured data (portfolio holdings) and unstructured market data (news, filings) are available, analysts currently have to manually query multiple systems, which:

Increases response latency

Makes context tracking difficult

Limits personalization and reasoning across portfolio + market signals

The firm wants to build an AI-based assistant capable of understanding natural language queries and generating relevant, factual, and explainable answers — while handling ambiguous questions through memory and reasoning.

1.2 Objective

To design and implement a multi-agent intelligence system that can:

💬 Understand natural language investment queries.

📊 Analyze and explain portfolio performance, holdings, and allocations.

📰 Augment answers with real-time market intelligence — news, SEC filings, price trends.

🧠 Maintain conversational context and reasoning capability over multiple turns.

✅ Validate responses for correctness before returning them to the user.

1.3 Scope

The system supports:

Portfolio-related queries (e.g., “What are my holdings?”, “How is MSFT performing?”)

Market-related queries (e.g., “What’s the latest news on Tesla?”)

Hybrid queries involving both (e.g., “Will Apple earnings affect my portfolio?”)

Contextual follow-ups (e.g., “And what about the second stock?”, “Compare them”)

Automatic detection and fallback for errors.

The system does not provide:

Personalized financial advice or recommendations.

Order execution or trading functionality.

Long-term forecasting.

1.4 Design Goals
Goal	Description
Natural Query Understanding	Robust classification of portfolio, market, and hybrid queries, including ambiguous follow-ups.
Multi-Agent Orchestration	Dedicated specialized agents working collaboratively within LangGraph.
Reliable Data Integration	Integration with market APIs and internal portfolio data.
Reasoning Capability	Use of conversation memory and structured data for intelligent answers.
Validation & Safety	Built-in ValidatorAgent ensures response accuracy and consistency.
Scalability	Session isolation and architecture ready for multi-client, concurrent usage.
1.5 Target Users & Use Cases
User	Use Case
Relationship Manager	“What is my client’s top performing stock this month?”
Analyst	“Is there any significant market event affecting our portfolio?”
Client	“Show me my holdings and their returns.”
Advisor	“Compare Tesla and Microsoft performance and show allocation impact.”
1.6 Key Features

🔹 End-to-end multi-agent orchestration using LangGraph

🔹 LLM + Rule-based hybrid architecture for robust classification and planning

🔹 Portfolio + Market data fusion for hybrid reasoning

🔹 Session memory for context retention

🔹 Validator agent for output correctness

🔹 Streamlit UI for user interaction

🔹 Extensible architecture for production deployment


2. High-Level System Architecture

This section maps the objectives to a clean, modular architecture that is easy to demo now and safe to evolve later.

2.1 Layered View
┌─────────────────────────────────────────────────────────────────────┐
│                           Streamlit UI                              │
│  ─ Query box ─ Chat history ─ Client switcher ─ Snapshots ─ Debug ─ │
└─────────────────────────────────────────────────────────────────────┘
                 │ user query / session payload
                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Orchestration (LangGraph)                       │
│  State: {query, client_id, session_id, session, classification,     │
│          execution_plan, portfolio_resp, market_resp, final_resp,   │
│          workflow_log}                                              │
│                                                                     │
│  Nodes:                                                             │
│   1) QueryClassification → 2) Planner →                             │
│   3a) MarketAgent  ↘                                               │
│   3b) PortfolioAgent → 4) ResponseGenerator → 5) Validator → END    │
└─────────────────────────────────────────────────────────────────────┘
                 │ calls / returns
                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           Agent Layer                               │
│  QueryClassificationAgent  •  PlannerAgent  •  MarketAgent          │
│  PortfolioAgent            •  ResponseGeneratorAgent • Validator     │
└─────────────────────────────────────────────────────────────────────┘
                 │ data access + tools
                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Memory, Data & Knowledge Layer                   │
│  Session Memory (chat history, last results, metadata)              │
│  Portfolio Store (client holdings)                                  │
│  Market APIs (prices, news, filings) + Caches                       │
│  Knowledge Base (embedded filings/news for retrieval)               │
│  Deterministic Tools (Calculator, Price Cache)                      │
└─────────────────────────────────────────────────────────────────────┘

Why this layout?

Meets objectives: natural language understanding, portfolio + market analysis, reasoning with memory, validation before answering.

Resilient: each node has clear fallbacks; the validator guards the final output.

Traceable: every step is logged in workflow_log for audits and demos.

2.2 Agent Graph (LangGraph)

Execution paths (decided by the Planner based on classification):

Entry
  └─> QueryClassification
          └─> Planner
                ├─(intent=market)───> MarketAgent ───────────────┐
                ├─(intent=portfolio)─> PortfolioAgent ───────────┼─> ResponseGenerator ─> Validator ─> END
                └─(intent=hybrid)───> MarketAgent → PortfolioAgent┘


Hybrid: MarketAgent runs first to gather event context; PortfolioAgent then computes impact on holdings.

Fallbacks:

If LLM function calling fails in planning, rule-based mapping creates safe function_calls.

If an agent returns partial/empty data, the pipeline continues with conservative phrasing.

2.3 Agent Roles & Responsibilities (at a glance)
Agent	Core Responsibility	Inputs	Outputs	Key Fallbacks
QueryClassificationAgent	Intent + entity extraction (uses history + symbol map)	query, symbol map, conversation history	{intent, entities, confidence}	If low confidence → LLM classifier; else unknown + empty entities
PlannerAgent	Build execution plan + tool calls	classification, query, entities, history	{agents[], function_calls[]}	If LLM tools fail → rule-based function mapping
MarketAgent	Prices, headlines, filings	plan, entities, caches	market_response	Cache-first; API on miss; partial returns allowed
PortfolioAgent	Holdings, returns, allocation, comparisons	plan, client portfolio, price_cache	portfolio_response	If functions missing → default to holdings+returns
ResponseGeneratorAgent	Grounded, concise Markdown answer; hybrid reasoning	query, portfolio_response, market_response, history	final_response.text (+ data)	Templated summary if LLM fails
ValidatorAgent	Judge workflow correctness; pass/fail	workflow_log, original query	{validation_result, failed_agent?, reason?}	Default pass if invalid JSON to avoid blocking

A detailed, per-agent spec (IO, fallbacks, validation hooks) is in the “Agent Components” section of the doc.

2.4 Data Flow Between Agents

Stateful flow (core structures simplified):

UI → Orchestrator

{ query, client_id, session_id, session? }

QueryClassificationAgent

Reads: query, session.symbol_name_map, session.chat_history

Writes: classification = {intent, entities, confidence}

PlannerAgent

Reads: classification, query, session.chat_history

Writes: execution_plan = {agents[], function_calls[]}

MarketAgent (if planned)

Reads: execution_plan.entities, caches

Writes: market_resp = {status, results{ticker→{price, news[], filings[]}}}

PortfolioAgent (if planned)

Reads: execution_plan.entities, session.portfolio[client_id], price_cache

Writes: portfolio_resp = {status, results[], portfolio_summary{...}}

ResponseGeneratorAgent

Reads: query, portfolio_resp, market_resp, session.chat_history

Writes: final_response = {text, data:{portfolio, market_response}}

ValidatorAgent

Reads: workflow_log (every step’s input/output), query

Writes: {validation_result, failed_agent?, reason?}; orchestrator can re-run from failed node or pass through

Orchestrator → UI

Returns {final_response, portfolio_resp, market_resp}; memory manager updates session

2.5 Decision-Making Processes

A) Classification (Rule → LLM fallback)

Detects portfolio vs market vs hybrid via keywords + symbol map; uses conversation history for pronouns/ellipsis.

If confidence < threshold → LLM prompt with symbol map + history.

Output normalized to uppercase tickers.

B) Planning & Function Calling (LLM → Rule fallback)

LLM receives ENTITIES and decides functions (e.g., get_returns, compare_performance).

If no function returned but entities exist → rule-based mapping from verbs/intent.

Hybrid routes: MarketAgent → PortfolioAgent.

C) Hybrid Reasoning in Response

ResponseGenerator relates market events to owned positions (when overlapping), else cleanly separates.

Always grounded in structured outputs.

D) Validation Before Output

Validator checks: misclassification, wrong plan, empty/irrelevant agent data, ungrounded response.

If fail → orchestrator can restart from the failed node or return a safe fallback.

2.6 Integration with External Systems

Portfolio Store: internal dataset for 10 clients (grouped by client_id).

Exchange/Market APIs: e.g., Finnhub for prices, news; SEC for filings.

Knowledge Base: embedded filings/news for retrieval (semantic match on entity + query).

Deterministic Tools:

Calculator (returns, allocations, best/worst, comparisons)

Price cache (avoid duplicate API hits)

Security & Privacy

Session isolation by client_id and session_id.

No cross-client leakage; memory is scoped per session.

2.7 State Shape (canonical)
{
  "query": "...",
  "client_id": "CLT-001",
  "session_id": "sess-...",
  "session": {
    "chat_history": [ { "user": {...}, "system": {...} } ],
    "symbol_name_map": { "TSLA": ["tesla", "tesla inc"], ... },
    "portfolio": { "CLT-001": [ ... ] },
    "price_cache": { "TSLA": 245.6, ... },
    "last_portfolio": { ... },
    "last_market": { ... },
    "metadata": { "query_count": 7, "last_ts": "..." }
  },
  "classification": { "intent": "...", "entities": ["..."], "confidence": 0.92 },
  "execution_plan": { "agents": ["..."], "function_calls": [ ... ] },
  "market_resp": { ... },
  "portfolio_resp": { ... },
  "final_response": { "text": "...", "data": {...} },
  "workflow_log": { "agents_executed": [...], "steps": [ { "agent": "...", "input": {...}, "output": {...} } ] }
}

2.8 How This Meets the Objectives

Agent roles & graph: Clear nodes and responsibilities; hybrid path supported.

Data flow: Explicit, typed contracts between nodes; state shared and logged.

Decision-making: Rule→LLM fallbacks for classification/planning; validator gate before answer.

Integrations: Portfolio store + market/SEC APIs + knowledge base retrieval.

Production-ready: Deterministic tools for numbers, caches, validation, and session isolation.


This section details each agent’s purpose, inputs/outputs, core logic, fallbacks, memory usage, and validation hooks. It matches the LangGraph nodes in the architecture and the contracts used in code.

3.1 QueryClassificationAgent

Purpose
Understand the user’s intent and extract normalized entities (tickers/companies), leveraging conversation history and a symbol map derived from the client’s portfolio.

Primary Responsibilities

Classify intent: portfolio | market | hybrid | unknown

Extract entities from the query (tickers and company names)

Normalize entities to UPPERCASE tickers using the symbol map

Use conversation history to resolve pronouns/ellipsis (“they”, “it”, “compare them”)

Inputs

query: str

symbol_name_map: Dict[str, List[str]] (e.g., "TSLA": ["tesla", "tesla inc"])

conversation_history: Optional[str] (compact formatted turns)

Outputs

{
  "intent": "portfolio" | "market" | "hybrid" | "unknown",
  "entities": ["TSLA", "MSFT"],
  "confidence": 0.0
}


Core Logic

Rule-based pass

Keyword + regex (tickers \b[A-Z]{2,5}\b)

Name→ticker normalization via symbol_name_map

History-based disambiguation (follow-ups)

Confidence scoring (high for explicit cues; low for ambiguity)

Fallbacks & Error Handling

If intent == "unknown" or confidence < threshold → LLM classification with:

SYMBOL_NAME_MAP JSON

Conversation history

Instruction to infer ticker if map misses (else include raw name)

If LLM returns invalid JSON → return {intent: "unknown", entities: [], confidence: 0.0}

Memory Usage

Reads conversation_history

Does not write memory directly

Validation Hooks

Logs (query, symbol_name_map excerpt, history excerpt) and (intent, entities, confidence) into workflow_log

3.2 PlannerAgent

Purpose
Convert classification into an execution plan: which agents to run and which portfolio functions to call (via LLM tool-calling with a deterministic fallback).

Primary Responsibilities

Decide agents: PortfolioAgent, MarketAgent, or both (hybrid)

Prepare function_calls for portfolio analysis (e.g., get_returns, compare_performance)

Use entities already normalized by the classifier

Inputs

classification_result: {intent, entities, confidence}

query: str

conversation_history: Optional[str]

Outputs

{
  "intent": "portfolio",
  "entities": ["TSLA"],
  "confidence": 0.95,
  "agents": ["PortfolioAgent"],
  "function_calls": [
    {"name": "get_returns", "arguments": {"entities": ["TSLA"]}}
  ]
}


Core Logic

If intent="portfolio" → plan PortfolioAgent (+ function calls)

If intent="market" → plan MarketAgent

If intent="hybrid" → plan MarketAgent → PortfolioAgent

LLM tool-calling for function selection using:

ENTITIES (do not infer entities here)

Conversation history (to resolve “them/it”)

Strict function schema

Fallbacks & Error Handling

If LLM doesn’t produce a function call but entities exist → deterministic mapping:

“compare” → compare_performance(entities)

“return/performance of X” → get_returns([X])

“best/worst” → get_best_performers / get_worst_performers

“allocation/weight” → get_allocation / get_weight_in_portfolio

If still nothing → plan only the agent(s); PortfolioAgent defaults to holdings + computed returns

Sanitize bad tool JSON; log warnings

Memory Usage

Reads conversation_history

Does not write memory directly

Validation Hooks

Logs mapping from (intent, entities) → (agents, function_calls) to workflow_log

3.3 MarketAgent

Purpose
Fetch market intelligence for entities: latest price, top news, recent SEC filings. Use cache-first, then API on miss.

Primary Responsibilities

Retrieve prices, headlines, filings per ticker

Normalize result shape and cap counts (e.g., top 3 news)

Merge cache and fresh fetches

Inputs

execution_plan (intent, entities)

session (market cache handles)

Outputs

{
  "status": "success",
  "results": {
    "MSFT": { "price": 511.61, "news": ["..."], "filings": ["..."] },
    "TSLA": { "price": 245.60, "news": [], "filings": [] }
  },
  "message": "Fetched from cache or API"
}


Core Logic

For each entity:

Try cache for price/news/filings

If missing → fetch via APIs (e.g., exchange + SEC)

Normalize symbol keys and ensure deterministic JSON

Fallbacks & Error Handling

If entities empty under intent=market → status=not_found, helpful message

On API errors → return partial results; log and continue

Always return stable keys; missing fields become empty arrays/None

Memory Usage

Optionally stored in session as last_market by the orchestrator

Validation Hooks

Logs (entities requested) and (market result) to workflow_log

3.4 PortfolioAgent

Purpose
Answer portfolio questions: holdings, individual/aggregate performance, allocations, comparisons, best/worst, and weights using deterministic calculators and a shared price_cache.

Primary Responsibilities

Resolve latest prices once (price_cache) for all needed tickers

Run CalculatorTool computations

Return standardized, auditable numbers

Inputs

execution_plan (intent, entities, function_calls)

session (portfolio by client, symbol map, price_cache)

client_id

Outputs

{
  "status": "success",
  "client_id": "CLT-001",
  "entities": ["TSLA"],
  "results": [
    {"symbol": "TSLA", "quantity": 100, "current_price": 245.60, "gain": 5034, "pct_return": 25.2}
  ],
  "portfolio_summary": {
    "total_portfolio_value": 123456.78,
    "total_cost_basis": 98765.43,
    "overall_gain_loss": 24691.35,
    "overall_pct_return": 24.99,
    "sector_allocations": {"Technology": 45.1}
  },
  "message": "Filtered portfolio returned"
}


Core Logic

If function_calls present → execute in order, collate outputs

Else:

If entities present → filter holdings to those tickers

If none → full portfolio

Compute individual_returns and aggregate_portfolio

Fallbacks & Error Handling

If function-calling fails → default to holdings + returns

If no matching holdings → status=not_found, message

If a price cannot be resolved → skip that ticker, return partials

Guard division by zero and missing fields

Memory Usage

Optionally stored in session as last_portfolio by the orchestrator

Validation Hooks

Logs (plan subset) and (portfolio result) to workflow_log

3.5 ResponseGeneratorAgent

Purpose
Produce a concise, markdown response grounded in structured portfolio/market outputs and aligned with the user query and conversation history. For hybrid queries, reason about relationships (don’t stitch).

Primary Responsibilities

Use portfolio and/or market outputs based on availability

For hybrid: identify overlap (entities present in both) and connect the market signal to held positions

Respect formatting rules (bullets for lists, numbers with separators, no JSON/code blocks)

Inputs

user_query: str

execution_result: Dict (standardized bundle: {portfolio, market_response, intent, entities})

conversation_history: Optional[str]

Outputs

{
  "text": "- Microsoft (MSFT) is trading at ... Since you hold MSFT, this may be relevant to your ...",
  "data": {
    "portfolio": {...},
    "market_response": {...}
  }
}


Core Logic

If only portfolio → summarize holdings/returns/allocations

If only market → summarize price + headline/filings, note if not held

If both → reason: “Since you hold X, this market event may be relevant to your current +Y%.”

Markdown only; no tables/code/JSON

Fallbacks & Error Handling

If LLM fails → templated summaries (simple holdings list or price+headline)

Always keep response 1–3 sentences; never speculate

Memory Usage

Reads conversation_history for coherence

Memory updates happen after this step (orchestrator)

Validation Hooks

Logs final (prompted input) and (text output) to workflow_log

3.6 ValidatorAgent

Purpose
Act as a strict critic over the entire workflow. Determine if each step (classification, planning, portfolio/market outputs, response) is logically correct and grounded.

Primary Responsibilities

Evaluate workflow_log (inputs/outputs of each agent) against the original query

Detect misclassification, incorrect planning, empty/irrelevant downstream data, or ungrounded final text

Emit pass/fail and identify the failed agent with a reason

Inputs

original_query: str

workflow_log: {agents_executed[], steps[]}

Outputs

{
  "validation_result": "pass" | "fail",
  "failed_agent": "QueryClassificationAgent" | "PlannerAgent" | "PortfolioAgent" | "MarketAgent" | "ResponseGeneratorAgent" | null,
  "reason": "Short reason"
}


Core Logic

LLM runs a validator prompt with:

System overview (agent roles/responsibilities)

Exact workflow steps (inputs/outputs)

Required structure for pass/fail

Fallbacks & Error Handling

If validator returns invalid JSON → default to {"validation_result":"pass"}

Orchestrator may re-run from the failed node or return a conservative response

Memory Usage

None

Validation Hooks

This is the final gate; decision recorded with the whole log

3.7 MemoryManager (Session Management)

Purpose
Maintain per-client conversational memory and last results for contextual understanding and efficient follow-ups.

Primary Responsibilities

Build session payload for backend runs

Update memory after each turn (truncate to a safe length)

Clear memory on reset/logout

Inputs

session_state (from UI) and/or backend session

result (final outputs)

query: str

Outputs

Updated session dict:

chat_history (compact)

last_portfolio, last_market, debug_data

metadata (query count, timestamps)

Fallbacks & Error Handling

Initialize missing structures

Never crash on malformed session state

3.8 Tools & Deterministic Components

CalculatorTool

Deterministic numeric computations only:

individual_returns, aggregate_portfolio, compare_performance

get_best_performers, get_worst_performers, get_allocation, get_weight_in_portfolio

Uses injected price_cache to avoid duplicate API calls

LLM Client

Two unified entry points:

generate_text(prompt, parse_json: bool)

function_call(user_query, function_schema, prompt, entities, chat_history)

Sanitizes outputs; logs anomalies

3.9 Cross-Agent Fallback Matrix
Stage	Primary	Fallback	Final Behavior If All Fail
Classification	Rule-based + history + symbol map	LLM classifier	intent="unknown", entities=[], proceed conservatively
Planning (functions)	LLM tools (with ENTITIES)	Rule-based function mapping	Agents only; PortfolioAgent returns holdings+returns
Market fetch	Cache → API	Partial results with warnings	“No market data available” message
Portfolio compute	Calculator with price_cache	Partial results; skip bad tickers	“No matching holdings found”
Response generation	LLM (reasoned, markdown)	Templated summaries	Apology + minimal factual info
Validation	LLM validator over workflow_log	Default pass	Return current response; log warning

This section gives reviewers the full picture of how each agent works, what it expects, how it fails gracefully, and how it collaborates with others.

Production Go-To Plan

This plan describes how to take the prototype to a secure, observable, scalable production system. It covers deployment architecture, data flows, reliability, security/privacy, CI/CD, monitoring, and a phased rollout strategy.

1) Production Architecture
1.1 High-level topology
[ Client (Browser) ]
        |
        v  HTTPS
[ Streamlit / Web UI ]  <-- CDN (static assets)
        |
        v  HTTPS (REST/gRPC)
[ API Gateway ]
        |
        v
[ App Backend (FastAPI) ]  --(SDK)--> [ LLM Gateway ] -> Gemini / Ollama
        |        |  \
        |        |   \--(async tasks)--> [ Worker Pool / Celery/RQ ]
        |        |
        |        +--(SQL)--> [ Relational DB (PostgreSQL) ]
        |        +--(KV)-->  [ Redis (session/cache/rate limits) ]
        |        +--(Obj)--> [ Object Store (docs, logs, artifacts) ]
        |        +--(Vec)--> [ Vector DB (KB: filings/news embeddings) ]
        |
        +---> [ Market Data APIs (e.g., Finnhub) / SEC APIs ]

1.2 Components

Web UI: Streamlit (or Next.js) served behind a CDN; reads/writes via REST to backend.

API Gateway: TLS termination, routing, authn/z, rate limiting, request logs.

App Backend (FastAPI + LangGraph runtime):

Orchestrates agents, state machine execution, memory, and validation.

Synchronous path for short queries, offloads long-running fetches to workers.

LLM Gateway:

A thin service handling model routing (Gemini primary, Ollama local fallback), timeouts, and cost caps.

Centralizes prompt templates and tool schemas; emits structured logs of prompts and tool calls.

Worker Pool:

Async prefetch (news/filings), backfills, batch cache refresh, and periodic KB ingestion/embedding.

Data Stores:

PostgreSQL: user profiles, portfolios, session memory (persisted), audit logs, validator outcomes.

Redis: session cache, request dedup, rate-limits, short-TTL market snapshots.

Object store (S3/GCS): archived prompts/outputs, agent traces, artifacts for audits.

Vector DB (Qdrant/Pinecone/PGVector): embeddings for filings/news; RAG context for MarketAgent.

External APIs:

Market data (prices/headlines), SEC/EDGAR filings.

2) Scalability & Performance
2.1 Concurrency model

Sync path for typical Q&A (P50 < 2.5s with cache, < 5s on fresh fetch).

Async tasks for heavy or multi-entity market pulls; response can stream partials, or UI can poll.

2.2 Caching strategy

Redis:

Market price cache: TTL 30–120s (symbol-level).

News/filings cache: TTL 15–60 min (ticker-level); store top N items.

LLM tool-call cache keyed by (normalized query, entities, session context hash) for 1–5 min to dedupe retries.

Client-side: Cache portfolios per client_id for the session (ETag headers).

2.3 Backpressure & limits

API Gateway rate limits per user/session/IP.

LLM Gateway circuit breakers (max calls/min/user, global budget).

Worker queue depth and concurrency caps; exponential backoff on provider errors.

3) Reliability & Resilience
3.1 Timeouts and retries

App→LLM: timeout 8–12s; retry once with shorter context; fallback to deterministic rules.

App→Market APIs: timeout 2–3s; retry with backoff; partial results acceptable.

Validator: timeout 4–6s; if timeout/invalid JSON → default pass.

3.2 Degradation modes

If LLM classification fails → rule-based classification only.

If function calling fails → deterministic mapping.

If market APIs fail → return portfolio-only answer with message.

If vector DB unavailable → skip RAG and return headline-only market intel.

3.3 High availability

Run multiple replicas (HPA) for API and workers.

Multi-AZ Postgres with read replicas; Redis in clustered/sentinel mode.

Health checks: liveness/readiness probes; graceful shutdown.

3.4 Disaster recovery

RPO ≤ 15 min (Postgres: WAL archiving; Object store versioning).

RTO ≤ 60 min (infra-as-code to rehydrate; runbooks below).

4) Security & Privacy

AuthN/Z: OIDC (Auth0/Cognito) for UI; JWT tokens to backend; per-client scoping.

Tenant isolation: enforce client_id scoping at the API and DB layer; signed session IDs.

Data minimization: store only required memory; purge PII; configurable retention windows.

Secrets management: use cloud KMS/Secrets Manager; no secrets in code or env files in prod.

Network: private subnets for DB/Redis/Vector DB; VPC egress controls for external APIs.

Audit: immutable logs of agent steps and validator decisions stored to object store with retention policies.

Compliance: align with SOC2 practices; logging, access controls, key rotation, backups tested quarterly.

5) Observability
5.1 Metrics

Business: queries/min, completion rate, validation pass rate, hybrid usage rate.

Quality: classification accuracy (via shadow labels), function-call success rate, grounding violations (from validator).

Latency: P50/P95 per stage (classification, planning, market, portfolio, LLM).

Cost: tokens per request, API spend per symbol, cache hit rates.

Infra: CPU/mem per pod, DB/Redis ops, queue depths.

5.2 Logs and traces

Structured JSON logs per agent step (workflow_log id).

Distributed tracing (OpenTelemetry): span per LangGraph node.

Redaction of sensitive fields before export to log sink.

5.3 Alerts

SLO breaches (latency/error rate), LLM failure spikes, validator fail spikes.

Market API error bursts, cache miss surges, abnormal cost increases.

6) CI/CD & Testing
6.1 CI

PR checks:

Unit tests (calculators, parsing, planners).

Linting/formatting, type checks (mypy/pyright).

Prompt lint: JSON schema validation for tool specs.

Security scans (SAST/Dependency).

6.2 CD

Blue/green or canary deployments (small traffic slice first).

Feature flags for new agents/prompts.

Automatic rollback on SLO breach or error spike.

6.3 Testing strategy

Unit: calculators, entity normalizer, rule-based classifier, portfolio filters.

Contract: I/O schemas between agents; pydantic validation in integration boundaries.

Integration: synthetic market responses; SEC mock endpoints.

Load: soak tests with replayed queries; ensure P95 within targets.

Prompt regression: golden test sets for LLM outputs (classification, planner, response).

7) Data Management

Schemas (Postgres):

clients, portfolios, sessions, chat_history, agent_runs, validator_outcomes.

Retention:

Session memory: 30–90 days (configurable).

Validator logs: 90–365 days for audits.

KB Ingestion:

Workers ingest filings/news hourly; chunk and embed; attach metadata (ticker, source, date).

Deduplicate content by hash; re-embed on significant model upgrades only.

8) Production Runbooks

Incident: LLM provider outage

Switch route to Ollama via LLM Gateway flag.

Disable function calling; enable deterministic planner fallback.

Incident: Market API rate limit

Increase cache TTLs temporarily; enable exponential backoff; switch to secondary provider if configured.

Incident: DB overload

Reduce per-request memory writes; throttle debug logs; use read replica for analytics.

Hotfix process

Feature flag toggles; canary rollout; roll back via CI/CD.

9) SLOs & Capacity Planning

Availability: 99.9% for API.

Latency:

P50 end-to-end: ≤ 2.5s cached, ≤ 5s uncached.

P95 end-to-end: ≤ 6s.

Error budget: ≤ 1% failed requests excluding user input errors.

Initial capacity:

API x 3 replicas (HPA 3–10), Workers x 2 (HPA 2–8).

Redis 3-node cluster; Postgres 2 vCPU/8GB with read replica.

10) Phased Rollout

Phase 0 – Hardening

Add API Gateway, auth, structured logs, tracing.

Introduce validator gating and fallbacks as feature flags.

Phase 1 – Limited Beta

Enable multi-tenant sessions; enforce client scoping.

Monitor SLOs; tune caches and timeouts; fix top validation failures.

Phase 2 – General Availability

Canary rollout to all clients.

Enable async prefetch and KB retrieval at scale.

Add dashboards for cost and quality metrics.

Phase 3 – Continuous Improvement

Clarification loop for low-confidence classification.

Advanced event–impact scoring tying market events to portfolio risk/exposure.

11) Cost Controls

Enforce per-user/month token budgets via LLM Gateway.

Aggressive caching of market data.

Batch embeddings and limit KB size (top tickers and top events first).

Nightly cost reports and anomaly alerts.

12) Security Review Checklist

Tenant isolation tests (no cross-client leakage).

Secrets rotation validation.

Transport security (TLS 1.2+), HSTS.

Least-privilege IAM on all services.

Log redaction and PII scrubbing verified.