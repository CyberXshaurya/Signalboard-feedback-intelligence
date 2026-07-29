# Agent Usage

## Tools used

A coding assistant was used to help design the repository structure, implement repetitive API and persistence code, build the reviewer UI, propose test cases and review data-flow boundaries.

## Representative prompts

- “Design a database model that keeps original feedback, AI theme drafts, evidence membership and human review history separate.”
- “Propose tests proving that merge and split operations never lose feedback memberships.”
- “Create a warm, rounded reviewer dashboard inspired by the supplied reference, but tailored to feedback analysis rather than HR metrics.”
- “Add a provider adapter for GitHub Models that requests JSON-schema output and never sends the server token to the browser.”

## Representative delegated work

- Generate a first-pass SQLAlchemy schema for projects, datasets, feedback, themes, review actions and immutable reports.
- Propose edge-case tests for CSV validation, evidence grounding, merge, split and report snapshots.
- Draft a hybrid clustering and structured-output interface.
- Build an initial responsive reviewer dashboard from the supplied visual reference.
- Add GitHub Models and Ollama provider adapters without exposing credentials to the browser.

## Important rejected suggestions

- LLM-generated feedback counts were rejected. Counts and distributions are calculated only from database memberships.
- Automatic roadmap prioritisation was rejected because the product is a synthesis and review tool, not a prioritisation engine.
- Automatic theme merges were rejected; only a human can apply a merge.
- Storing unmasked customer text in AI logs was rejected.
- Using API keys found in public GitHub repositories was rejected. The implementation accepts only a legitimate server-side token supplied by the operator.
- A separate JavaScript dependency stack was rejected for this phase after the package registry was unavailable. The final reviewer UI uses dependency-free browser code and is served by FastAPI.

## Important agent mistakes and corrections

### Clustering calibration

The first clustering configuration was too conservative on 250 real complaint narratives and produced 235 mostly singleton themes. The result was rejected after a real-data smoke test. The engine was changed to use metadata-aware vectors, a calibrated threshold, redaction-noise filtering and a hard maximum cluster size. The repeated smoke test produced 39 reviewable themes with a maximum size of 30.

### Sample delivery path

The first UI static-file layout placed the sample CSV under a `public` subdirectory while the interface requested it from `/app/cfpb_feedback_sample.csv`. A delivery test caught the 404. The sample was moved to the mounted static root and a regression test was added.


### Strict structured-output schema

The first raw GitHub Models schema used Pydantic's default JSON schema. A release contract review found that strict structured output requires closed objects and a fully required nullable field. The models were changed to forbid extra properties, `uncertainty_reason` became required-but-nullable, and regression assertions now verify `additionalProperties: false` at both schema levels.

### Browser preview dependencies

The first visual preview attempted to load a remote web font. Browser console verification exposed the unnecessary network request. The UI was changed to a system-font stack and a data-URI favicon, leaving the interface with no external frontend runtime dependency or console error.

## Verification performed

- All generated evidence IDs are intersected with the cluster's persisted IDs.
- Unit tests validate malformed CSVs and duplicate handling.
- End-to-end tests cover upload through immutable report creation.
- Merge and split tests confirm no feedback memberships are lost.
- The deterministic fallback keeps tests independent of external model availability.
- OpenAI structured-output batching is tested with a mocked SDK contract.
- GitHub Models JSON-schema requests and server-side token handling are tested with a mocked HTTP contract.
- Explicit provider modes fail visibly when required credentials or local services are missing.
- The reviewer UI and bundled sample are verified through the FastAPI static delivery layer.
- A real browser smoke test against a seeded 250-row database verified dashboard rendering, evidence loading, approval and report saving.
- The final browser smoke run produced no console or page errors.
- The final release suite has 14 passing tests and 83.47% statement coverage.
