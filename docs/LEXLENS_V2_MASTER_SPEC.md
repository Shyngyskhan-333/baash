# LexLens V2 Master Spec

## Purpose And Authority

This document is the repository source of truth for LexLens V2 product and architecture decisions.
Future implementation, UX, AI, security, and roadmap work must conform to this spec unless a later architecture decision explicitly changes it.

## Final Product Definition

LexLens V2 is an evidence-first legal change-control and legislative intelligence platform for Kazakhstan law.
It is one platform with one shared evidence core powering three product surfaces:

- Government Draft Law Review
- Enterprise Regulatory Monitoring
- Legal Research Copilot

LexLens is not a generic legal chatbot, a search-only product, or a decorative legal graph.

## Production Principles

- Every legal claim must be traceable to citations and evidence packets.
- AI suggests, ranks, summarizes, and explains; humans validate legal findings.
- Source snapshots, legal document versions, citations, finalized evidence packets, model runs, and audit logs are immutable.
- Legal document versions are first-class entities.
- Candidate issues and validated issues must never be merged into one status.
- Deterministic systems own source ingestion, text extraction, versioning, citations, dates, permissions, and audit logs.
- AI-generated outputs must eventually link to `ModelRun` and supporting citations.

## Product Surfaces

### Government Draft Law Review

Government users upload or select draft laws, amendments, and legal change packages.
LexLens compares drafts against current and historical legislation, generates candidate conflicts or outdated references, assigns review tasks, and produces evidence packets.

### Enterprise Regulatory Monitoring

Enterprise users define organization profiles, regulated sectors, watched legal sources, and internal obligation mappings.
LexLens monitors legal changes, proposes obligation impacts, creates regulatory alerts, and supports compliance review tasks.

### Legal Research Copilot

Legal professionals ask questions against Kazakhstan legal documents.
LexLens answers only from retrieved citations or explicitly states that evidence is insufficient.

## Shared Evidence Core

The evidence core is the canonical source of truth. Search indexes, graph views, AI summaries, alerts, and reports are derived from it.

Layers:

- Source truth: `Source`, `SourceSnapshot`, `LegalDocument`, `LegalDocumentVersion`
- Legal structure: `Article`, `Clause`, `Citation`, `LegalReference`, `Amendment`
- Computational derivatives: `SemanticChunk`, `SearchIndexRecord`, `ModelRun`
- Candidate intelligence: `ConflictCandidate`, `DuplicateCandidate`, `OutdatedNormCandidate`
- Human-validated intelligence: `ReviewTask`, `ValidatedIssue`, `EvidencePacket`
- Product workflows: `DraftLawReview`, `OrganizationProfile`, `Obligation`, `RegulatoryAlert`
- Governance: `AuditLog`, `EvaluationCase`, `UserFeedback`

## Canonical Domain Model

Minimum production foundation entities:

- `Source`: authoritative origin such as Adilet or an approved internal upload channel.
- `SourceSnapshot`: immutable captured source content with URL, fetch metadata, raw storage URI, and SHA-256 hash.
- `LegalDocument`: stable legal act identity independent from versions.
- `LegalDocumentVersion`: immutable text version tied to a source snapshot.
- `Article`: article-level legal structure within one document version.
- `Clause`: precise clause-level legal structure within one article.
- `Citation`: exact pointer to document version text, article, clause, chunk, quote, and offsets.
- `SemanticChunk`: retrieval unit derived from canonical legal text and linked to citation.
- `ModelRun`: immutable record of AI/NLP execution metadata.
- `EvidencePacket`: exportable bundle of citations, snapshots, review records, model runs, and hash.
- `AuditLog`: append-only record of sensitive actions and evidence changes.

Later entities:

- `LegalReference`, `Amendment`, `SearchIndexRecord`, `ConflictCandidate`, `DuplicateCandidate`, `OutdatedNormCandidate`, `ValidatedIssue`, `Obligation`, `Sector`, `OrganizationProfile`, `RegulatoryAlert`, `DraftLawReview`, `ReviewTask`, `UserFeedback`, `EvaluationCase`.

## Immutability Rules

Immutable:

- `SourceSnapshot`
- `LegalDocumentVersion`
- `Article`
- `Clause`
- `Citation`
- `SemanticChunk`
- completed `ModelRun`
- finalized `EvidencePacket`
- `AuditLog`

Mutable only with audit:

- source registry metadata
- organization profiles
- candidate statuses
- review tasks
- obligation status
- regulatory alert status

## Versioning Rules

- Legal text changes create new `LegalDocumentVersion` records.
- Parser, chunking, embedding, prompt, and index changes must have explicit versions.
- Evidence packets are regenerated as new immutable packets, not edited after finalization.
- AI/provider changes must be evaluated before broader rollout.
- A parsed document may create a `LegalDocumentVersion` only when citable legal text is available and the parsed record belongs to the matching immutable `SourceSnapshot`.

## Citation Rules

