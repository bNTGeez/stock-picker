# AI Investment Research Analyst — Product & Technical Plan

## Mission

The system automates evidence gathering, structuring, and first-pass analysis, while final judgment and capital allocation remain human-controlled.

The primary output of the system is not a score or verdict. The primary output is a structured, evidence-backed explanation of market expectations, business reality, risks, and thesis evolution.

It is designed to answer one question:

> "Is this stock misunderstood enough to deserve deeper research or capital?"

The system is **not** an autonomous stock picker, portfolio manager, or trading engine.

It produces:

- Research verdicts
- Investment stances
- Expectations analysis
- Risk mapping
- Variant perception
- Valuation ranges
- Monitoring rules

Final capital allocation decisions remain with the user.

---

## Core Philosophy

Most research systems ask: *Is this a good company?*

This system asks:

- What does the market expect?
- What does the evidence suggest?
- Where is the mismatch?
- What would prove the thesis right or wrong?

The objective is not to predict stock prices. The objective is to identify situations where market expectations may be materially different from business reality.

The memo must preserve the research chain explicitly:

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

The model should not jump directly from evidence to a verdict. It must first state the observations the evidence supports, then anchor the variant hypothesis against what the market is currently pricing in, and test that hypothesis against the strongest opposing case. The variant hypothesis must answer: *variant relative to what?*

---

## Research Framework

Every company is evaluated using six scored categories.

| Category | Weight |
| --- | --- |
| Business Quality | 30% |
| Risk Profile | 20% |
| Expectations Gap | 20% |
| Variant Perception | 15% |
| Valuation | 10% |
| Catalyst | 5% |

**Scores are summary labels, not the analysis.** Evidence, rationale, variant hypothesis, risks, and monitoring rules are the actual product. A numeric score is a compressed label over the underlying reasoning — it is never a substitute for it, and it carries no standalone authority.

Category scores must not be combined into a composite or weighted aggregate. The weights indicate review emphasis — the order in which categories deserve analytical attention — not optimization targets. A high composite score cannot override a weak variant hypothesis, and a low composite score cannot dismiss a strong one. The system must never surface a single "overall score" or ranking signal.

### Category Score Schema

```python
class CategoryScore(BaseModel):
    score: int                    # 0–100 summary label
    weight: float                 # fixed category weight
    rationale: str                # why the score summarizes the underlying analysis

class CategoryScores(BaseModel):
    business_quality: CategoryScore      # weight 0.30
    risk_profile: CategoryScore          # weight 0.20
    expectations_gap: CategoryScore      # weight 0.20
    variant_perception: CategoryScore    # weight 0.15
    valuation: CategoryScore             # weight 0.10
    catalyst: CategoryScore              # weight 0.05
```

The schema must enforce all six categories and their fixed weights. The score is not evidence by itself; the rationale must be consistent with the memo's observations, variant hypothesis, risks, valuation range, and monitoring rules.

### Business Quality
Competitive moat, pricing power, customer stickiness, capital efficiency, historical ROIC, industry structure.

### Risk Profile
Business risks, execution risks, financial risks, valuation risks, macro risks.

### Expectations Gap
What the current stock price implies, market-implied growth assumptions, market-implied margin assumptions, and whether expectations are too low, reasonable, or excessive.

### Variant Perception
What consensus believes, what the evidence suggests instead, why consensus may be wrong, and the confidence level.

### Valuation
Valuation **ranges**, not target prices: Bear Case, Base Case, Bull Case.

```python
class ValuationScenario(BaseModel):
    label: Literal["Bear", "Base", "Bull"]
    assumptions: List[str]
    implied_outcome: str
    supporting_evidence: List[EvidenceItem]

class ValuationRange(BaseModel):
    bear: ValuationScenario
    base: ValuationScenario
    bull: ValuationScenario
```

### Catalyst
Events capable of forcing expectations to converge with reality: product launches, margin inflections, industry shifts, regulatory changes, competitive failures.

