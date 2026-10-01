# api-contract

Kontrakt API (TASK-2.1, [ADR-024](../../docs/architecture/ADR-024-api-contract-generation.md)):

- `openapi.json` — schemat OpenAPI FastAPI, generowany: `cd apps/api && uv run python scripts/export_openapi.py`
- `schema.ts` — typy TS (jeden `export type` na schemat), generowane: `node packages/api-contract/generate.mjs`
- `generate.mjs` — generator bez zależności (Node ≥ 22); `--check` wykorzystuje CI.

Nie edytuj `openapi.json` ani `schema.ts` ręcznie. Mobile importuje wyłącznie `import type`
(np. `../../../packages/api-contract/schema`), więc nic z tego pakietu nie trafia do bundla.
