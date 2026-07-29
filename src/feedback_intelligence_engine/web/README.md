# Reviewer UI

The reviewer interface is intentionally dependency-free: semantic HTML, CSS and browser JavaScript are served by the FastAPI application. This avoids a separate frontend build pipeline while the product workflow is still evolving.

## Screens

- Overview dashboard with validation quality, review progress, source mix and leading themes
- Theme review workspace with evidence, deterministic metrics and historical comparison
- Dataset history and validation counts
- Immutable reviewed reports
- Structured workflow activity

## Core interactions

- Upload a CSV or run the included 250-row CFPB sample
- Search and filter themes
- Rename and edit theme copy
- Merge multiple themes
- Split selected source feedback into a new theme
- Approve or reject themes
- Save an immutable reviewed report

The visual direction uses soft neutral surfaces, oversized rounded cards, charcoal controls and a restrained yellow accent. It is inspired by the supplied dashboard reference without reproducing its product structure or content.
