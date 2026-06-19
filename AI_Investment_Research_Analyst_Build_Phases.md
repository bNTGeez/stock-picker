# AI Investment Research Analyst — Step-by-Step Build Phases

## Purpose

This document turns the product and technical plan into a reviewable implementation roadmap.

The project should be built in gated phases, starting with the highest-risk question:

> Can the memo generator consistently produce structured, evidence-backed investment research with strong variant hypotheses?

No database, API, dashboard, or monitoring work should begin until the Phase 3 memo-quality gate passes.

---

## Phase 0 — Repo Foundation

### Goal
Prepare the project structure so the backend can be built alongside the existing Next.js app.

### Build
- Add a Python/FastAPI backend directory structure.
- Add folders for models, services, raw data, processed data, and tests.
- Add basic environment configuration for:
  - LLM provider key
  - model name
  - quote-match threshold
  - local data paths
- Add a minimal backend health check.
- Add a test runner.

### Exit Criteria
- Backend can start locally.
- Test runner works.
- Core schema modules can be imported.
- No database, dashboard, ingestion automation, or monitoring yet.

---

## Phase 1 — Manual Research Copilot

### Goal
Generate a structured Investment Memo JSON from manually supplied source text.

### Build
- Define core Pydantic schemas:
  - `EvidenceItem`
  - `ObservationItem`
  - `ObservationSection`
  - `AdversarialResearchSection`
  - `UnknownsSection`
  - `ResearchVerdict`
  - `InvestmentStance`
  - `Confidence`
  - `CategoryScore`
  - `CategoryScores`
  - `ReverseDCFExpectations`
  - `ValuationScenario`
  - `ValuationRange`
  - `MonitoringRule`
  - `InvestmentMemo`
- Build a manual memo-generation pipeline that accepts:
  - company metadata
  - local 10-K excerpts
  - local transcript excerpts
  - optional consensus notes
- Prompt the LLM to return only structured JSON matching the memo schema.
- Require the memo to preserve this reasoning chain:

```text
Evidence
↓
Observations
↓
Market Expectations
↓
Variant Hypothesis
↓
Adversarial Research Reasoning
↓
Research Verdict
↓
Investment Stance
```

### Exit Criteria
- One manually supplied company can produce a complete memo JSON.
- The output includes all fields defined in the `InvestmentMemo` schema. `reverse_dcf_expectations` may be `null` until Phase 4.
- No database, frontend, external ingestion, or automation yet.

---

## Phase 2 — Schema And Evidence Validation

### Goal
Prevent invalid memo structure and fabricated evidence.

### Build
- Enforce strict schema validation for all memo fields and enums.
- Validate that no composite or weighted aggregate score is produced. Category scores must remain individual labels; the system must not surface a single overall ranking signal.
- Validate that category scores exist for all six weighted categories:
  - Business Quality — 30%
  - Risk Profile — 20%
  - Expectations Gap — 20%
  - Variant Perception — 15%
  - Valuation — 10%
  - Catalyst — 5%
- Add quote validation:
  - normalize whitespace in quote and source text
  - exact normalized substring match first
  - fuzzy fallback if exact match fails
  - reject evidence below the match threshold
- Store validation metadata on each evidence item:
  - `normalized_quote`
  - `located_start_offset`
  - `located_end_offset`
  - `match_score`
- Require evidence references for:
  - observations
  - adversarial evidence for the variant view
  - adversarial evidence against the variant view
  - monitoring rules where applicable

### Exit Criteria
- Fabricated or unlocatable quotes fail validation.
- Malformed memos fail fast.
- Valid memos contain located evidence offsets and match scores.
- The system can return `Insufficient Evidence` instead of inventing conviction.

---

## Phase 3 — Memo Quality Evaluation Gate

### Goal
Prove the memo generator is analytically useful before building infrastructure around it.

### Build
- Select 5-10 companies the reviewer already understands deeply.
- Generate memos through the normal Phase 1-2 pipeline.
- Score each memo manually using the rubric:
  - Did it identify the real variant hypothesis?
  - Did it miss obvious risks?
  - Did it overstate confidence?
  - Did it correctly explain what is priced in?
  - Were the monitoring rules useful and specific?
  - Did the evidence actually support the conclusion?
  - Did it fairly present the strongest opposing case?
  - Did the final synthesis explain why one argument was better supported?
- Recommended passing threshold:
  - average score at least `4.0 / 5`
  - no criterion below `3 / 5`
  - no fabricated or unvalidated evidence
- Known limitation: criterion 4 (did it correctly explain what is priced in?) is evaluated qualitatively only — consensus narrative, valuation multiples, guidance, estimate revision direction, and transcript sentiment. The quantitative reverse DCF engine is added in Phase 4. Score this criterion against qualitative reasoning; do not hold Phase 3 to a standard that requires Phase 4 tooling.