---

## Advisory Outputs

These outputs do **not** contribute to the score.

### Research Verdict
Single field (formerly split across "Research Verdict" and "Research Priority"):

- Insufficient Evidence
- Reject
- Watchlist
- Research Further
- Candidate
- High Conviction Candidate

### Investment Stance
Kept separate from the verdict:

- Bearish
- Lean Bearish
- Neutral
- Lean Bullish
- Bullish

### Confidence
- Low
- Medium
- High

### Monitoring Rules
- **Green Flags** — evidence the thesis is strengthening.
- **Yellow Flags** — evidence requiring closer monitoring.
- **Red Flags** — evidence that materially damages the thesis.

---

## Product Output

Every analysis produces a structured Investment Memo.

```
Research Verdict:        High Conviction Candidate
Investment Stance:       Lean Bullish
Confidence:              Medium

Category Scores:
  Business Quality:      82 / 100
  Risk Profile:          58 / 100
  Expectations Gap:      76 / 100
  Variant Perception:    80 / 100
  Valuation:             64 / 100
  Catalyst:              55 / 100

Market Expectations:     Pricing in 12–18% revenue growth

Observations:
  - Revenue concentration risk is higher than peers.
  - AI infrastructure demand appears stronger than consensus implies.

Variant Hypothesis:      Growth likely exceeds expectations due to
                         AI infrastructure demand.

Why Consensus May Be Wrong:
                         Consensus underestimates networking
                         bottlenecks and cloud capex demand.

Adversarial Research Reasoning:
  Bull Case:             AI infrastructure demand drives upside to
                         revenue and margins.
  Bear Case:             Demand normalizes and concentration risk
                         offsets growth.
  Key Disagreement:      Whether current demand is durable or pulled
                         forward.
  Evidence For Variant:  Transcript commentary and capex trends.
  Evidence Against:      Customer concentration and cyclical capex risk.
  Rebuttal:              Multi-year cloud buildouts reduce the chance
                         that demand is purely temporary.
  Disconfirming Evidence:
                         Slowing backlog, weaker renewals, or lower
                         AI-related disclosure.
  Final Synthesis:       Variant view is plausible but still requires
                         monitoring and additional evidence.

Unknowns:
  - Customer-level retention data unavailable
  - Management has not disclosed AI revenue contribution
  - Consensus margin assumptions unavailable

Top Risks:
  - AI spending slowdown
  - Customer concentration
  - Multiple compression

Valuation Range:
  Bear:                  Assumptions X, Y, Z → outcome.
  Base:                  Assumptions A, B, C → outcome.
  Bull:                  Assumptions P, Q, R → outcome.
  (Each scenario lists assumptions, implied outcome, and
   supporting evidence. No point target.)

Reverse DCF Expectations:
                         Optional until Phase 4. Once enabled,
                         stores implied revenue CAGR and FCF margin
                         ranges as structured fields.

Monitoring Rules:        Green / Yellow / Red triggers

Recommended Next Step:   Further research warranted. Final decision
                         is the user's.
```

---

## System Architecture

A modular FastAPI backend. Not microservices. Not autonomous agents.

```
research-copilot/
│
├── data/
│   ├── raw/
│   └── processed/
│
├── models/
│   └── schemas.py
│
├── services/
│   │
│   ├── ingestion/
│   │   ├── sec_parser.py
│   │   └── transcript_parser.py
│   │
│   ├── agents/
│   │   ├── prompts.py
│   │   └── memo_generator.py
│   │
│   ├── valuation/
│   │   └── reverse_dcf.py
│   │
│   ├── validation/
│   │   └── validator.py
│   │
│   ├── evaluation/
│   │   └── rubric.py
│   │
│   └── database/
│       └── persistence.py
│
├── main.py
├── config.py
└── requirements.txt
```

---

## LLM Responsibilities

The LLM performs:

