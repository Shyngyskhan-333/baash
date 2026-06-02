# LexLens V2 Implementation Backlog

## Purpose

This backlog tracks production foundation work for LexLens V2. It is not an MVP backlog.
The first implementation phase prioritizes the shared evidence core, not UI polish or product-surface expansion.

## Priority Levels

- `P0 Foundation`: required before reliable V2 implementation can proceed.
- `P1 Production Core`: evidence, citations, review, packets, audit, model-run foundations.
- `P2 Product Surface`: Draft Review, Monitoring, Copilot workflows.
- `P3 Hardening`: security, observability, deployment, evaluation depth.
- `P4 Scale`: infrastructure upgrades justified by measured need.

## Epic Backlog

### Evidence Core

#### EC-001: Define evidence core models

- Priority: P0 Foundation
- Goal: Add immutable domain models for source provenance, document versions, citations, evidence packets, model runs, and audit logs.
- Value: Gives all future legal claims a traceable structure.
- Affected modules: `src/evidence/*`, `tests/*`
- Steps: create evidence package; implement dataclasses; add validation and hash helpers; export public symbols.
- Acceptance: models can be instantiated, validate required fields, and reject invalid hashes/offsets.
- Tests: unit tests for immutability, hashes, citations, packets, audit logs.
- Risk: low
- Dependencies: none
- Rollback: remove additive package and tests.

#### EC-002: Add legacy parsed JSON adapter

- Priority: P0 Foundation
- Goal: Read current `data/parsed/*.json` through evidence interfaces.
- Value: Allows migration without breaking current storage.
- Affected modules: `src/evidence/*`, `data/parsed`
- Steps: map doc JSON to document, version, articles, citations, chunks; add fixture tests.
- Acceptance: one fixture document imports into canonical evidence objects.
- Tests: fixture import test.
- Risk: medium
- Dependencies: EC-001
- Rollback: keep adapter unused behind feature flag.

#### EC-003: Add local in-memory evidence repository

- Priority: P0 Foundation
- Goal: Store and query canonical evidence objects in tests and early service wiring without selecting durable database infrastructure.
- Value: Allows ingestion, citation, packet, and future workflow services to share one evidence boundary during migration.
- Affected modules: `src/evidence/*`, `tests/*`
- Steps: implement in-memory repository methods for snapshots, documents, versions, articles, clauses, citations, and chunks; add conflict detection for duplicate IDs with different content.
- Acceptance: ingestion bundles can be saved and queried by canonical IDs; saving the same bundle is idempotent; conflicting duplicate IDs are rejected.
- Tests: repository save/query, idempotency, and conflict tests.
- Risk: low
- Dependencies: EC-001, ING-001
- Rollback: remove repository module and tests; existing services remain pure.

### Legal Source Ingestion

#### ING-001: Split source fetch, snapshot, parse, and chunk responsibilities

- Priority: P1 Production Core
- Goal: Stop treating scraper output as canonical truth.
- Value: Makes source provenance auditable.
- Affected modules: `src/scraper/*`, `src/evidence/*`
- Steps: isolate fetch function; write source snapshot metadata; keep parser pure; keep chunking separate.
- Acceptance: fetching can produce immutable snapshot before parsing; parser can return metadata-only results or normalized article/clause structure without creating chunks or citations; citable ingestion can compose document versioning, citation generation, and chunking into one evidence bundle without persistence or indexing.
- Tests: mocked HTTP, snapshot hash, raw hash verification, metadata-only parsing, structured article/clause parsing, citation-derived chunking, and ingestion orchestration tests.
- Risk: medium
- Dependencies: EC-001
- Rollback: keep old scraper path active.

### Legal Versioning

#### VER-001: Add canonical document version import

- Priority: P1 Production Core
- Goal: Represent current and archived acts as versions.
- Value: Prevents current/historical text confusion.
- Affected modules: `src/evidence/*`, `api/routers/index.py`
- Steps: define version mapping; preserve archive IDs; validate effective date ordering where known.
- Acceptance: citable parsed source documents map to stable `LegalDocument` and `LegalDocumentVersion` records tied to the matching `SourceSnapshot`; metadata-only parses cannot create legal text versions.
- Tests: version import, stable ID, metadata-only rejection, and snapshot mismatch tests.
- Risk: medium
- Dependencies: EC-001, EC-002
- Rollback: keep legacy preview/document endpoints.

### Citation System

#### CIT-001: Generate citations from imported legal structure