- No legal answer, candidate issue, evidence packet, or report should make a serious legal claim without citations.
- Citations must include document version, legal location, quote, and source lineage.
- Chunks are retrieval helpers, not legal authority.
- Source parsing may produce normalized `Article` and `Clause` records, but citation creation remains a separate deterministic step.
- Metadata-only parses must not be treated as citable legal text.
- Parsed legal structures may be converted into canonical `Article`, `Clause`, and `Citation` objects only when legal text is available and tied to a `LegalDocumentVersion`.
- Semantic chunks are deterministic derivatives of citations; chunk generation must not create legal authority or bypass citation requirements.

## Evidence Packet Rules

- Evidence packets require at least one citation.
- Finalized packets must include a stable hash.
- Packets must show candidate vs validated status.
- Packets may include model run IDs, reviewer decisions, source snapshot IDs, and audit metadata.

## Human Review Workflow

Candidate states:

- `candidate`
- `under_review`
- `validated`
- `rejected`
- `needs_evidence`
- `superseded`

Only human-reviewed findings may become validated legal issues.

## AI Usage Boundaries

Allowed:

- query expansion
- summarization
- candidate explanation
- reranking
- obligation drafts
- draft memo generation
- citation-grounded copilot answers

Prohibited:

- final legal conclusions without review
- invented citations
- mutation of source truth
- bypassing permissions
- marking candidates as validated

## Security And RBAC Model

LexLens must support organization-level tenancy and roles:

- platform admin
- organization admin
- legal reviewer
- compliance officer
- researcher
- viewer
- external auditor

Production mode must not expose unauthenticated settings, secrets, evidence packets, or review actions.

## Audit Logging Model

Audit logs are required for:

- source changes
- ingestion runs
- AI settings changes
- secret updates
- candidate review decisions
- evidence packet generation and export
- permission changes
- organization profile changes

## Deployment Model

LexLens must support:

- local/offline deployment for sensitive environments
- cloud/institution deployment for managed environments

Both deployment modes use the same domain model. Do not adopt microservices, Kubernetes, Redis, Celery, PostgreSQL, Qdrant, or any dedicated vector database until measured requirements justify them.

## Testing And Evaluation Model

Required test categories:

- evidence model unit tests
- citation accuracy tests
- source snapshot hash tests
- parser fixture tests
- mocked API smoke tests
- retrieval recall tests
- known contradiction and false-positive cases
- AI grounding and hallucination tests
- RBAC and tenant isolation tests

Default tests must not require live Adilet, live LLMs, or prebuilt FAISS files.

## Current Repo Migration Plan

1. Stabilize current product.
2. Introduce evidence core interfaces and models.
3. Add canonical legal data model.
4. Move search, diff, audit, graph, and chat onto evidence-backed services.
5. Build Government Draft Law Review.
6. Build Enterprise Regulatory Monitoring.
7. Build Legal Research Copilot.
8. Harden security, audit, deployment, and evaluation.

## Current Foundation Modules