- Business analysis
- Risk extraction
- Variant perception generation
- Monitoring rule generation
- Evidence-backed synthesis

The LLM does **NOT** perform:

- DCF calculations
- Financial statement calculations
- Share count calculations
- Debt calculations
- WACC calculations

All numerical analysis must be deterministic Python.

---

## Evidence System

Every major conclusion must be traceable. Evidence is not a free-form string.

```python
class EvidenceItem(BaseModel):
    source_type: str              # e.g. "10-K Item 1A", "transcript", "consensus_estimate"
    source_tier: int              # 1–4, based on the source hierarchy below
    source_id: str                # document identifier the quote was drawn from
    quote: str                    # the raw quoted text as produced by the LLM
    normalized_quote: str         # whitespace-normalized form used for matching
    located_start_offset: int | None = None   # offset in normalized source, set after match
    located_end_offset: int | None = None     # offset in normalized source, set after match
    match_score: float            # similarity score of the best match (0.0–1.0)
```

Source examples: 10-K Item 1A, Earnings Transcript Q2 2025, Consensus Estimate FY2027, Historical ROIC Calculation.

### Source Hierarchy

Not all evidence carries equal weight. Confidence should partially depend on source quality.

| Tier | Source Types |
| --- | --- |
| 1 | SEC filings, financial statements |
| 2 | Earnings transcripts, investor presentations |
| 3 | Consensus estimates, industry reports |
| 4 | News articles, secondary commentary |

A variant hypothesis supported by a 10-K, transcript, and financial statements should carry more weight than one supported only by news articles and analyst commentary.

### Observations

Observations are the bridge between raw evidence and the variant hypothesis. They force the model to state what the evidence implies before it argues for a verdict or stance.

```python
class ObservationItem(BaseModel):
    statement: str
    supporting_evidence: List[EvidenceItem]

class ObservationSection(BaseModel):
    observations: List[ObservationItem]
```

Example:

- Evidence: Customer concentration is 38%.
- Observation: Revenue concentration risk is higher than peers.
- Variant Hypothesis: Market is underestimating diversification improvements.

### Adversarial Research Reasoning

Investment research is argumentative. Every memo must explicitly test the variant hypothesis against the strongest opposing case before assigning a verdict or stance.

```python
class AdversarialResearchSection(BaseModel):
    bull_case: str
    bear_case: str
    key_disagreement: str
    evidence_for_variant_view: List[EvidenceItem]
    evidence_against_variant_view: List[EvidenceItem]
    rebuttal: str
    disconfirming_evidence: List[str]
    final_synthesis: str
```

The goal is not to create an autonomous decision-maker. The goal is to force structured disagreement:

- Bull Case — why the stock may be misunderstood positively.
- Bear Case — why the market may be right or too optimistic.
- Key Disagreement — the central point the research must resolve.
- Evidence For Variant View — the strongest evidence supporting the thesis.
- Evidence Against Variant View — the strongest evidence challenging it.
- Rebuttal — why the selected thesis may still survive the opposing case.
- Disconfirming Evidence — what would weaken or break the thesis.
- Final Synthesis — why the verdict is better supported, or why evidence remains insufficient.

### Unknowns

Hidden uncertainty is one of the biggest failure modes in LLM research. Every memo must explicitly state what the model does not know.

```python
class UnknownsSection(BaseModel):
    unknowns: List[str]
```

Examples:

- Customer-level retention data unavailable
- Management has not disclosed AI revenue contribution
- Consensus margin assumptions unavailable

### Investment Memo Schema

```python
class InvestmentMemo(BaseModel):
    research_verdict: ResearchVerdict
    investment_stance: InvestmentStance
    confidence: Confidence
    category_scores: CategoryScores
    market_expectations: str
    observations: ObservationSection
    variant_hypothesis: str
    why_consensus_may_be_wrong: str
    adversarial_research: AdversarialResearchSection
    unknowns: UnknownsSection
    top_risks: List[str]
    valuation_range: ValuationRange
    reverse_dcf_expectations: ReverseDCFExpectations | None = None
    monitoring_rules: List[MonitoringRule]
    recommended_next_step: str
```