- Priority: P0 Foundation
- Goal: Create exact citation objects from articles/chunks.
- Value: Makes search and AI grounding possible.
- Affected modules: `src/evidence/*`, `src/ingestion/*`
- Steps: derive citation labels; preserve quote text; link citation to document version, article, and clause.
- Acceptance: each citable parsed clause can become a canonical citation; metadata-only parses are rejected as non-citable.
- Tests: citation generation, stable ID, metadata-only rejection, and validation tests.
- Risk: medium
- Dependencies: EC-001
- Rollback: keep citations internal only.

### Evidence Packets

#### PKT-001: Implement JSON evidence packet builder

- Priority: P1 Production Core
- Goal: Bundle citations, snapshots, model runs, and review metadata.
- Value: Enables defensible exports later.
- Affected modules: `src/evidence/*`
- Steps: define packet schema; compute packet hash; require citations.
- Acceptance: packet cannot be created without citations; packet hash is stable.
- Tests: packet hash and validation tests.
- Risk: low
- Dependencies: CIT-001
- Rollback: do not expose builder through API.

### Human Review Workflow

#### REV-001: Define review task state model

- Priority: P1 Production Core
- Goal: Separate candidate issues from validated issues.
- Value: Prevents AI/NLI output from becoming legal authority.
- Affected modules: `src/evidence/*` or future `src/review/*`
- Steps: define review states, reviewer decision values, note requirements.
- Acceptance: candidate status transitions are explicit and testable.
- Tests: state transition tests.
- Risk: medium
- Dependencies: EC-001
- Rollback: keep model unused until APIs exist.

### Search and Retrieval

#### SRCH-001: Wrap current retriever behind SearchService

- Priority: P0 Foundation
- Goal: Keep FAISS/BM25 while stabilizing the interface.
- Value: Enables citation-backed search migration without route breakage.
- Affected modules: `src/retrieval/retriever.py`, new `src/search/*`
- Steps: create service interface; adapt `LegalRetriever.search_hybrid`; keep existing route response shape.
- Acceptance: existing search still works; internal result can include citation ID when available.
- Tests: mocked retriever service tests.
- Risk: medium
- Dependencies: CIT-001
- Rollback: route continues using `LegalRetriever` directly.

#### SRCH-002: Add canonical in-memory retrieval adapter

- Priority: P1 Production Core
- Goal: Search canonical `SemanticChunk` records through the evidence-core `RetrievalIndex` protocol without changing production routes.
- Value: Enables evidence-core retrieval tests and future migration away from legacy-only search results.
- Affected modules: `src/search/*`, `src/evidence/*`, `tests/*`
- Steps: implement deterministic token matching over canonical chunks; support top-k and document filtering; keep legacy `SearchService` unchanged.
- Acceptance: canonical chunks can be retrieved by query and filtered by document ID; empty queries are rejected; result chunks retain citation IDs.
- Tests: canonical retrieval matching, ordering, filtering, and validation tests.
- Risk: low
- Dependencies: EC-003, ING-001, CIT-001
- Rollback: remove adapter and tests; legacy search remains active.

#### SRCH-003: Format canonical retrieval results with citations

- Priority: P1 Production Core
- Goal: Convert canonical retrieval chunks into evidence-packet-compatible search result dictionaries.
- Value: Allows canonical search results to feed existing grounding and evidence packet services without losing provenance.
- Affected modules: `src/search/*`, `src/evidence/*`, `tests/*`
- Steps: resolve chunk citation, document version, document, article metadata; emit citation-aware result fields; fail closed when provenance is missing.
- Acceptance: formatted results include document ID, version ID, snapshot ID, article/clause IDs, chunk ID, citation ID, citation label, quote, and text.
- Tests: formatter field mapping, ordering preservation, and missing-citation rejection tests.
- Risk: low
- Dependencies: EC-003, SRCH-002
- Rollback: remove formatter and tests; legacy formatter remains unchanged.

#### SRCH-004: Compose canonical retrieval and formatting

- Priority: P1 Production Core
- Goal: Provide a canonical search service that returns evidence-packet-compatible results from evidence-core chunks.
- Value: Enables future route and copilot migration without coupling product code to retrieval internals.
- Affected modules: `src/search/*`, `tests/*`
- Steps: compose canonical retrieval adapter and result formatter; preserve top-level `{"results": [...]}` shape; keep legacy routes unchanged.
- Acceptance: canonical search returns formatted cited results, supports document filtering, and can feed `EvidencePacketService`.
- Tests: canonical search composition, filtering, no-match, and evidence packet compatibility tests.
- Risk: low
- Dependencies: SRCH-002, SRCH-003, PKT-001
- Rollback: remove canonical service and tests; legacy `SearchService` remains active.

