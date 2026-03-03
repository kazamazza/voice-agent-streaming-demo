Voice Agent Streaming Demo

A streaming voice-agent backend demonstrating:
	•	Hexagonal architecture
	•	Chain of Responsibility routing
	•	Hybrid intent detection (keyword → ML intent model → LLM)
	•   Lightweight NLP training pipeline (dataset → model → inference)
	•	Config-driven scoring and messaging
	•	Redis stream + worker processing
	•	End-to-end trace propagation
	•	Unit-tested routing pipeline

This project simulates a real-time AI-assisted call center backend.

⸻

Overview

This system ingests incremental transcript chunks (e.g. from streaming speech-to-text), processes them asynchronously, and produces:
	•	Routing decisions (SUPPORT / BILLING / SALES / HUMAN_AGENT)
	•	Agent suggestions
	•	Real-time call scoring
	•	Clarification prompts when intent is ambiguous

It is designed to be:
	•	Deterministic-first (low latency)
	•	Safe under failure
	•	Horizontally scalable
	•	Easy to extend with semantic or LLM intelligence

⸻

Architecture

Hexagonal Architecture (Ports & Adapters)

The application follows a hexagonal (clean architecture) structure:

                ┌─────────────────────────┐
                │     External World      │
                │  (STT, LLM, Redis, UI)  │
                └────────────┬────────────┘
                             │
               ┌─────────────▼─────────────┐
               │        Adapters           │
               │  - Redis broker           │
               │  - LLM provider           │
               │  - ML Intent Model        │
			   │  - Optional LLM Provider  │       │
               └─────────────┬─────────────┘
                             │
               ┌─────────────▼─────────────┐
               │       Application         │
               │  - RoutingEngine          │
               │  - SuggestionEngine       │
               │  - ScoringEngine          │
               └─────────────┬─────────────┘
                             │
               ┌─────────────▼─────────────┐
               │          Domain           │
               │  - RouteDecision          │
               │  - Suggestion             │
               │  - Score                  │
               │  - CallSession            │
               └───────────────────────────┘

The domain is pure and framework-agnostic.
Adapters can be replaced without affecting business logic.

⸻

Routing Pipeline

Routing uses a Chain of Responsibility pattern.

Resolvers execute sequentially and stop on first confident match.

Pipeline:
	1. Keyword Resolver (deterministic)
	2. ML Intent Resolver (trained TF-IDF + LogisticRegression model)
	3. LLM Resolver (fallback)
	4. Clarification Resolver
	5.	Clarification Resolver (agent-assist when still UNKNOWN)

Transcript
   ↓
Keyword match?
   ↓ no
Semantic similarity?
   ↓ no
LLM classify?
   ↓ no
Clarification suggestion

Design goals:
	•	Low latency first
	•	Deterministic before probabilistic
	•	Never crash worker
	•	Avoid suggestion overwrite
	•	Avoid LLM spam below threshold

⸻

Config-Driven Design

All behavior is externalized via YAML config:
	•	Routing thresholds
	•	Intent keywords
	•	Semantic toggle
	•	Scoring weights
	•	Taxonomy definitions
	•	Agent-facing messages

Example:

routing:
  min_chunks_for_clarify: 2
  min_chunks_for_llm_fallback: 3

This allows:
	•	Runtime tuning without code changes
	•	A/B testing routing behavior
	•	Safer production adjustments

⸻

Intent Model

The system includes a lightweight trained intent model used by the SemanticRouteResolver.

Pipeline:

Synthetic Call Logs
      ↓
Dataset Builder (JSONL → Parquet)
      ↓
Intent Model Training
      ↓
TF-IDF Vectorizer + LogisticRegression
      ↓
Serialized Model (joblib)
      ↓
Runtime Semantic Intent Resolver

Example training command:

make train

Example inference demo:

make nlp-demo

The model provides fast probabilistic intent ranking used by the routing engine.

Example output:

TEXT: money was taken from my card two times
  BILLING       0.68
  SUPPORT       0.10
  HUMAN_AGENT   0.10

Design goals:
• Sub-millisecond inference
• Cheap to retrain
• Deterministic routing boost
• No external ML dependencies

⸻

Real-Time Processing Model

POST /calls/{call_id}/chunks
        ↓
Redis Stream
        ↓
Background Worker
   - RoutingEngine
   - SuggestionEngine
   - ScoringEngine
        ↓
Session State (Redis)
        ↓
GET /agent_view

The worker is stateless and horizontally scalable.

Trace IDs propagate end-to-end.

⸻

How To Run

1. Start Redis

docker run -p 6379:6379 redis

2. Start API

uvicorn voice_demo.main:app --reload

3. Start Worker

python -m voice_demo.worker

4. Send Test Transcript

curl -X POST http://localhost:8000/calls/demo/chunks \
  -H "Content-Type: application/json" \
  -d '{"seq":0,"text":"You charged my card twice"}'

5. View Agent State

curl http://localhost:8000/calls/demo/agent_view


⸻

Production Deployment Model

In production this system would sit inside a larger voice stack:

Twilio Media Stream
        ↓
Speech-to-Text (Deepgram / AWS Transcribe)
        ↓
FastAPI Ingestion Service (Docker)
        ↓
Redis Stream
        ↓
Routing Worker (Docker)
        ↓
Redis Session Store
        ↓
Agent Dashboard (WebSocket)

Deployment example:
	•	Docker containers
	•	AWS ECS Fargate or Kubernetes
	•	Redis via ElastiCache
	•	OpenTelemetry tracing
	•	Prometheus metrics
	•	CI/CD via GitHub Actions
	•	Secrets via Parameter Store or Vault

The system is designed to scale horizontally:
	•	API layer stateless
	•	Worker horizontally scalable
	•	Redis stream supports consumer groups

⸻

Design Decisions

Why deterministic-first?
	•	LLM calls are expensive
	•	Routing must be low latency
	•	70–80% of intents are obvious via keywords

Why Chain of Responsibility?
	•	Clean separation of routing logic
	•	Easy to add new resolvers
	•	Clear fallback ordering
	•	Testable in isolation

Why central UTC helper?
	•	Avoid datetime.utcnow deprecation
	•	Timezone-safe timestamps
	•	Easier test mocking

⸻

Future Improvements
	•	Add embedding-based semantic model (OpenAI / local transformers)
	• Upgrade intent model to transformer classifier
	• Online learning from real transcripts
	•	Add OpenTelemetry tracing
	•	Add rate limiting & auth
	•	Implement WebSocket push instead of polling
	•	Dead-letter queue handling
	•	CI/CD pipeline with container builds
	•	Observability dashboards

⸻

Current Status
	•	Routing chain implemented
	•	Semantic stage toggle
	•	LLM fallback guard
	•	Clarification safety
	•	Config-driven scoring
	•	Trace ID propagation
	•	10 unit tests passing
	•	Production-ready architectural foundation
	• Trained intent model integrated
	• Config-driven semantic provider (stub | model)
	• Dataset + training pipeline