`why_consensus_may_be_wrong` is a top-level memo field. It explains the gap between consensus assumptions and the evidence-backed variant hypothesis; it is related to adversarial reasoning, but it is not nested inside `AdversarialResearchSection`.

---

## Evidence Validation

This is a core feature. It exists to prevent fabricated evidence — every quote must be located in its claimed source or the memo is rejected.

**Validator logic:**

1. Normalize whitespace in both the quote and the source text (collapse runs of whitespace, strip, standardize line breaks). Store the normalized quote in `normalized_quote`.
2. Check whether the normalized quote exists as an exact substring of the normalized source.
3. If no exact match, run fuzzy matching against the source (e.g. best-window similarity).
4. Accept the match only if `match_score` is above ~0.95.
5. Reject any evidence item below the threshold — and reject the memo if any item fails.
6. On an accepted match, store `located_start_offset`, `located_end_offset`, and `match_score`.

Exact string equality (`source_text[start:end] == quote`) is intentionally **not** used: real source text varies by whitespace, PDF-extraction artifacts, and minor LLM paraphrase, so strict equality would reject legitimate quotes. The normalize-then-fuzzy-with-threshold approach keeps the "no fabricated evidence" guarantee while surviving real-world text.

---

## Memo Quality Evaluation

Schema validation and quote verification only prove a memo is **structurally valid** — that it has the right shape and that its quotes exist. They say nothing about whether the memo is **analytically useful**. A memo can pass every validator and still pick the wrong variant hypothesis, miss an obvious risk, or overstate confidence.

This layer closes that gap with a manual, human-scored evaluation loop.

The project may not proceed to database, API, dashboard, or monitoring development until the memo generator achieves a predefined quality threshold on the evaluation rubric.

Default quality gate:

- Average rubric score must be at least `4.0 / 5`.
- No individual criterion may be below `3 / 5`.
- No fabricated or unvalidated evidence is allowed.

**Workflow:**

1. Choose 5–10 companies the reviewer already understands deeply.
2. Generate memos for each through the normal pipeline.
3. Score each memo by hand against the rubric below.
4. Record the scores and notes (persisted — see Database Design).
5. Re-run this evaluation whenever prompts, parsing, or the memo generator change, so quality is treated as a regression target, not a one-time check.

**Rubric** (per memo):

| # | Criterion |
| --- | --- |
| 1 | Did it identify the real variant hypothesis? |
| 2 | Did it miss obvious risks? |
| 3 | Did it overstate confidence? |
| 4 | Did it correctly explain what is priced in? |
| 5 | Were the monitoring rules useful and specific? |
| 6 | Did the evidence actually support the conclusion? |
| 7 | Did it fairly present the strongest opposing case? |
| 8 | Did the final synthesis explain why one argument was better supported? |

Each criterion is scored (e.g. 1–5) with a short written justification. The aggregate, plus the notes, is the real signal for whether the memo generator is good enough to build further infrastructure on top of. Phase 3 specifically tests whether the system can consistently generate high-quality variant hypotheses before database, API, dashboard, or monitoring work begins. **A structurally valid system that produces subtly wrong memos is more dangerous than an obviously broken one, because the polish invites misplaced trust.** This layer is the guard against that.

---

## Reverse DCF Expectations Engine

**Purpose:** not valuation prediction — determining what expectations are embedded in the current stock price.

Output (a range, never a single precise number):

```python
class ReverseDCFExpectations(BaseModel):
    implied_revenue_cagr_low: float
    implied_revenue_cagr_mid: float
    implied_revenue_cagr_high: float
    implied_fcf_margin_low: float
    implied_fcf_margin_mid: float
    implied_fcf_margin_high: float
```

