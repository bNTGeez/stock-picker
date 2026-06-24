"""
Run the Phase 3 manual quality gate across your reviewed memos.

Usage (from repo root):
    python backend/scripts/run_gate.py

Steps:
1. Generate memos with generate_memo.py.
2. Read each memo JSON in backend/data/raw/.
3. Score each memo against the 8 rubric criteria below (1-5).
4. Add your scores to REVIEWS and run this script.
5. If it passes, proceed to Phase 4.
   If it fails, read the output, fix the prompt, regenerate, re-score.

Rubric criteria (score 1-5 each):
    1  real_variant_hypothesis  Did it identify the real variant hypothesis?
    2  obvious_risks            Did it miss obvious risks?
    3  confidence_calibration   Did it overstate confidence?
    4  priced_in_explanation    Did it correctly explain what is priced in?
                               (qualitative only until Phase 4)
    5  monitoring_rules         Were the monitoring rules useful and specific?
    6  evidence_support         Did the evidence actually support the conclusion?
    7  opposing_case            Did it fairly present the strongest opposing case?
    8  final_synthesis          Did the final synthesis explain why one argument
                               was better supported?

Score guide:
    5  Nailed it
    4  Good, minor gaps
    3  Acceptable, notable gaps
    2  Weak, meaningful problems
    1  Wrong or missing entirely
"""

from backend.models.schemas import ManualMemoQualityReview
from backend.services.memo_quality_gate import evaluate_memo_quality_gate


# ── REVIEWS — add one block per company ──────────────────────────────────────
#
# Copy the template below and fill in your honest scores and notes.
# memo_identifier should match the ticker and date you used when generating.