### Legal Graph

#### GRAPH-001: Define graph edge projection contract

- Priority: P1 Production Core
- Goal: Make graph a projection from canonical evidence.
- Value: Prevents graph pickle from becoming source truth.
- Affected modules: `src/graph/*`, `src/evidence/*`
- Steps: define edge source types; include citation/candidate references.
- Acceptance: graph edge can point back to evidence.
- Tests: projection tests.
- Risk: medium
- Dependencies: EC-001, CIT-001
- Rollback: keep current graph path.

### Conflict Candidate Detection

#### CCD-001: Define candidate issue models

- Priority: P1 Production Core
- Goal: Store conflict/duplicate/outdated outputs as candidates.
- Value: Supports human validation.
- Affected modules: `src/reasoning/*`, `src/evidence/*`
- Steps: define candidate fields; include citations, signals, status, model run ID.
- Acceptance: detector output can be represented without claiming validation.
- Tests: candidate model tests.
- Risk: medium
- Dependencies: CIT-001, AI-001
- Rollback: keep current audit response only.

### Government Draft Review

#### GOV-001: Define draft review domain model

- Priority: P2 Product Surface
- Goal: Prepare draft review workflow after evidence core.
- Value: First institutional product surface.
- Affected modules: future `src/draft_review/*`
- Steps: define draft snapshot, scope, candidate links, evidence packet links.
- Acceptance: draft review can reference evidence core objects.
- Tests: model tests.
- Risk: medium
- Dependencies: EC-001, REV-001, PKT-001
- Rollback: no API exposure until ready.

### Enterprise Regulatory Monitoring

#### ENT-001: Define organization profile and obligation draft models

- Priority: P2 Product Surface
- Goal: Prepare enterprise monitoring without automatic legal truth.
- Value: Enables organization-specific alerting later.
- Affected modules: future `src/monitoring/*`
- Steps: define organization profile, sector, watched documents, obligation draft.
- Acceptance: alerts can be traced to citations and org profile.
- Tests: model tests.
- Risk: medium
- Dependencies: CIT-001, REV-001
- Rollback: keep models unused.

### Legal Research Copilot

#### COP-001: Define citation-grounded answer contract

- Priority: P2 Product Surface
- Goal: Prevent ungrounded copilot answers.
- Value: Makes research assistant legally safer.
- Affected modules: `api/routers/chat.py`, future `src/copilot/*`
- Steps: define answer parts, citations, uncertainty labels, refusal state.
- Acceptance: answer contract supports no-citation refusal.
- Tests: grounding tests with mocked model.
- Risk: medium
- Dependencies: CIT-001, AI-001
- Rollback: keep current chat route behavior.

### Security and RBAC

#### SEC-001: Add production mode guardrails

- Priority: P0 Foundation
- Goal: Prevent insecure production settings paths.
- Value: Reduces accidental institutional exposure.
- Affected modules: `api/main.py`, `api/routers/settings.py`, config module.
- Steps: define production mode flag; restrict unsafe settings operations; document local mode.
- Acceptance: production mode rejects unauthenticated AI settings writes.
- Tests: settings route tests.
- Risk: medium
- Dependencies: none
- Rollback: default remains development mode.

### Audit Logs

#### AUD-001: Define audit log model

- Priority: P1 Production Core
- Goal: Create append-only audit record structure.
- Value: Required for legal and institutional accountability.
- Affected modules: `src/evidence/*`
- Steps: add actor, action, target, hashes, timestamp, reason fields.
- Acceptance: audit log validates required fields and hashes.
- Tests: audit model tests.
- Risk: low
- Dependencies: EC-001
- Rollback: keep model unused.

### AI Grounding and Evaluation

#### AI-001: Define model run model

- Priority: P1 Production Core
- Goal: Track AI/NLP execution metadata.
- Value: Makes AI outputs auditable and evaluable.
- Affected modules: `src/evidence/*`, `api/services/ai_provider.py`
- Steps: define model name/version, prompt hash, input citations, output hash, status.
- Acceptance: model run can link to citations and packet IDs.
- Tests: model run validation tests.
- Risk: low
- Dependencies: CIT-001
- Rollback: no route integration until wrapper is ready.

#### AI-002: Ground canonical search answers with ModelRun and evidence packets