This field is optional in `InvestmentMemo` during Phases 1–3 and becomes populated after Phase 4.

Includes: EV adjustments, net debt adjustments, SBC dilution adjustments, cyclicality adjustments, and WACC sensitivity analysis. All of it is deterministic Python — the LLM does not touch these numbers.

---

## Database Design

The database preserves research history.

Core tables:

- companies
- source_documents
- financial_statements
- financial_metrics
- consensus_estimates
- price_snapshots
- stock_reports
- report_scores
- risk_items
- valuation_ranges
- monitoring_flags
- memo_quality_evaluations  *(rubric scores + reviewer notes per memo)*

Every report stores `raw_memo_json JSONB` **before** normalization, to protect against future schema changes.

---

## Build Roadmap

**Phase 0 — Repo Foundation**
Add the backend project foundation alongside the existing Next.js app: Python/FastAPI structure, data folders, test runner, health check, and environment configuration for LLM provider, model name, quote-match threshold, and local data paths. *Success: backend starts locally, tests run, and schema modules can be imported.*

**Phase 1 — Manual Research Copilot**
Generate a validated Investment Memo JSON from manually supplied source files (local 10-K, local transcript, optional consensus estimates). Define the core memo schema, including category scores for the six weighted research categories. No database, no frontend, no automation. *Success: reliable evidence-backed memo generation.*

**Phase 2 — Schema Validation Layer**
Enforce strict Pydantic validation of category scores, category weights, evidence, quotes, valuation ranges, and verdicts.

**Phase 3 — Memo Quality Evaluation**
Run the manual rubric across 5–10 well-understood companies. No database, API, dashboard, or monitoring work begins until the memo generator passes the quality gate: average score at least `4.0 / 5`, no criterion below `3 / 5`, and no fabricated or unvalidated evidence. This phase specifically tests whether the system can consistently generate high-quality variant hypotheses before infrastructure is built. Re-run as a regression check whenever prompts or generation logic change.

Phase 3 evaluates market-expectations reasoning qualitatively only — rubric criterion 4 (did it correctly explain what is priced in?) is assessed against qualitative evidence: consensus narrative, valuation multiples, guidance, estimate revision direction, and transcript sentiment. The quantitative reverse DCF engine that supports this criterion is added in Phase 4. This is a known limitation of Phase 3, not a blocker.

**Phase 4 — Reverse DCF Expectations Engine**
Generate market-implied expectations ranges. Not price targets. Not buy/sell recommendations.

**Phase 5 — SEC & Transcript Parsing**
Robust ingestion pipelines extracting Business Overview, Risk Factors, MD&A, and earnings-call sections.

**Phase 6 — Database Layer**
Persist reports, scores, evidence, monitoring rules, and quality evaluations.

**Phase 7 — FastAPI API Layer**
Endpoints: generate memo, retrieve memo, historical reports, monitoring status.

**Phase 8 — Research Dashboard**
Display expectations, variant hypotheses, risks, evidence, and monitoring status.

**Phase 9 — Monitoring Engine**
Compare new transcripts against existing monitoring rules. The engine **may**:

- Automatically flag Green / Yellow / Red events.
- Propose changes to verdict, stance, or confidence.
- Propose updates to monitoring rules.

The engine **must not** automatically commit verdict, stance, confidence, or monitoring rule changes. Human review is required before the official memo state is updated. Auto-flagging is allowed; auto-deciding is not.

---

## Success Criteria

The project succeeds if it can:

1. Explain what the market expects.
2. Explain what the evidence suggests.
3. Identify variant perception.
4. Map risks clearly.
5. Generate verifiable evidence.
6. Explain thesis-breaking conditions.
7. Produce useful research recommendations.
8. Pass its own memo-quality rubric on companies the reviewer understands.

The project does not need to predict stock prices or beat the market automatically. It succeeds if it consistently helps the user reach better-informed decisions with substantially less manual research effort — while keeping final judgment and capital allocation human-controlled.