### Exit Criteria
- If the memo generator passes, proceed to Phase 4.
- If it fails, revise prompts, schemas, and validation rules, then rerun Phase 3.
- Do not build database, API, dashboard, or monitoring before this gate passes.

---

## Phase 4 — Reverse DCF Expectations Engine

### Goal
Add deterministic market-expectations analysis without letting the LLM calculate numbers.

### Build
- Implement reverse DCF calculations in Python.
- Inputs:
  - share price
  - shares outstanding
  - net debt
  - current revenue
  - FCF margin assumptions
  - WACC range
  - terminal assumptions
  - SBC or dilution adjustments
- Outputs:
  - `implied_revenue_cagr_low`
  - `implied_revenue_cagr_mid`
  - `implied_revenue_cagr_high`
  - `implied_fcf_margin_low`
  - `implied_fcf_margin_mid`
  - `implied_fcf_margin_high`
- Include required adjustments and sensitivities:
  - EV adjustments
  - net debt adjustments
  - SBC dilution adjustments
  - cyclicality adjustments
  - WACC sensitivity analysis
- Let the LLM explain deterministic outputs, but never calculate them.

### Exit Criteria
- Deterministic tests pass for known fixtures.
- Generated memos can populate `reverse_dcf_expectations` with the exact reverse DCF output fields listed above.
- Tests cover EV, net debt, SBC dilution, cyclicality, and WACC sensitivity behavior.
- No price targets or buy/sell recommendations are introduced.

---

## Phase 5 — SEC And Transcript Parsing

### Goal
Reduce manual source preparation while preserving evidence traceability.

### Build
- Build local-file parsers for SEC filings and transcripts.
- Extract:
  - business overview
  - risk factors
  - MD&A
  - financial notes
  - management commentary
  - analyst Q&A
  - relevant transcript sections
- Preserve source IDs and normalized source text for quote validation.

### Exit Criteria
- Parser outputs reusable source documents.
- Memo generator can cite parsed source documents.
- Validator can locate cited quotes in parsed source text.

---

## Phase 6 — Database Layer

### Goal
Persist research history after the memo core has proven useful.

### Build
- Add the planned core tables:
  - companies
  - source_documents
  - financial_statements
  - financial_metrics
  - consensus_estimates
  - price_snapshots
  - stock_reports
  - report_scores
  - valuation_ranges
  - risk_items
  - monitoring_flags
  - memo_quality_evaluations
- Store `raw_memo_json` as a JSONB field on `stock_reports` before normalization to protect against future schema changes.
- Preserve validated evidence metadata inside the report payload until or unless a dedicated evidence table is added in a later schema revision.

### Exit Criteria
- Reports can be saved, retrieved, and revalidated.
- Quality evaluation scores and reviewer notes are persisted.

---

## Phase 7 — FastAPI API Layer

### Goal
Expose the research pipeline through controlled backend endpoints.

### Build
- Add endpoints:
  - `POST /reports/generate`
  - `GET /reports/{id}`
  - `GET /companies/{ticker}/reports`
  - `POST /evaluations`
  - `GET /monitoring/{ticker}`
- Keep verdict, stance, and confidence changes human-reviewed.

### Exit Criteria
- API can run the memo pipeline from uploaded or local source files.
- API returns validated report JSON.
- API does not make autonomous investment decisions.

---

## Phase 8 — Research Dashboard

### Goal
Use the existing Next.js app as the review interface.

### Build
- Display:
  - market expectations
  - six weighted category scores
  - observations
  - variant hypothesis
  - why consensus may be wrong
  - adversarial research reasoning
  - unknowns
  - risks
  - valuation range
  - reverse DCF expectations, once Phase 4 is enabled
  - evidence
  - monitoring rules
  - research verdict
  - investment stance
  - confidence
  - recommended next step
- Add report history views.
- Add manual quality evaluation scoring views.

### Exit Criteria
- User can inspect a memo.
- User can trace evidence.
- User can score memo quality.
- User can compare historical reports.

---

## Phase 9 — Monitoring Engine

### Goal
Surface evidence-linked changes without allowing autonomous decisions.

### Build
- Compare new transcripts, filings, or source updates against existing monitoring rules.
- Automatically flag:
  - Green events
  - Yellow events
  - Red events
- Allow the system to propose changes to verdict, stance, or confidence.
- Allow the system to propose updates to monitoring rules.
- Require human approval before any official memo state changes, including monitoring rule updates.

### Exit Criteria
- Monitoring surfaces evidence-linked alerts.
- Monitoring proposes but does not decide.
- No portfolio management or trading action is added.

---

## Non-Negotiable Constraints

- Human remains the final decision-maker.
- Scores are summaries, not the analysis.
- The primary output is the evidence-backed explanation, not a rating.
- The system is not an autonomous stock picker, portfolio manager, or trading engine.
- The LLM does not perform deterministic financial calculations.
- The project must pass Phase 3 before infrastructure work begins.