- Priority: P1 Production Core
- Goal: Feed canonical search results into AI grounding without relying on legacy result assumptions.
- Value: Ensures canonical AI outputs are tied to citations, source snapshots, evidence packets, and immutable model metadata.
- Affected modules: `src/search/*`, `src/evidence/*`, `tests/*`
- Steps: compose canonical search with `AIGroundingService`; reject no-evidence queries; propagate source snapshot IDs into evidence packets.
- Acceptance: grounded canonical answers include `ModelRun`, citation IDs, model run IDs, packet hash, and source snapshot IDs.
- Tests: canonical grounding success, no-evidence rejection, and existing AI grounding regression tests.
- Risk: low
- Dependencies: AI-001, SRCH-004, PKT-001
- Rollback: remove canonical grounding wrapper; existing grounding service remains available.

#### AI-003: Define canonical evaluation case/result models

- Priority: P1 Production Core
- Goal: Represent golden retrieval, citation accuracy, answer grounding, hallucination, and contradiction-candidate evaluation cases.
- Value: Creates a durable test/evaluation contract before adding evaluator runtime or model-specific scoring.
- Affected modules: `src/evidence/*`, `tests/*`
- Steps: define immutable evaluation case and result models; require expected citations; validate observed citations and score range.
- Acceptance: evaluation cases capture expected citation/document IDs and results capture pass/fail status, observed citations, optional model run ID, and bounded score.
- Tests: evaluation model validation, immutability, required citation, and score bounds tests.
- Risk: low
- Dependencies: EC-001, AI-001
- Rollback: remove evaluation model module and tests.

#### AI-004: Add deterministic retrieval recall evaluator

- Priority: P1 Production Core
- Goal: Evaluate canonical search results against expected citation IDs without LLMs or external services.
- Value: Provides a repeatable grounding/retrieval quality gate for future search migration.
- Affected modules: `src/evidence/*`, `src/search/*`, `tests/*`
- Steps: call canonical search using an `EvaluationCase`; collect observed citation IDs; compute recall score; record pass/fail result.
- Acceptance: evaluator passes only when all expected citations are retrieved, records observed citations, rejects unsupported case types, and produces bounded scores.
- Tests: retrieval evaluation pass, partial/missing recall failure, and unsupported case type tests.
- Risk: low
- Dependencies: AI-003, SRCH-004
- Rollback: remove evaluator module and tests.

#### AI-005: Add deterministic citation accuracy evaluator

- Priority: P1 Production Core
- Goal: Verify formatted results preserve expected citation quotes and document version IDs.
- Value: Creates a repeatable citation-integrity gate before grounding outputs are trusted.
- Affected modules: `src/evidence/*`, `src/search/*`, `tests/*`
- Steps: evaluate citation accuracy cases; compare observed citation IDs, normalized quotes, and document versions; report pass/fail and bounded score.
- Acceptance: evaluator passes when expected citation quote/version match, fails on quote mismatch or version mismatch, and rejects unsupported case types.
- Tests: citation accuracy pass, quote mismatch, version mismatch, and unsupported case type tests.
- Risk: low
- Dependencies: AI-003, SRCH-003
- Rollback: remove evaluator module and tests.

#### AI-006: Add deterministic grounding traceability evaluator

- Priority: P1 Production Core
- Goal: Verify grounded AI outputs preserve expected citation, `ModelRun`, and evidence packet links.
- Value: Adds a repeatable AI safety gate before answer quality or legal correctness evaluation.
- Affected modules: `src/evidence/*`, `tests/*`
- Steps: evaluate `GroundedAIOutput`; compare model input citations to expected citations; verify packet citation/model-run links and model output hash.
- Acceptance: evaluator passes when traceability is complete, fails on unexpected citations or missing packet links, and rejects unsupported case types.
- Tests: grounding pass, unexpected citation failure, missing packet model-run link failure, and unsupported case type tests.
- Risk: low
- Dependencies: AI-002, AI-003
- Rollback: remove evaluator module and tests.

#### AI-007: Add explicit deterministic evaluation suite runner

- Priority: P1 Production Core
- Goal: Run retrieval, citation accuracy, and grounding traceability cases through existing deterministic evaluators.
- Value: Provides one local evaluation entry point before CI integration or persistent evaluation storage.
- Affected modules: `src/evidence/*`, `tests/*`
- Steps: dispatch by evaluation case type; aggregate results; fail closed for missing grounded outputs and unsupported case types.
- Acceptance: runner executes supported cases, reports total/pass/fail counts, rejects unsupported cases, and does not create hidden cases or call external services.
- Tests: suite pass aggregation, missing grounding output rejection, and unsupported case type rejection tests.
- Risk: low
- Dependencies: AI-004, AI-005, AI-006
- Rollback: remove suite runner module and tests.

#### AI-008: Add local JSON evaluation fixture loader

