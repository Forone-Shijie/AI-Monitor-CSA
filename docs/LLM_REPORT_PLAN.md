# AI Report (Bilingual) Plan - Qwen2.5-7B Local

## Scope
- Generate post-session evaluation reports using a local LLM.
- Store bilingual fields in backend (ZH + EN) while keeping existing fields for backward compatibility.
- Prioritize report quality over latency; batch/offline generation is acceptable.
- Deployment target: WSL2 Ubuntu, easy migration to other machines.

## Current Code Touchpoints
- Backend report logic: `backend/src/evaluation/report_generator.py`
- API report endpoints: `backend/src/api/routes/evaluation.py`
- API schemas: `backend/src/api/schemas.py`
- Config: `backend/config/config.yaml`
- Frontend types: `frontend/src/types/api.ts`
- Frontend report UI: `frontend/src/views/Reports.vue`

## Target Architecture (Post-Session)
1) Session ends -> evaluation result exists.
2) Report generator builds structured metrics context.
3) Local LLM generates bilingual JSON report.
4) Backend stores both new bilingual fields and existing legacy fields.
5) API serves report for UI rendering.

## LLM Deployment (Local)
- Recommended runtime: Ollama
- Model: `qwen2.5:7b`
- Example base URL:
  - OpenAI-compatible: `http://localhost:11434/v1`
  - Native Ollama: `http://localhost:11434`

## Data Contract (LLM Output JSON)
```json
{
  "summary_zh": "2 sentences max",
  "summary_en": "2 sentences max",
  "action_items": [
    {
      "priority": "high",
      "zh": "short actionable item",
      "en": "short actionable item",
      "evidence": ["pose.stability=0.72"]
    }
  ]
}
```

## Backend Storage (Keep Legacy Fields)
- New fields:
  - `ai_summary_zh`, `ai_summary_en`
  - bilingual suggestion fields (see below)
- Legacy fields kept:
  - `ai_summary`
  - `suggestions[].issue`, `suggestions[].suggestion`, `suggestions[].example`

## Suggested Schema Extensions
### ReportData (backend + frontend)
- Add:
  - `ai_summary_zh: string`
  - `ai_summary_en: string`

### SuggestionData (backend + frontend)
- Add:
  - `issue_zh`, `issue_en`
  - `suggestion_zh`, `suggestion_en`
  - `example_zh`, `example_en`
- Keep existing fields for compatibility and map them from ZH content.

## Prompt Template (Bilingual, Concise)
System:
- "You are a training evaluation expert. Output JSON only."
User:
- Provide structured metrics and rubric.
- Require:
  - `summary_zh` + `summary_en` (2 sentences each)
  - `action_items` max 3
  - No additional fields

## Implementation Steps
### Phase 0 - Environment
1) Install Ollama in WSL2.
2) `ollama pull qwen2.5:7b`.
3) Verify local inference via curl.

### Phase 1 - LLM Provider
1) Add an LLM provider that calls the local endpoint.
2) Read `evaluation.llm` from `backend/config/config.yaml`.
3) Support `model`, `base_url`, `temperature`, `max_tokens`.

### Phase 2 - Report Generator
1) Build a structured context from `EvaluationResult`:
   - Pose: stability, category scores, improvements.
   - Action: completion_rate, sequence_correct, average_delay.
   - Communication: terminology_accuracy, clarity_score, missed_terms.
2) Generate LLM JSON and parse strictly.
3) Populate bilingual fields.
4) Fill legacy fields from ZH output for compatibility.

### Phase 3 - API Layer
1) Extend `ReportData` and `SuggestionData` schemas.
2) Update `/reports` and `/reports/{session_id}` responses.
3) Keep old fields to avoid frontend breakage.

### Phase 4 - Frontend
1) Extend `ReportData` and `Suggestion` types.
2) Update report UI to show ZH + EN summary.
3) For suggestions, show ZH as primary and EN as secondary text.

### Phase 5 - Tests and Validation
1) Add unit test for LLM JSON parsing with sample payload.
2) Add test for report generation when LLM is unavailable (fallback).
3) Manual validation: generate a report and verify bilingual fields in API response.

## Acceptance Criteria
- Report endpoint returns bilingual fields without breaking existing UI.
- Summary is concise (2 sentences max for each language).
- Action items <= 3 and include evidence references.
- LLM failures gracefully degrade to rule-based suggestions.

## Risks / Notes
- LLM output format drift: mitigate with strict JSON parsing and retries.
- GPU memory for qwen2.5-7b: use 4-bit quantization if needed.
- Ensure no blocking calls in request path if generation is slow.

## Optional Enhancements (Later)
- Background job for report generation (async queue).
- Report versioning and prompt version in metadata.
- Configurable bilingual toggle on UI.

