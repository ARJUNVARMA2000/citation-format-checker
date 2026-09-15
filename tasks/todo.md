# Tasks

## 2026-09-15 Gemini model migration

- [x] Audit current model settings and provider lifecycle documentation.
- [x] Receive implementation and pull-request approval from Arjun.
- [x] Migrate application and evaluation models, endpoint configuration, and setup documentation.
- [x] Run relevant tests and bounded provider smoke checks.
- [x] Review the diff and prepare the pull request.

### Review

The application and evaluation judge call Gemini 2.5 Flash, which is scheduled for retirement on Vertex. Use GA Gemini 3.5 Flash-Lite for citation responses and Gemini 3.5 Flash for judging. Make both selections configurable, use the global model endpoint, refresh the LiteLLM lockfile, and correct local setup instructions.

Live APA, MLA, and Chicago citation checks returned the expected rule IDs and corrected citations. Out-of-scope routing passed. The new evaluation judge scored an exact golden-reference match 10/10. Lockfile, syntax, and diff checks passed.

Merging to master triggers the existing Cloud Run deployment workflow. The deployment environment now sets the new model and global endpoint explicitly.
