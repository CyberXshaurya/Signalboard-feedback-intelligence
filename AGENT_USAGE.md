# Agent Usage

## Tools used

A coding assistant was used for repository design, repetitive API and persistence code, UI implementation, test generation, release review and documentation. Browser automation, backend tests and real-data runs were used to verify—not merely accept—the generated output.

## Representative prompts

- “Design a data model that keeps original feedback, AI theme drafts, evidence membership and human review history separate.”
- “Propose tests proving merge and split operations never lose feedback memberships.”
- “Create a warm, rounded dashboard inspired by the supplied visual reference, but tailored to evidence-backed feedback review.”
- “Add a GitHub Models adapter with strict JSON output while keeping the server token out of browser responses.”
- “Audit every visible `data-action`, make modals keyboard-accessible, and execute critical reviewer flows through Playwright.”
- “Add product-memory CRUD and rerun historical comparison without including historical records in current counts.”

## Work delegated

- First-pass SQLAlchemy models and typed API schemas.
- Edge-case test ideas for CSV validation, evidence grounding, review actions and immutable reports.
- Hybrid clustering and provider-adapter scaffolding.
- Initial dashboard and review-workspace markup.
- README structure, deployment notes and release-media generation.

Every delegated change was inspected, exercised against tests and revised when the observed behaviour was not acceptable.

## Important rejected suggestions

- **LLM-generated counts:** rejected. Counts and distributions are calculated from persisted memberships.
- **Automatic roadmap ranking:** rejected. The product synthesises evidence; it does not prioritise the roadmap.
- **Automatic merges:** rejected. Merge and split require explicit human action.
- **Raw customer text in AI logs:** rejected. Logs record identifiers, timing and outcome—not sensitive prompts.
- **Public or borrowed API keys:** rejected. Only operator-owned backend credentials are supported.
- **Silently claiming an LLM is operational:** rejected. A provider self-test performs a real minimal inference and labels the deterministic fallback separately.

## Important agent mistakes and corrections

### Clustering calibration

The first threshold was too conservative on the 250-row public sample and created 235 mostly singleton themes. That result was rejected. Metadata-aware vectors, calibrated similarity, redaction-noise filtering and a maximum cluster size were added. The repeated deterministic smoke run created 39 reviewable themes with a maximum cluster size of 30.

### Modal event propagation

The first modal implementation stopped click propagation on the dialog while close actions were delegated to the document. Consequently, backdrop clicks worked but X, Done and Cancel could fail. The modal controller was rewritten with direct close listeners, backdrop detection, `Escape`, focus restoration and a keyboard focus trap. Playwright now clicks the affected controls.

### Static-only UI verification

The first UI test only checked that HTML, CSS, JavaScript and the sample CSV were served. It could not detect broken interactions. Browser tests were added for provider verification, historical-note add/edit/delete confirmation, modal controls, keyboard shortcuts, rename, approve, split, merge and report saving. A static audit also confirms every visible `data-action` has a dispatcher.

### Historical comparison UI gap

The backend initially supported historical records without a complete user-facing management flow. A product-memory view was added with create, edit, delete and rerun comparison controls. Historical records remain contextual and never enter current feedback counts.

### Strict structured-output schema

The first GitHub Models schema inherited open Pydantic objects. Strict JSON output requires closed objects and fully required nullable fields. Extra properties were forbidden, the uncertainty field became required-but-nullable and contract assertions were added.

### Sample delivery path

The first static layout placed the sample under a path different from the frontend request. A delivery test found the 404. The sample was moved to the mounted package root and a regression test was added.

## Verification performed

- Model evidence IDs are intersected with persisted candidate-cluster IDs.
- Malformed CSV, alias mapping, duplicate warnings and upload boundaries are tested.
- Deterministic analytics and evidence coverage are tested independently from the LLM.
- Merge and split tests prove memberships are preserved.
- Report tests prove saved snapshots remain unchanged after later edits.
- GitHub Models and OpenAI request/response contracts are mocked and inspected.
- Explicit provider modes fail visibly when credentials or local services are unavailable.
- The provider self-test never exposes credential values.
- Historical-memory CRUD is tested through the API and browser.
- Playwright exercises X/Done/Cancel, Escape, focus behaviour, theme review actions and report creation.
- The release test loads the mapped public dataset, analyses it, approves a theme and reads an immutable report back.
- Product screenshots and the README GIF are generated from the actual bundled interface.

## Verification boundary

A real GitHub Models request requires the operator's private token and was not executed in the build environment. The request contract is automated, and the deployed interface contains **Provider settings → Run live provider check** so the operator can prove the hosted provider works without exposing the token.