- Priority: P1 Production Core
- Goal: Load version-controlled evaluation cases from local JSON fixtures.
- Value: Allows golden retrieval, citation, and grounding cases to exist without database or CI infrastructure decisions.
- Affected modules: `src/evidence/*`, `tests/*`
- Steps: validate the top-level fixture structure; instantiate `EvaluationCase` objects; generate stable IDs when fixture IDs are omitted; reject invalid case payloads.
- Acceptance: valid fixtures load into immutable evaluation cases; omitted IDs are stable; missing `cases` lists and invalid case payloads fail closed.
- Tests: valid fixture loading, stable ID generation, missing `cases` rejection, and invalid case rejection.
- Risk: low
- Dependencies: AI-003
- Rollback: remove fixture loader module and tests.

#### AI-009: Add synthetic local evaluation fixture corpus

- Priority: P1 Production Core
- Goal: Commit a minimal local fixture file for retrieval, citation accuracy, and grounding evaluation cases.
- Value: Gives the evaluation foundation a stable, version-controlled corpus without claiming legal correctness or requiring live data.
- Affected modules: `tests/fixtures/evaluation/*`, `tests/*`, `docs/*`
- Steps: add synthetic fixture cases; document that the corpus validates evaluator wiring only; add a loader regression test for the committed fixture.
- Acceptance: repository fixture loads through `EvaluationFixtureLoader`; supported case types are represented; fixture source identifies it as synthetic golden-case data.
- Tests: committed fixture load test and existing fixture-loader validation tests.
- Risk: low
- Dependencies: AI-008
- Rollback: remove fixture file and fixture-specific test.

#### AI-010: Add fixture-backed deterministic evaluation runner

- Priority: P1 Production Core
- Goal: Run local JSON evaluation fixtures through the deterministic suite runner when explicit runtime dependencies are provided.
- Value: Creates a reusable boundary for future manual checks or CI integration without making synthetic fixtures a production quality gate.
- Affected modules: `src/evidence/*`, `tests/*`, `docs/*`
- Steps: compose `EvaluationFixtureLoader` with `EvaluationSuiteRunner`; require caller-supplied search and grounding inputs; fail closed when required grounded outputs are missing.
- Acceptance: fixture-backed runner loads the committed fixture corpus, executes retrieval/citation/grounding cases, returns a suite report, and rejects missing grounding outputs.
- Tests: fixture-backed success and missing-grounding failure tests.
- Risk: low
- Dependencies: AI-007, AI-008, AI-009
- Rollback: remove fixture-backed runner module and tests.

### Testing and CI

#### TEST-001: Split default and external tests

- Priority: P0 Foundation
- Goal: Make default verification reliable.
- Value: Enables safe incremental migration.
- Affected modules: `tests/*`
- Steps: isolate live Adilet tests; add mocked smoke tests; keep heavy dependency tests separate.
- Acceptance: default tests run without live network.
- Tests: test suite itself.
- Risk: low
- Dependencies: none
- Rollback: restore old test command.

### Deployment and Observability

#### OPS-001: Document deterministic local setup

- Priority: P0 Foundation
- Goal: Make developer setup reproducible.
- Value: Reduces environment failures.
- Affected modules: `docs/*`
- Steps: document Python deps, frontend deps, commands, known heavy dependencies.
- Acceptance: setup docs match actual commands.
- Tests: command verification.
- Risk: low
- Dependencies: none
- Rollback: docs-only.

## First 2-Week Engineering Plan

1. EC-001
2. CIT-001
3. PKT-001
4. AUD-001
5. AI-001
6. TEST-001
7. OPS-001
8. EC-002
9. SRCH-001
10. SEC-001

## First 30-Day Production Foundation Plan

- Complete the first 2-week plan.
- Add ING-001.
- Add VER-001.
- Add GRAPH-001.
- Add CCD-001.
- Add review task model REV-001.
- Add fixture corpus for evidence import tests.

## Definition Of Done For Production Foundation

- Evidence core models are implemented and tested.
- Source snapshots have hashes.
- Legal document versions are represented explicitly.
- Citations can be generated and validated.
- Evidence packets require citations and compute stable hashes.
- Audit logs and model runs exist as domain models.
- Default tests run without live network or live AI.
- Existing `/api/v1` behavior is preserved.

## Must Not Start Yet

- Institutional Chrome extension rollout.
- Dedicated vector database migration.
- Kubernetes or microservices.
- Automatic validated obligations.
- Full enterprise monitoring UI.
- Full copilot redesign.
- PDF polish before JSON evidence packets are correct.