REVIEWS = [
    ManualMemoQualityReview.model_validate({
        "memo_identifier": "NOW-2026-06-19",
        "reviewer": "Benjamin",
        "criterion_scores": [
            {"criterion": "real_variant_hypothesis", "score": 4, "notes": "Correct: market prices as SaaS, variant is AI orchestration platform with consumption inflection. 13x entitlement expansion is real evidence. Minor gap: Microsoft Copilot competition not fully integrated."},
            {"criterion": "obvious_risks",           "score": 4, "notes": "Catches gross margin compression, Armis/Veza integration, deal complexity, hyperscaler competition. Missing explicit valuation/multiple compression risk."},
            {"criterion": "confidence_calibration",  "score": 4, "notes": "Medium confidence with Candidate verdict is right. Now Assist still sub-$1B vs $11B+ subscription base. Says 'initial validation' throughout."},
            {"criterion": "priced_in_explanation",   "score": 4, "notes": "Correctly identifies consensus treats it as mature SaaS vendor subject to seat compression. Solid qualitative framing without DCF."},
            {"criterion": "monitoring_rules",        "score": 5, "notes": "Excellent and specific: Now Assist ACV at or above $1B, subscription gross margin at or above 80%, subscription revenue below 17% triggers red."},
            {"criterion": "evidence_support",        "score": 4, "notes": "Evidence chain solid. 13x entitlement expansion, 70%+ upsell, 10x multi-product deals all from primary sources."},
            {"criterion": "opposing_case",           "score": 4, "notes": "Bear case covers gross margin, Armis/Veza, deal complexity, professional services loss. Could go harder on Microsoft Copilot and Salesforce Agentforce specifically."},
            {"criterion": "final_synthesis",         "score": 4, "notes": "Clear: exceptional fundamentals, variant has initial validation, but gross margin + acquisition + early-stage consumption = medium confidence. Well-reasoned."},
        ],
        "evidence_validation_status": "validated",
        "evidence_notes": "All quotes located in supplied 10-K and transcript excerpts.",
        "overall_notes": "Strongest of the three memos. Prompt fix needed: category weights and verbatim quote capitalisation (fixed for future runs).",
    }),

    ManualMemoQualityReview.model_validate({
        "memo_identifier": "FIVN-2026-06-19",
        "reviewer": "Benjamin",
        "criterion_scores": [
            {"criterion": "real_variant_hypothesis", "score": 4, "notes": "Better framing: now explicitly anchors variant to lagging (FY2025) vs leading (Q1 2026) indicator distinction. The DBR sequential inflection and AI growth acceleration are the right evidence to cite."},
            {"criterion": "obvious_risks",           "score": 4, "notes": "Now includes two RIFs as backward-looking cost pressure evidence. AI seat/TAM cannibalization addressed through competitive intensity and the fixed-revenue-commitment framing. Improvement from prior run."},
            {"criterion": "confidence_calibration",  "score": 4, "notes": "Research Further with appropriate confidence. Correctly notes market price unavailable and flags backlog reliance as a limitation."},
            {"criterion": "priced_in_explanation",   "score": 4, "notes": "Now uses specific numbers: 108% to 105% DBR decline, 14% to 10% revenue decel. Qualitative but grounded in the supplied consensus notes."},
            {"criterion": "monitoring_rules",        "score": 4, "notes": "Specific and measurable triggers tied to the variant thesis."},
            {"criterion": "evidence_support",        "score": 4, "notes": "Backward-looking evidence now primary (Q1 actuals, multi-year DBR trend, two RIFs). Forward guidance flagged as limitation in unknowns. Improvement from prior run."},
            {"criterion": "opposing_case",           "score": 4, "notes": "Bear case now includes RIF-based margin expansion critique and explicit backlog reliance flagging."},
            {"criterion": "final_synthesis",         "score": 4, "notes": "Grounded in lagging vs leading indicator framing. Honest about what is and is not confirmed."},
        ],
        "evidence_validation_status": "validated",
        "evidence_notes": "All quotes located in supplied 10-K and transcript excerpts.",
        "overall_notes": "Improved from prior run. Prompt fix (backward-looking evidence priority) worked. Average now 4.0.",
    }),

    ManualMemoQualityReview.model_validate({
        "memo_identifier": "GOOGL-2026-06-19",
        "reviewer": "Benjamin",
        "criterion_scores": [
            {"criterion": "real_variant_hypothesis", "score": 4, "notes": "Correct angle: CapEx treated as pure risk but Cloud margin already tripling and backlog nearly doubled. Self-funding inflection is right framing. Loses one point: can't establish expectations gap without market price data."},
            {"criterion": "obvious_risks",           "score": 5, "notes": "Excellent. Both antitrust cases with specifics, CapEx/depreciation trajectory with numbers, 70%+ revenue concentration, Wiz margin headwind, compute-constrained growth, $15.6B legal settlements, AI regulation. Nothing obvious missing."},
            {"criterion": "confidence_calibration",  "score": 5, "notes": "Perfect. Candidate with medium confidence, and recommended next step explicitly says to get market multiples before elevating conviction."},
            {"criterion": "priced_in_explanation",   "score": 4, "notes": "New run with consensus notes included. Memo correctly states market prices at ~$165 (~$2T cap), consensus expects 11-12% FY2026 revenue growth and 28-30% Cloud growth. Street treats Cloud as a long-dated option; CapEx risk as valuation discount not existential. Solid qualitative framing."},
            {"criterion": "monitoring_rules",        "score": 5, "notes": "Best of the three. Uses actual numbers: Cloud margin at or above 32.9%, backlog at 50%+ over 24 months, DOJ ad-tech remedies as red flag."},
            {"criterion": "evidence_support",        "score": 4, "notes": "PDF workflow — quotes manually spot-checked against Q1 2026 earnings call transcript. Key quotes confirmed verbatim: $462B backlog (Ashkenazi), $6.6B Cloud income tripling, 17.8% to 32.9% margin, 2027 CapEx increase. Evidence is real."},
            {"criterion": "opposing_case",           "score": 5, "notes": "Best bear case of the three. Explicitly acknowledges 2026-2027 CapEx depreciation hasn't hit P&L yet, making trailing margins look better than forward reality. Honest and sharp."},
            {"criterion": "final_synthesis",         "score": 4, "notes": "Clear: reported not merely guided operating leverage vs concrete unresolved legal and depreciation risks. Explains why Candidate not High Conviction."},
        ],
        "evidence_validation_status": "validated",
        "evidence_notes": "PDF workflow — quotes manually confirmed against Alphabet Q1 2026 earnings call transcript (Motley Fool). All sampled quotes verified verbatim.",
        "overall_notes": "Analytically strongest memo. Market context (price ~$165, consensus ~11% growth) now in prompt. Evidence manually validated. Passes on all criteria.",
    }),
    ManualMemoQualityReview.model_validate({
        "memo_identifier": "META-2026-06-20",
        "reviewer": "Benjamin",
        "criterion_scores": [
            {"criterion": "real_variant_hypothesis", "score": 4, "notes": "AI monetization flywheel (Lattice, GEM, adaptive ranking) grounded in Q1 actuals. Dual mechanism — expanding inventory and improving conversion — is specific and observable."},
            {"criterion": "obvious_risks",           "score": 5, "notes": "Catches CapEx escalation, EU DMA structural risk, AI monetization failure, youth litigation, macro, Reality Labs widening losses, geopolitical ad spend. Comprehensive."},
            {"criterion": "confidence_calibration",  "score": 4, "notes": "Candidate / Lean Bullish / Medium is right for a 33% revenue grower at ~22x with open-ended CapEx and EU regulatory overhang."},
            {"criterion": "priced_in_explanation",   "score": 4, "notes": "Correctly identifies consensus prices Meta as high-quality ad business at discount to growth due to CapEx overhang and EU risk. Specific about the debate."},
            {"criterion": "monitoring_rules",        "score": 4, "notes": "Price-per-ad above 10%, CapEx guidance unchanged, EU DMA adverse ruling as red flag. Tied to the variant thesis and measurable."},
            {"criterion": "evidence_support",        "score": 4, "notes": "PDF workflow — quotes spot-checked: $55.9B Q1 revenue, 12% price-per-ad growth, $200.97B FY2025 revenue, Reality Labs -$19.2B loss all confirmed in filings."},
            {"criterion": "opposing_case",           "score": 4, "notes": "Bear case is honest: CapEx open-ended with admitted escalation pattern, EU risk structural, AI monetization speculative. Rebuttal is fair."},
            {"criterion": "final_synthesis",         "score": 4, "notes": "Clear: dual AI mechanism observable in current financials, not dependent on speculative products. Cautiously constructive framing is well-reasoned."},
        ],
        "evidence_validation_status": "validated",
        "evidence_notes": "PDF workflow — key financial figures spot-checked against Meta Q1 2026 earnings call and FY2025 10-K. Revenue, ad pricing, and Reality Labs loss figures confirmed verbatim.",
        "overall_notes": "Strong memo. Risk section is the best of all five memos. Variant is grounded in observable data, not guidance.",
    }),

    ManualMemoQualityReview.model_validate({
        "memo_identifier": "COST-2026-06-20",
        "reviewer": "Benjamin",
        "criterion_scores": [
            {"criterion": "real_variant_hypothesis", "score": 4, "notes": "Three-part thesis (pharmacy/GLP-1, AI commerce, executive upgrades) is specific and grounded. Minor gap: each vector is individually modest and consensus may already partially know about them."},
            {"criterion": "obvious_risks",           "score": 4, "notes": "Catches valuation at 50x+, membership decel, SG&A inflation, tariff pass-through, Section 301 litigation, warehouse execution, geographic concentration. Solid coverage."},
            {"criterion": "confidence_calibration",  "score": 4, "notes": "Candidate / Lean Bullish / Medium is appropriate for a well-understood compounder with a stretched valuation. Not overclaiming."},
            {"criterion": "priced_in_explanation",   "score": 4, "notes": "Correctly identifies consensus prices ~50x for 6-8% comps with low variance. Specific about what the multiple implies and where the expectations gap sits."},
            {"criterion": "monitoring_rules",        "score": 4, "notes": "Membership growth re-acceleration above 5.5%, pharmacy comp threshold above 15%, renewal rate red flag below 91% — measurable and tied to the thesis."},
            {"criterion": "evidence_support",        "score": 4, "notes": "PDF workflow — quotes manually spot-checked. Pharmacy/GLP-1 quote confirmed in transcript. Specific dollar amounts and percentages match (membership fee $1.37B, exec members 41.2M, comps 9.8%). Evidence is real."},
            {"criterion": "opposing_case",           "score": 4, "notes": "Bear case is honest: 50x multiple, membership growth decel, variant not strongly differentiated from what consensus already knows. Rebuttal is fair."},
            {"criterion": "final_synthesis",         "score": 4, "notes": "Clear: exceptional business but variant is directionally plausible rather than high-conviction. Correctly says wait for pharmacy segment sizing before elevating conviction."},
        ],
        "evidence_validation_status": "validated",
        "evidence_notes": "PDF workflow — key quotes spot-checked against Costco Q3 FY2026 earnings transcript and FY2025 10-K. Pharmacy, membership fee, and comp figures confirmed verbatim.",
        "overall_notes": "Clean memo on a well-understood business. Variant is reasonable but consensus may already partially price in the growth vectors. Medium confidence appropriate.",
    }),
]


# ── RUN ───────────────────────────────────────────────────────────────────────

def main() -> None:
    result = evaluate_memo_quality_gate(REVIEWS)

    print(f"\n{'='*50}")
    print(f"Phase 3 Gate: {'PASSED' if result.passed else 'FAILED'}")
    print(f"Memos reviewed: {result.review_count} (need 5-10)")
    print(f"Aggregate average score: {result.aggregate_average_score:.2f} / 5.0")
    print(f"{'='*50}\n")

    if result.failing_reasons:
        print("Failing reasons:")
        for reason in result.failing_reasons:
            print(f"  - {reason}")
        print()

    for i, (review, review_result) in enumerate(
        zip(REVIEWS, result.review_results), start=1
    ):
        status = "PASS" if review_result.passed else "FAIL"
        print(f"  [{status}] {review.memo_identifier}  avg {review_result.average_score:.2f}")
        for reason in review_result.failing_reasons:
            print(f"         {reason}")

    print()
    if result.passed:
        print("Gate passed. You can proceed to Phase 4.")
    else:
        print("Gate failed. Fix the prompt, regenerate failing memos, re-score, rerun.")


if __name__ == "__main__":
    main()