- `src/evidence/models.py`: immutable production foundation entities for source provenance, legal document versions, citations, semantic chunks, evidence packets, model runs, and audit logs.
- `src/evidence/legacy_adapter.py`: compatibility adapter that maps legacy `data/parsed/*.json` documents into evidence core objects without changing the legacy storage format. It records `parse_quality` and `legal_text_available`; `metadata_only` imports are provenance/preview records only and must not generate citations or chunks.
- `src/evidence/packet_service.py`: storage-free evidence packet builder that requires citations, de-duplicates evidence references, computes stable packet hashes, and exports JSON-safe bundles.
- `src/evidence/ai_grounding.py`: storage-free grounding service that links AI answers to cited evidence packets, immutable `ModelRun` metadata, and source snapshot IDs when supplied by search results.
- `src/evidence/analyze_grounding.py`: analyze-route grounding helper that turns legacy document text into citation-backed candidate metadata.
- `src/evidence/review_workflow.py`: storage-free review workflow state machine for candidate, under-review, validated, rejected, needs-evidence, and superseded states with audit log emission.
- `src/search/service.py`: citation-aware search boundary around the current `LegalRetriever`; it preserves legacy result fields and adds internal `citation_id`, `citation_label`, `citation_quote`, and `document_version_id` fields.
- `api/services/nlp_service.py`: existing search behavior is preserved while delegating search enrichment to `SearchService`.
- `api/routers/analyze.py`: existing summary behavior is preserved while adding optional `grounding` metadata marked as `candidate` and `not_human_validated`.
- `src/draft_review/`: domain-only Government Draft Law Review foundation that references draft source snapshots, target legal document versions, candidate issues, evidence packets, and review tasks without exposing new public APIs.
- `src/monitoring/`: domain-only Enterprise Regulatory Monitoring foundation for organization profiles, watched sectors/documents, obligation candidates, regulatory alerts, evidence packets, and review tasks without automatic validated obligations.
- `src/copilot/`: domain-only Legal Research Copilot answer contract with answered/refused states, uncertainty labels, citation requirements, evidence packet linkage, and model run linkage without changing the current chat API.
- `api/routers/settings.py`: production-mode guardrail blocks unauthenticated AI settings writes when `LEXLENS_ENV`, `APP_ENV`, or `ENV` is `production`/`prod`; development/local behavior remains unchanged until full RBAC is implemented.
- `src/security/rbac.py`: lightweight RBAC foundation defining platform roles, protected actions, and production-mode permission checks. It intentionally does not implement login, JWT, persistence, or tenant middleware yet.
- `src/audit/events.py`: audit event helpers for sensitive operations. AI settings changes produce sanitized before/after hashes that redact secret values before hashing.
- `src/audit/sink.py`: append-only local JSONL audit sink for immutable `AuditLog` records. This is the local/offline foundation; institutional persistence and querying remain postponed.
- `src/audit/reader.py`: local audit read model for JSONL records with malformed-line tolerance, optional organization filtering, and RBAC-protected read service for future admin/auditor APIs.
- `src/ingestion/snapshot.py`: source-ingestion boundary for turning fetched raw content into immutable `SourceSnapshot` records before parsing/chunking. It can optionally persist raw content and keeps `parser_version` unset at fetch time.
- `src/ingestion/parser.py`: pure parser boundary that consumes a `SourceSnapshot` and matching raw content, verifies the snapshot hash, and returns parsed metadata with explicit `parse_quality` and parser version without creating citations or chunks.
- `src/ingestion/document_builder.py`: pure builder for `LegalDocument` and `LegalDocumentVersion` from citable parsed legal text tied to a matching `SourceSnapshot`.
- `src/ingestion/citation_builder.py`: pure builder for canonical `Article`, `Clause`, and `Citation` objects from parsed legal structure.
- `src/ingestion/chunk_builder.py`: pure builder for deterministic `SemanticChunk` records from canonical citations.
- `src/ingestion/service.py`: composition boundary that turns fetched content into a citable evidence bundle without persistence, API exposure, or search indexing.
- `src/evidence/memory_repository.py`: in-memory evidence repository for tests and early wiring. It is not the durable production storage layer and must not be treated as a database decision.
- `src/search/canonical_retrieval.py`: deterministic in-memory retrieval adapter over canonical `SemanticChunk` records. It is for tests and early evidence-core wiring and does not replace the legacy retriever in production routes yet.
- `src/search/result_formatter.py`: canonical search result formatter that resolves chunks to citations, document versions, and document metadata before producing evidence-packet-compatible result dictionaries.
- `src/search/canonical_service.py`: canonical search composition service that combines canonical retrieval and result formatting while preserving the same top-level result shape used by downstream evidence packet code.
- `src/search/canonical_grounding.py`: canonical grounding service that feeds canonical search results into `AIGroundingService`, creating `ModelRun` and evidence packet records from cited evidence.
- `src/evidence/evaluation.py`: immutable evaluation case/result models for retrieval recall, citation accuracy, answer grounding, hallucination, and contradiction-candidate checks. These are domain contracts only; evaluator runtime is a later slice.
- `src/evidence/retrieval_evaluation.py`: deterministic retrieval recall evaluator that compares canonical search citation IDs with `EvaluationCase.expected_citation_ids`. It does not invoke LLMs or external services.
- `src/evidence/citation_accuracy_evaluation.py`: deterministic citation accuracy evaluator that checks formatted result citation quotes and document versions against expected evaluation data. It does not judge legal correctness.
- `src/evidence/grounding_evaluation.py`: deterministic grounding evaluator that checks AI output traceability to expected citations, `ModelRun`, and evidence packet links. It does not evaluate legal correctness or answer quality.
- `src/evidence/evaluation_suite.py`: explicit local suite runner for retrieval, citation accuracy, and grounding traceability cases. It does not persist results, call external services, or create hidden evaluation cases.
- `src/evidence/evaluation_fixture_loader.py`: strict local JSON loader for version-controlled `EvaluationCase` fixtures. It does not choose storage infrastructure or run suites automatically.
- `src/evidence/fixture_evaluation.py`: local composition service that loads fixture files and runs them through the deterministic evaluation suite when explicit search and grounding dependencies are supplied. It is not a CI gate.
- `tests/fixtures/evaluation/golden_cases.json`: synthetic local golden-case fixture corpus for deterministic loader and evaluator wiring. It is not a legal correctness benchmark.

## Production Implementation Roadmap

Initial foundation:

- evidence models
- source provenance
- document versions
- citations
- evidence packets
- audit logs
- model runs
- tests

Product surfaces start only after the evidence core is usable and tested.

## What Must Not Be Built Yet

- broad chatbot positioning
- institutional Chrome extension rollout
- automatic validated obligations
- microservices or Kubernetes
- dedicated vector database migration
- regional expansion
- decorative graph-first workflows
- risk scores without validated methodology

## Non-Negotiables

- No legal conclusion without citations.
- No validated issue without human review.
- No mutation of source snapshots or legal document versions.
- No AI output treated as source truth.
- No cross-organization data leakage.
- No secret exposure.
- No unsupported evidence packet export.
