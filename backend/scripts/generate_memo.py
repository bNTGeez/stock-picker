"""

Generate an investment memo for one company.

Usage (from repo root):

    # Real LLM — requires ANTHROPIC_API_KEY
    ANTHROPIC_API_KEY=your-key python -m backend.scripts.generate_memo

    # Paste mode — prints the prompt so you can paste it into Claude.ai or ChatGPT,
    # then paste the JSON response back. No API key needed.
    python -m backend.scripts.generate_memo --paste

    # Stub mode — no API key needed, uses a pre-written example memo to test the pipeline
    python -m backend.scripts.generate_memo --stub

Edit the REQUEST section below before running.
The memo is saved to backend/data/raw/<TICKER>.json and printed to the terminal.
"""

import json
import os
import sys
from datetime import date
from pathlib import Path

from backend.services.manual_memo_generator import (
    CompanyMetadata,
    ManualMemoGenerator,
    ManualMemoRequest,
    ManualSourceExcerpt,
    parse_investment_memo_response,
    source_documents_from_request,
)


# ── LLM ──────────────────────────────────────────────────────────────────────

class _AnthropicLLM:
    def generate(self, prompt: str) -> str:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text


class _PasteLLM:
    """Saves the prompt to a file and waits for you to paste the JSON response back.

    The prompt file is saved to backend/data/raw/<TICKER>_prompt.txt.
    Upload that file directly to Claude.ai instead of copy-pasting.
    """

    def __init__(self, ticker: str) -> None:
        self._ticker = ticker

    def generate(self, prompt: str) -> str:
        prompt_path = (
            Path(__file__).resolve().parents[1]
            / "data" / "raw"
            / f"{self._ticker}_prompt.txt"
        )
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt)

        print(f"\nPrompt saved to: {prompt_path}")
        print("\nSteps:")
        print("  1. Upload that file to Claude.ai (attachment button).")
        print("  2. Ask: 'Respond with only the JSON memo, no markdown, no code fences.'")
        print("  3. In Claude.ai, click the copy button on the response.")
        print(f"  4. Save it to a file, e.g.:")
        print(f"       pbpaste > backend/data/raw/{self._ticker}_response.json")
        print(f"  5. Then run:")
        print(f"       python -m backend.scripts.generate_memo --response-file backend/data/raw/{self._ticker}_response.json")
        print("\nOr paste the JSON response below and press Enter twice (may not work for long responses):")
        lines = []
        while True:
            line = input()
            if line == "" and lines and lines[-1] == "":
                break
            lines.append(line)
        return "\n".join(lines).strip()


class _StubLLM:
    """Returns a pre-written example memo so you can run the pipeline without an API key.

    The quotes in this stub are copied exactly from the REQUEST source text below,
    so evidence validation passes. When you swap in a real company, switch to the
    real LLM — the stub is only for learning the workflow.
    """

    RESPONSE = json.dumps({
        "company_name": "Verano Software",
        "ticker": "VRNO",
        "memo_date": "2026-06-19",
        "research_verdict": "Research Further",
        "investment_stance": "Lean Bullish",
        "confidence": "Medium",
        "category_scores": {
            "business_quality": {
                "score": 74,
                "weight": 0.30,
                "rationale": "Net revenue retention of 118% and growing customer base indicate above-average business quality, offset by a history of net losses.",
            },
            "risk_profile": {
                "score": 52,
                "weight": 0.20,
                "rationale": "Customer concentration risk is elevated: the top 20 customers account for 34% of revenue. Competition from larger vendors adds to the risk profile.",
            },
            "expectations_gap": {
                "score": 72,
                "weight": 0.20,
                "rationale": "Consensus expects deceleration to 18% revenue growth. Bookings growth of 40% and NRR of 118% both point to a stronger demand environment than the market appears to be pricing in.",
            },
            "variant_perception": {
                "score": 68,
                "weight": 0.15,
                "rationale": "The variant hypothesis — that demand is accelerating rather than decelerating — is supported by bookings and NRR evidence but is not yet confirmed by a full revenue print.",
            },
            "valuation": {
                "score": 58,
                "weight": 0.10,
                "rationale": "Valuation range is contingent on whether growth acceleration is sustained. Without reverse DCF work, the range is qualitative.",
            },
            "catalyst": {
                "score": 50,
                "weight": 0.05,
                "rationale": "FCF turning positive and a strong bookings quarter are near-term catalysts, but the next earnings print is the key forcing event.",
            },
        },
        "market_expectations": "Consensus is pricing in a deceleration from 26% to 18% revenue growth in FY2026, with FCF margins in the low single digits. The implied assumption is that net revenue retention normalises toward 110% and bookings growth slows as the market matures.",
        "observations": {
            "observations": [
                {
                    "statement": "Net revenue retention of 118% exceeds the consensus normalisation assumption.",
                    "supporting_evidence": [
                        {
                            "source_type": "10-K Item 1",
                            "source_tier": 1,
                            "source_id": "Verano FY2025 10-K Item 1",
                            "quote": "Net revenue retention was 118% for fiscal 2025.",
                        }
                    ],
                },
                {
                    "statement": "Q4 bookings grew 40% year-over-year, above the pace implied by 18% revenue growth consensus.",
                    "supporting_evidence": [
                        {
                            "source_type": "earnings_transcript",
                            "source_tier": 2,
                            "source_id": "Verano Q4 2025 Earnings Call",
                            "quote": "Bookings in Q4 were up 40% year over year.",
                        }
                    ],
                },
                {
                    "statement": "Free cash flow turned positive in Q4 ahead of street timing expectations.",
                    "supporting_evidence": [
                        {
                            "source_type": "earnings_transcript",
                            "source_tier": 2,
                            "source_id": "Verano Q4 2025 Earnings Call",
                            "quote": "Free cash flow turned positive for the first time in Q4 at $3.2 million.",
                        }
                    ],
                },
            ]
        },
        "variant_hypothesis": "Revenue growth in FY2026 likely exceeds the 18% consensus estimate because bookings momentum and net revenue retention both point to a stronger demand environment than the market is pricing in.",
        "why_consensus_may_be_wrong": "Consensus appears to be anchoring to historical SaaS deceleration patterns without sufficiently weighting the 40% bookings growth and 118% NRR signals, which together suggest demand is accelerating rather than normalising.",
        "adversarial_research": {
            "bull_case": "40% bookings growth and 118% NRR drive revenue acceleration to 25%+, with FCF margin expanding faster than consensus expects as operating leverage kicks in.",
            "bear_case": "Customer concentration — top 20 customers at 34% of revenue — creates fragility. One or two large churn events could sharply reverse the growth narrative and send NRR below 100%.",
            "key_disagreement": "Whether bookings growth and NRR durability can offset concentration risk and competition from larger vendors.",
            "evidence_for_variant_view": [
                {
                    "source_type": "earnings_transcript",
                    "source_tier": 2,
                    "source_id": "Verano Q4 2025 Earnings Call",
                    "quote": "Bookings in Q4 were up 40% year over year. We're not seeing demand weakness.",
                },
                {
                    "source_type": "10-K Item 1",
                    "source_tier": 1,
                    "source_id": "Verano FY2025 10-K Item 1",
                    "quote": "Net revenue retention was 118% for fiscal 2025.",
                },
            ],
            "evidence_against_variant_view": [
                {
                    "source_type": "10-K Item 1",
                    "source_tier": 1,
                    "source_id": "Verano FY2025 10-K Item 1",
                    "quote": "A small number of customers represent a significant portion of revenue; the top 20 customers accounted for 34% of total revenue in fiscal 2025.",
                },
                {
                    "source_type": "10-K Item 1A",
                    "source_tier": 1,
                    "source_id": "Verano FY2025 10-K Item 1A",
                    "quote": "We face significant competition from larger, more established vendors.",
                },
            ],
            "rebuttal": "NRR of 118% is a trailing indicator of actual customer expansion behaviour, not management guidance. A 1,840-customer base with 34% in the top 20 means roughly 20 customers averaging 1.7% of revenue each — single-customer churn is painful but not catastrophic.",
            "disconfirming_evidence": [
                "NRR falling below 110% in the next earnings disclosure.",
                "Q1 bookings growth decelerating below 20%.",
                "Loss of any top-5 customer.",
            ],
            "final_synthesis": "The variant view is better supported by the evidence than the consensus deceleration assumption. NRR of 118% is a hard data point, not a forward estimate, and 40% bookings growth is a leading indicator. The bear case is real but requires a specific churn event to materialise. Watchlist with a lean bullish stance is appropriate until the next earnings print confirms or denies the bookings trend.",
        },
        "unknowns": {
            "unknowns": [
                "Segment-level NRR is not disclosed — we cannot tell which verticals drive retention.",
                "No disclosure of average contract value or seat counts, making bookings quality hard to assess.",
                "Consensus margin assumptions are not broken out by line item.",
            ]
        },
        "top_risks": [
            "Customer concentration — top 20 customers at 34% of revenue.",
            "Competition from larger, more established vendors.",
            "History of net losses; profitability not guaranteed.",
            "Multiple compression if growth decelerates.",
        ],
        "valuation_range": {
            "bear": {
                "label": "Bear",
                "assumptions": [
                    "NRR falls below 110%.",
                    "Bookings growth decelerates to 10-15%.",
                ],
                "implied_outcome": "Revenue growth falls back to 12-14%, FCF margins remain thin, multiple compresses.",
                "supporting_evidence": [
                    {
                        "source_type": "10-K Item 1A",
                        "source_tier": 1,
                        "source_id": "Verano FY2025 10-K Item 1A",
                        "quote": "If net revenue retention declines materially, our business could be adversely affected.",
                    }
                ],
            },
            "base": {
                "label": "Base",
                "assumptions": [
                    "NRR holds at 115-118%.",
                    "Bookings growth moderates to 25-30%.",
                ],
                "implied_outcome": "Revenue growth of 22-25% with FCF margins expanding to 6-8%.",
                "supporting_evidence": [
                    {
                        "source_type": "10-K Item 1",
                        "source_tier": 1,
                        "source_id": "Verano FY2025 10-K Item 1",
                        "quote": "Net revenue retention was 118% for fiscal 2025.",
                    }
                ],
            },
            "bull": {
                "label": "Bull",
                "assumptions": [
                    "NRR expands above 120%.",
                    "Bookings growth sustains at 35-40%.",
                    "FCF margin expands to 10%+.",
                ],
                "implied_outcome": "Revenue re-accelerates, multiple expands on FCF inflection.",
                "supporting_evidence": [
                    {
                        "source_type": "earnings_transcript",
                        "source_tier": 2,
                        "source_id": "Verano Q4 2025 Earnings Call",
                        "quote": "We exited fiscal 2025 with our strongest pipeline in company history.",
                    }
                ],
            },
        },
        "reverse_dcf_expectations": None,
        "monitoring_rules": {
            "green_flags": [
                {
                    "trigger": "NRR remains at or above 115% in the next earnings disclosure.",
                    "rationale": "Confirms the retention durability thesis.",
                    "evidence": [
                        {
                            "source_type": "10-K Item 1",
                            "source_tier": 1,
                            "source_id": "Verano FY2025 10-K Item 1",
                            "quote": "Net revenue retention was 118% for fiscal 2025.",
                        }
                    ],
                },
                {
                    "trigger": "Q1 bookings growth reported above 30%.",
                    "rationale": "Confirms demand acceleration is not a one-quarter event.",
                    "evidence": [
                        {
                            "source_type": "earnings_transcript",
                            "source_tier": 2,
                            "source_id": "Verano Q4 2025 Earnings Call",
                            "quote": "Bookings in Q4 were up 40% year over year.",
                        }
                    ],
                },
            ],
            "yellow_flags": [
                {
                    "trigger": "NRR slips to 108-114%.",
                    "rationale": "Retention still positive but thesis durability needs monitoring.",
                    "evidence": [],
                },
                {
                    "trigger": "Customer concentration rises above 40% for the top 20.",
                    "rationale": "Increasing concentration raises churn fragility.",
                    "evidence": [],
                },
            ],
            "red_flags": [
                {
                    "trigger": "NRR falls below 105%.",
                    "rationale": "Materially damages the retention durability variant hypothesis.",
                    "evidence": [],
                },
                {
                    "trigger": "Loss of any top-5 customer disclosed.",
                    "rationale": "Directly tests concentration risk and would require thesis revision.",
                    "evidence": [],
                },
            ],
        },
        "recommended_next_step": "Research further before any capital allocation decision. Priority actions: obtain segment-level NRR data, model the concentration scenario, and wait for Q1 bookings confirmation.",
    })

    def generate(self, prompt: str) -> str:
        return self.RESPONSE


# ── REQUESTS — one entry per company ─────────────────────────────────────────
#
# Usage:
#   python -m backend.scripts.generate_memo --ticker NOW --paste
#   python -m backend.scripts.generate_memo --ticker AAPL --paste
#
# Add a new company by copying the boilerplate block at the bottom of this dict.

REQUESTS: dict[str, ManualMemoRequest] = {}


# ── ServiceNow (NOW) ──────────────────────────────────────────────────────────

REQUESTS["NOW"] = ManualMemoRequest(
    company=CompanyMetadata(
        company_name="ServiceNow",
        ticker="NOW",
        memo_date=date.today(),
    ),

    # Paste excerpts from ServiceNow's FY2025 10-K (filed early 2026).
    # Good sections: Item 1 (Business), Item 1A (Risk Factors), Item 7 (MD&A).
    # Source: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=NOW&type=10-K
    ten_k_excerpts=[
        ManualSourceExcerpt(
            source="ServiceNow FY2025 10-K Item 1",
            text="""
            The ServiceNow AI Platform (our “Platform”) connects people, processes and data to break down silos and
simplify complex business processes, increasing flexibility, scalability and extensibility. Our one platform
architecture provides the foundation for organizations to seamlessly integrate AI, data, and workflows and create
intelligent processes across their enterprise.
AI. Our Platform’s integrated AI offering, Now Assist, empowers organizations to boost productivity by providing a
range of AI tools. These tools operate autonomously with human oversight and adhere to predefined guardrails.
Organizations can select the tools that best align with their unique AI transformation needs. To illustrate,
organizations can choose to leverage ServiceNow’s language models or integrate third-party or proprietary
models. Depending on the selected model, they can process different types of data, such as text, images, audio
and video. They can also trust that the selected models are tested to confirm they will perform as intended on our
Platform, as all integrated models are regularly evaluated on Platform-representative data. Additionally,
organizations can choose to rapidly deploy thousands of out-of-the-box ServiceNow AI agents, integrate AI agents
built into third-party applications, or create custom AI agents on our Platform using natural language. These
options allow for flexible AI agent workflow orchestration in a wide range of use cases, making AI agents
accessible to users with varying technical expertise. AI agents developed using our solutions follow a human-inthe-loop governance model. This allows developers to retain control of application changes while benefiting from
AI assistance. We also offer governance tools designed to help manage these AI agents and other AI-powered
products. Our AI governance tools include integrated monitoring and guardrails, as well as dataset creation
management, benchmarking and performance analytics capabilities. They offer organizations greater visibility into
their AI adoption, usage and performance. These tools provide organizations confidence that they are building,
testing and deploying AI use cases and applications responsibly as they operationalize their AI strategy.
Data. Our Platform’s single data fabric and integrated data layer, enabled by our Workflow Data Fabric and
RaptorDB products, supports organizations’ operationalization of their AI strategy with speed, scale and security.
Our data fabric’s architecture also provides our Platform flexibility to create intuitive, efficient and seamless
workflows aligned with business needs. For example, our Platform’s data fabric can connect to external data
sources in real-time without moving or copying data from its source and map those connections to its single data
model, which creates a seamless user experience. AI-enabled tools for the data layer can also help deliver
precise, context-aware insights by linking people, processes and systems. By connecting a wide variety of data
and systems, our Platform enables a single process flow across people and functions. These capabilities allow
the front, middle and back offices to coordinate and address end user requests quickly and effectively.
Workflows. Through its orchestration capabilities, our Platform manages complex, cross-functional workflows
end-to-end. For example, an organization’s entire employee onboarding workflow, which spans across both
internal and external functions, can be managed by our Platform. AI agents can autonomously trigger information
technology (“IT”) provisioning, payroll setup, compliance checks and facilities access – coordinating tasks,
monitoring progress and resolving exceptions without human intervention, if desired. Because our AI agents can
access required information and understand the context of requests in a single environment, employees can
complete their onboarding without contacting multiple departments. Additionally, with our acquisition of
Moveworks, Inc. we have strengthened our enterprise workflow automation on our Platform by integrating
advanced enterprise search and front-end virtual agent technology. The advanced machine learning,
conversational interface, natural language comprehension and broad integration capabilities of this technology
help organizations and their employees handle service requests automatically, retrieve information quickly using
AI, and complete tasks across diverse business applications, enhancing overall workflow experience.
Together, these AI, data and workflow capabilities support our broad portfolio of products on our Platform.
            """,
        ),
        ManualSourceExcerpt(
            source="ServiceNow FY2025 10-K Item 1A",
            text="""

            Risk Factors Summary
This summary provides an overview of the risks we face and should not be considered a substitute for the more
fulsome risk factors discussed immediately following this summary.
Risks Related to Our Ability to Grow Our Business
• Laws, regulations and customer expectations regarding the use, storage and movement of data may restrict
our ability to continue to optimize our platform.
• A failure to innovate and adapt how we offer our products in response to rapidly evolving technological changes
and in the midst of an intensely competitive market may harm our competitive position and business prospects.
• We may not successfully increase our penetration of international markets or manage risks associated with
foreign markets.
• Incorporating AI technology into our offerings may result in operational, legal, regulatory, ethical and other
challenges.
• We rely on our network of partners for an increasing portion of our revenues, and if these partners fail to
perform, our business may be harmed.
• Doing business with the public sector and heavily-regulated entities subjects us to risks related to government
procurement processes, regulations and contracting requirements.
• If we fail to comply with applicable anti-corruption and anti-bribery laws, export control laws, economic and
trade sanctions laws, or other global trade laws, we could be subject to penalties and civil and/or criminal
sanctions and our business could be materially adversely affected.
• Our customer deals are becoming more complex, which tend to involve longer, more expensive sales cycles,
increased pricing pressure, and implementation and configuration challenges.
• As we acquire or invest in companies and technologies, we may not realize the expected business or financial
benefits and the acquisitions and investments may divert our management’s attention and result in additional
shareholder dilution or costs.
Risks Related to the Operation of Our Business
• Actual or perceived cybersecurity events experienced by us or our third-party service providers may create the
perception that our platform is not secure, and we may lose customers or incur significant liabilities.
• We may lose key members of our management team or qualified employees or may not be able to attract and
retain employees we need.
Part I
22
• Delays in the release of, or actual or perceived defects in, our products may slow the adoption of our latest
technologies, reduce our ability to efficiently provide services, decrease customer satisfaction and adversely
impact future product sales.
• Disruptions or defects in our services could damage our customers’ businesses, subject us to substantial
liability and harm our business.
• Delays in improving our information systems and processes could interfere with our ability to support our
existing and growing base of customers and employees as we scale.
• We may not be able to protect or enforce our IP rights.
• Our use of open-source software could harm our ability to sell our products and services and subject us to
possible litigation.
• Various factors, including our customers’ business, integration, migration, compliance and security
requirements or errors by us, our partners or our customers, may cause implementations of our products to be
delayed, inefficient or otherwise unsuccessful.
• Our failure or perceived failure to achieve our corporate sustainability goals or maintain corporate sustainability
practices that meet evolving stakeholder expectations could adversely affect us.
• We may face natural disasters, including climate change, and other events beyond our control.
Risks Related to the Financial Performance or Financial Position of Our Business
• Because we generally recognize revenues from our subscription services over the subscription term, a
decrease in new subscriptions or renewals may not be immediately reflected in our operating results.
• As our business grows, we expect our revenue growth rate to decline over the long term.
• Changes in our effective tax rate or disallowance of our tax positions may adversely affect our business.
• We may be adversely affected by our debt service obligations.
Risks Related to General Economic Conditions
• Our industry and business may be harmed by global economic conditions.
• We may be harmed by foreign currency exchange rate fluctuations.
Risks Related to Ownership of Our Common Stock
• Our stock price is likely to continue to be volatile.
• Provisions in our governing documents or Delaware law might discourage

            Incorporating AI technology into our offerings may result in operational, legal, regulatory, ethical and
other challenges.

            A failure to innovate and adapt how we offer our products in response to rapidly evolving technological
changes and in the midst of an intensely competitive market may harm our competitive position and
business prospects.

            We may not successfully increase our penetration of international markets or manage risks associated
with foreign markets.

            Our customer deals are becoming more complex, which tend to involve longer, more expensive sales
cycles, increased pricing pressure, and implementation and configuration challenges.
            """,
        ),
        ManualSourceExcerpt(
            source="ServiceNow FY2025 10-K Item 7",
            text="""
            Subscription revenues increased by $2.2 billion for the year ended December 31, 2025, compared to the prior
year, primarily driven by increased purchases by new and existing customers. Included in subscription revenues is
$492 million and $409 million of revenues recognized upfront from the delivery of software associated with selfhosted offerings during the years ended December 31, 2025 and 2024, respectively.
We expect subscription revenues for the year ending December 31, 2026 to increase in absolute dollars and
remain relatively flat as a percentage of revenue as we continue to add new customers and existing customers
increase their usage of our products compared to the year ended December 31, 2025.
Our expectations for revenues, cost of revenues and operating expenses for the year ending December 31,
2026 are based on the 31-day average of foreign exchange rates for December 31, 2025.
Professional services and other revenues increased by $57 million for the year ended December 31, 2025,
compared to the prior year, due to an increase in services and trainings provided to new and existing customers.
We expect professional services and other revenues for the year ending December 31, 2026 to increase in
absolute dollars and remain relatively flat as a percentage of revenue compared to the year ended December 31,
2025.

        Cost of subscription revenues increased by $627 million for the year ended December 31, 2025, compared to the
prior year, primarily due to increased headcount and increased costs to support the growth of our subscription
offerings including costs to support customers in regulated markets. Personnel-related costs, including
stock-based compensation and overhead expenses, increased by $307 million as compared to the prior year.
Depreciation expense related to infrastructure hardware equipment and expenses associated with software,
maintenance, third-party cloud services and other costs, which together support the expansion of data center
capacity increased by $277 million for the year ended December 31, 2025, as compared to the prior year.
We expect our cost of subscription revenues for the year ending December 31, 2026 to increase in absolute
dollars as we provide subscription services to more customers and increase usage within our customer instances
and increase slightly as a percentage of revenue compared to the year ended December 31, 2025. We will
continue to incur incremental costs to attract customers in regulated markets by adopting public cloud offerings as
well as increased support for customers impacted by new and evolving data residency requirements. To the
extent future acquisitions are consummated, our cost of subscription revenues may increase due to additional
non-cash charges associated with the amortization of intangible assets acquired.
Our subscription gross profit percentage was 80% and 82% for the years ended December 31, 2025 and 2024,
respectively. We expect our subscription gross profit percentage to decrease slightly for the year
ending December 31, 2026 compared to the year ended December 31, 2025, primarily due to the ongoing growth
of our third-party cloud services usage and incremental amortization expense of intangible assets acquired
through acquisitions completed during the year ended December 31, 2025.
Cost of professional services and other revenues increased by $69 million for the year ended December 31, 2025
as compared to the prior year, primarily driven by an increase in partner ecosystem spend to further help
accelerate customer value realization.
Our professional services and other gross loss percentage was 5% for the year ended December 31, 2025,
compared to 2% in the prior year, and was primarily driven by partner ecosystem spend to further help accelerate
customer value realization increasing at a faster rate than revenue. We expect our professional services and other
gross loss percentage to increase for the year ending December 31, 2026 compared to the year ended December
31, 2025. Sales and marketing expenses increased by $534 million for the year ended December 31, 2025, compared to
the prior year, primarily due to increased headcount resulting in an increase in personnel-related costs including
stock-based compensation and overhead expenses of $332 million, compared to the prior year. Amortization
expenses associated with deferred commissions increased by $67 million, compared to the prior year, due to an
increase in contracts with new customers, expansion and renewal contracts. Other sales and marketing program
expenses, which include branding, costs associated with purchasing advertising, marketing events and market
data, increased by $68 million compared to the prior year, primarily due to increased program costs and travel
costs for our annual Knowledge user conference.
We expect sales and marketing expenses for the year ending December 31, 2026 to increase in absolute dollars
and to decrease slightly as a percentage of revenue compared to the year ended December 31, 2025, as we
continue to see leverage from increased sales productivity and marketing efficiencies. Research and development expenses (“R&D”) increased by $417 million during the year ended December 31,
2025, compared to the prior year, primarily due to increased headcount resulting in an increase in
personnel-related costs including stock-based compensation and overhead expenses of $383 million compared to
the prior year.
We expect R&D expenses for the year ending December 31, 2026 to increase in absolute dollars but remain
relatively flat as a percentage of revenue compared to the year ended December 31, 2025, as we continue to
improve the existing functionality of our services, develop new applications to fill market needs and enhance our
core platform. General and administrative expenses (“G&A”) increased by $187 million during the year ended December 31,
2025, compared to the prior year, primarily due to increased headcount resulting in an increase in
personnel-related costs including stock-based compensation of $39 million and an increase in outside services of
$78 million. The remaining increase was primarily due to an increase in contract termination costs of $37 million
and impairment of assets of $30 million for the year ended December 31, 2025, compared to the prior year.
We expect G&A expenses for the year ending December 31, 2026 to decrease in absolute dollars and to
decrease slightly as a percentage of revenue compared to the year ended December 31, 2025, as we continue to
see leverage from continued G&A productivity. Stock-based compensation increased by $209 million during the year ended December 31, 2025, compared to
the prior year, primarily due to additional grants to current and new employees.
Stock-based compensation is inherently difficult to forecast due to fluctuations in our stock price. Based upon our
stock price as of December 31, 2025, we expect stock-based compensation to continue to increase in absolute
dollars for the year ending December 31, 2026 as we continue to issue stock-based awards to our employees but
remain relatively flat as a percentage of revenue compared to the year ended December 31, 2025. We expect
stock-based compensation as a percentage of revenue to decline over time as we continue to grow. 

We generate cash inflows from operations primarily from selling subscription services which are generally paid in
advance of provisioning services, and expend cash outflows to develop new services and core technologies that
further enhance the Platform, engage our customers and enhance their experience, and enable and transform our
business operations. Subscription services arrangements typically have a three-year duration, and we have
experienced a renewal rate of 98% for each of the years ended December 31, 2025, 2024 and 2023. Cash
outflows from operations are principally comprised of the salaries, bonuses, commissions, and benefits for our
workforce, licenses and services arrangements, including cloud services, that are integral to our business
operations and data centers and operating lease arrangements that underlie our facilities. We have generated
positive operating cash flows for more than ten years as we continue to grow our business in pursuit of our
business strategy, and we expect to grow our business and generate positive cash flows from operations during
2026. When assessing sources of liquidity, we also include cash and cash equivalents, marketable securities and
long-term marketable securities totaling $10.1 billion as of December 31, 2025.
Our capital requirements are principally comprised of capital expenditures to support data center capacity
expansion, non-contract workforce salaries, bonuses, commissions, and benefits and, to a lesser extent,
cancellable and non-cancellable licenses, operating leases and services arrangements that are integral to our
business operations. We also acquire technology and businesses to expand our service offerings and
functionality. Our capital expenditures are under cancellable and non-cancellable arrangements. Non-cancellable
purchase commitments for business operations total $7.9 billion as of December 31, 2025, which are due
primarily over the next five years. Operating lease obligations totaling $1.1 billion are principally associated with
leased facilities and have varying maturities with $687 million due over the next five years.
Our supply chain finance (“SCF”) program provides suppliers with the opportunity to sell their receivables due
from us to a global financial institution. A supplier’s election to receive early payment at a discounted amount from
the financial institution does not change the amount that we must remit to the financial institution on our payment
date, which is generally 90 days from the invoice date. As of December 31, 2025, our outstanding payment
Part II
2025 Annual Report 61
obligations to suppliers participating in the SCF program totaled $87 million. These obligations are included in
accounts payable in our consolidated balance sheets, and all activity related to these obligations is presented
within operating activities in the consolidated statements of cash flows.
We may repurchase our shares of common stock through open market purchases, accelerated share repurchase
transactions, privately negotiated transactions or by other means, with the objective to return value to our
stockholders and manage the dilution from future employee equity grants and employee stock purchase
programs. In May 2023, our board of directors authorized a program to repurchase up to $1.5 billion of our
common stock and authorized an additional $3.0 billion in repurchases under the program in January 2025.
During the year ended December 31, 2025, the Company repurchased 10.3 million shares of our common stock
for $1.8 billion. All repurchases were made in open market transactions. Repurchases of common stock are
recognized as treasury stock and held for future issuance. As of December 31, 2025, approximately $1.4 billion of
the authorized amount under the share repurchase program remained available for future repurchases. In
January 2026, our board of directors authorized an additional $5.0 billion in repurchases under the Share
Repurchase Program.
We have also issued long-term debt to finance our business. In August 2020, we issued 1.40% fixed rate ten-year
notes with an aggregate principal amount of $1.5 billion due on September 1, 2030 (the “2030 Notes”).
Our operating cash flows, together with our other sources of liquidity, are available to service our liabilities as well
as our cancellable and non-cancellable arrangements. We anticipate cash flows generated from operations, cash,
cash equivalents, marketable securities and long-term marketable securities will be sufficient to meet our liquidity
needs for at least the next 12 months, although we do expect to seek additional debt financing to fund our
acquisition of Armis Security Ltd. discussed in Note 5 “Business Combinations” in the notes to our consolidated
financial statements. As we look beyond the next 12 months, we seek to continue to grow cash flows necessary to
fund our operations and grow our business. If we require additional capital resources, we may seek to finance our
operations from the current funds available or additional equity or debt financing.

We have historically seen higher collections in the quarter ended March 31 due to seasonality in timing of entering
into customer contracts, which is significantly higher in the quarter ended December 31. Additionally, we have
historically seen higher disbursements in the quarters ended March 31 and September 30 due to payouts under
our annual commission plans, purchases under our employee stock purchase plan, payouts under our bonus
plans and coupon payments related to our 2030 Notes.
Non-GAAP consolidated income from operations. Non-GAAP consolidated income from operations is identified as
an additional measure of profit or loss. This non-GAAP measure is used by the chief operating decision maker to
allocate resources and assess performance. We define non-GAAP consolidated income from operations as
income from operations excluding certain non-cash or non-recurring items, including stock-based compensation
expense, amortization of purchased intangibles, legal settlements, impairment of assets, severance costs,
contract termination costs and business combination and other related costs including compensation expense.
We believe these adjustments provide useful supplemental information to investors and facilitate the analysis of
our operating results and comparison of those results across reporting periods. The following table shows the
reconciliation of our reported consolidated income from operations to non-GAAP consolidated income
from operations. Renewal rate. We calculate our renewal rate by subtracting our attrition rate from 100%. Our attrition rate for a
period is equal to the ACV from customers lost during the period, divided by the sum of (i) the total ACV from all
customers that renewed during the period, excluding changes in price or users, and (ii) the total ACV from all
customers lost during the period. Accordingly, our renewal rate is calculated based on ACV and is not based on
the number of customers that have renewed. Further, our renewal rate does not reflect increased or decreased
purchases from our customers to the extent such customers are not lost customers or lapsed renewals. A lost
customer is a customer that did not renew an expiring contract and that, in our judgment, will not be renewed.
Typically, a customer that reduces its subscription upon renewal is not considered a lost customer. However, in
instances where the subscription decrease represents the majority of the customer’s ACV, we may deem the
renewal as a lost customer. For our renewal rate calculation, we define a customer as an entity with a separate
production instance of our service and an active subscription contract as of the measurement date, instead of an
entity with a unique GULT or DUNS number. We adjust our renewal rate for acquisitions, consolidations and other
customer events that cause the merging of two or more accounts occurring at the time of renewal. Our renewal
rate was 98% for each of the years ended December 31, 2025, 2024 and 2023. As our renewal rate is impacted
by the timing of renewals, which could occur in advance of, or subsequent to the original contract end date,
period-to-period comparison of renewal rates may not be meaningful.

Cost of subscription revenues increased by $627 million for the year ended December 31, 2025, compared to the
prior year, primarily due to increased headcount and increased costs to support the growth of our subscription
offerings including costs to support customers in regulated markets. Personnel-related costs, including
stock-based compensation and overhead expenses, increased by $307 million as compared to the prior year.
Depreciation expense related to infrastructure hardware equipment and expenses associated with software,
maintenance, third-party cloud services and other costs, which together support the expansion of data center
capacity increased by $277 million for the year ended December 31, 2025, as compared to the prior year.
We expect our cost of subscription revenues for the year ending December 31, 2026 to increase in absolute
dollars as we provide subscription services to more customers and increase usage within our customer instances
and increase slightly as a percentage of revenue compared to the year ended December 31, 2025. We will
continue to incur incremental costs to attract customers in regulated markets by adopting public cloud offerings as
well as increased support for customers impacted by new and evolving data residency requirements. To the
extent future acquisitions are consummated, our cost of subscription revenues may increase due to additional
non-cash charges associated with the amortization of intangible assets acquired.
Our subscription gross profit percentage was 80% and 82% for the years ended December 31, 2025 and 2024,
respectively. We expect our subscription gross profit percentage to decrease slightly for the year
ending December 31, 2026 compared to the year ended December 31, 2025, primarily due to the ongoing growth
of our third-party cloud services usage and incremental amortization expense of intangible assets acquired
through acquisitions completed during the year ended December 31, 2025.
Cost of professional services and other revenues increased by $69 million for the year ended December 31, 2025
as compared to the prior year, primarily driven by an increase in partner ecosystem spend to further help
accelerate customer value realization.
Our professional services and other gross loss percentage was 5% for the year ended December 31, 2025,
compared to 2% in the prior year, and was primarily driven by partner ecosystem spend to further help accelerate
customer value realization increasing at a faster rate than revenue. We expect our professional services and other
gross loss percentage to increase for the year ending December 31, 2026 compared to the year ended December
31, 2025. Sales and marketing expenses increased by $534 million for the year ended December 31, 2025, compared to
the prior year, primarily due to increased headcount resulting in an increase in personnel-related costs including
stock-based compensation and overhead expenses of $332 million, compared to the prior year. Amortization
expenses associated with deferred commissions increased by $67 million, compared to the prior year, due to an
increase in contracts with new customers, expansion and renewal contracts. Other sales and marketing program
expenses, which include branding, costs associated with purchasing advertising, marketing events and market
data, increased by $68 million compared to the prior year, primarily due to increased program costs and travel
costs for our annual Knowledge user conference.
We expect sales and marketing expenses for the year ending December 31, 2026 to increase in absolute dollars
and to decrease slightly as a percentage of revenue compared to the year ended December 31, 2025, as we
continue to see leverage from increased sales productivity and marketing efficiencies. Research and development expenses (“R&D”) increased by $417 million during the year ended December 31,
2025, compared to the prior year, primarily due to increased headcount resulting in an increase in
personnel-related costs including stock-based compensation and overhead expenses of $383 million compared to
the prior year.
We expect R&D expenses for the year ending December 31, 2026 to increase in absolute dollars but remain
relatively flat as a percentage of revenue compared to the year ended December 31, 2025, as we continue to
improve the existing functionality of our services, develop new applications to fill market needs and enhance our
core platform.
            """,
        ),
    ],

    # Paste excerpts from the most recent earnings call.
    # Q1 2026 would be the most recent as of June 2026.
    # Good sources: Motley Fool, Seeking Alpha, or investor.servicenow.com
    transcript_excerpts=[
        ManualSourceExcerpt(
            source="ServiceNow Q4 2025 Earnings Call",
            text="""
            Full Conference Call Transcript
Darren Yip: Good afternoon, and thank you for joining ServiceNow's fourth quarter 2025 earnings conference call. Joining me are Bill McDermott, Chairman and Chief Executive Officer, Gina Mastantuono, our President and Chief Financial Officer, and Amit Zavery, President, Chief Product Officer, and Chief Operating Officer. During today's call, we will review our fourth quarter 2025 results and discuss our guidance for the first quarter and full year 2026. Before we get started, we want to emphasize that the information discussed on this call, including our guidance, is based on information as of today and contains forward-looking statements that involve risks, uncertainties, and assumptions. We undertake no duty or obligation to update such statements as a result of new information or future events.

Please refer to today's earnings press release and our SEC filings, including our most recent 10-Q and 10-Ks, for factors that may cause actual results to differ materially from our forward-looking statements. I would also like to point out that we present non-GAAP measures in addition to, and not as a substitute for, financial measures calculated in accordance with GAAP. Unless otherwise noted, all financial measures and related growth rates we discuss today are non-GAAP except for revenues, remaining performance obligations, or RPO, current RPO, and cash and investments. To see the reconciliation between these non-GAAP and GAAP measures, please refer to today's earnings press release and investor presentation, which are both posted on our website at investors.servicenow.com.

A replay of today's call will also be posted on our website. With that, I'll turn the call over to Bill. Thank you very much, and good afternoon to everyone joining today's call. As you might imagine, I've been waiting for this extraordinarily exciting moment since 12/31/2025.

Bill McDermott: There seems to be speculation everywhere these days, so let's take it all head-on. Here are the facts. Our Q4 results beat expectations handily, just like we have consistently for years now. Overall, Q4 NNACV growth accelerated. Our subscription revenue growth was 21%, both quarter over quarter and year over year in Q4, 19.5% in constant currency, 1.5 points above the high end of our guidance. Contribution from Moveworks was de minimis. Our CRPO growth was 25%, 21% in constant currency, two points above our guidance, including a 1% contribution from Moveworks. Operating margin was 31%, one point above our guidance. Full year '25 free cash flow margin was 35%, one point above our already raised guidance.

We had 244 deals greater than $1,000,000 in NNACV. We had seven deals greater than $10,000,000 in NNACV. And CRM NNACV growth accelerated quarter over quarter to close its largest quarter in history. RaptorDB Pro more than tripled NNACV year on year in Q4, including $131,000,000 plus deals. Workflow Data Fabric was in 16 of our top 20 Q4 deals, and we've seen attach rates increase in every quarter of 2025. All of the workflow businesses were very strong in Q4. Gina will take you through the breakdown on all the metrics. The speculation of AI will eat software companies is out there. Let's clear it up with the facts.

Enterprise AI will be the largest driver of return on the multitrillion-dollar super cycle of investment in AI infrastructure. The real payoff comes when trillions of tokens move beyond pilots to be embedded directly into the workflows where business decisions are made. ServiceNow is the gateway to this shift, serving as the semantic layer that makes AI ubiquitous in the enterprise. We are also the great consolidator of hundreds of feature and function-specific software solutions into end-to-end business processes with our AI control tower for business reinvention. You need AI plus workflows because AI is probabilistic, which by definition means we can't be certain about the results.

Workflow orchestration is deterministic, predictable, no randomness, which is required given the sophistication and governance of running global enterprises. AI doesn't replace enterprise orchestration. It depends on it. It depends on governance. It depends on scale. Many people ask why our valuation has not kept pace with our results. The short answer is that we have been viewed as a feature-oriented SaaS company. We are not living in a SaaS neighborhood. We are a platform company executing a long-term platform strategy where AI agents and workflows are harmonious and synonymous, creating sustained advantage, not short-term wins. This makes ServiceNow's AI platform more strategically relevant today than ever. By the way, our monthly active users grew 25%.

Now Assist NNACV outperformed expectations in Q4 and surpassed $600,000,000 in ACV. In Q4, Now Assist NNACV more than doubled year over year. We had 35 deals over $1,000,000 in Q4 alone. Our AI control tower deal volume nearly tripled. We saw great brands already purchasing assist packs quarter over quarter in Q4 across a variety of industries, including financial services, manufacturing, healthcare, life sciences, public sector, and technology. Overall, the number of workflows and the number of transactions each grew over 33%, from 60,000,000,000 to 80,000,000,000 and from 4,800,000,000,000 to 6,400,000,000,000 respectively. And the growth continues. I continue to hear speculation about seat compression.

If all we did was look at available seats in our target market, there would be an estimated 1,300,000,000 seats in that target market. So we barely scratched the surface. And, of course, we're looking far beyond seats alone with our hybrid business model for billions of devices, agents, and assists. On the back of this momentum, we're guiding to 20% subscription revenue growth for 2026. And by now, everyone knows how ServiceNow rolls. We don't set our sights on hitting the guide. We set our sights on beating it. The speculation out there is that M&A is the new playbook out of necessity. Here are the facts. ServiceNow has the fastest organic growth in the history of enterprise software.

We're the fastest enterprise software company to have ever reached $1,000,000,000, $5,000,000,000, and $10,000,000,000 organically. And on our way to cross $15,000,000,000 plus this year. Since 2019, nearly quadrupled our revenue all built on a foundation of continuous innovation and net new product delivery. ServiceNow is fully capable of achieving previously stated subscription revenue and Now Assist ACV targets without M&A. Our capital allocation strategy is about accelerating customer value and shareholder value. We have never acquired a single company for revenue alone. We use M&A to expand into an even larger TAM. And it is now beyond $600,000,000,000 based entirely on where our customers need us to go, where we know we can build exciting growth businesses.

Our announced plans to acquire VESA and ARMS happened in rapid succession because this assembles three critical layers for enterprises to operate securely in an agentic AI world: visibility, identity, and orchestration. With our fast-growing billion-plus dollar CACV security and risk business, the timing to expand the opportunity could not be better. Post ARMS, we do not see any other large white spaces that are necessary to complete our platform vision for security. ServiceNow's organic growth strategy and opportunistic tuck-ins for tech and talent remain unchanged. AI, data, workflows, security. We are one of the few companies totally in control of our own destiny. We are playing offense on our tippy toes.

That's why we're announcing an incremental $5,000,000,000 US dollar share repurchase authorization with an immediate ASR of $2,000,000,000. Here's another fact. ServiceNow has one unifying objective, which is simply to be the AI-defining enterprise software of the twenty-first century. IDC estimates there will be 2,200,000,000 AI agents in the world by 2030. Millions of those will be built on the ServiceNow platform. Whatever isn't built on our platform will be governed and secured by our AI control tower. ServiceNow is a build-or-buy winner. We'll win with the builders because they want ServiceNow for our data fabric, our agents, governance, and security.

We'll win for buyers because they want best-of-breed AI native workflows and agents to reinvent their status quo in IT, HR, CRM, app development, and beyond. We have a pristine rule of 55 plus financial profile. A comprehensive integrated platform architecture. We're open to any cloud, any language model, any data source, any system integration. We're one of the most trusted companies in the world according to Forbes. Have an award-winning culture with millions of talented applicants. You may have noticed that I recently extended my own commitment here to ServiceNow until 2030 and beyond. There's one reason I did this. Overwhelming belief in this company. This is a $1,000,000,000,000 company in the making.

I can't fathom a better entry point for what ServiceNow is building. To those on this journey with us, we are grateful for your enduring support. To those who are waiting, we've given you every reason to believe the time is now. This is a one-of-one company. That's not speculation. It's a fact. Let's bring the ServiceNow story to life with customer examples. We closed a $1,000,000 plus assist pack deal with a leading US consumer services company after customer service agents generated a 400% ROI. After a year of deployment, the customer needed eight times more assists.

As they transition customer support operations to predominantly automated interactions, this is minimizing operating costs, shortening support resolution times, and enhancing the overall customer experience. They are flipping the support model from 80% human-led, 20% automated, to 80% automated, and 20% human-led. In Q4, we closed a landmark 7-figure deal with a complex high-tech manufacturer. Involving an end-to-end takeout of a legacy CRM competitor. They turned to ServiceNow CPQ to solve their complex deal evaluations, replacing manual spreadsheets and unsuccessful legacy tools. In combination with CSM, workflow data fabric, Now Assist, and other products too, our customer trusted ServiceNow as their AI control tower for business reinvention.

A leading European telecom provider is building an AI-driven CRM solution for the telecom industry with ServiceNow. They consolidated seven internal systems using ServiceNow CRM, and they're gonna modernize even further to sell, serve, and support its own customers. This is reducing cost by 30%, reducing cycle time from order to fulfillment by 25%, and resolving 20% more work orders on the first request. A leading Canadian real estate company selected ServiceNow CRM platform to integrate all aspects of their resident support and field operations with a unified data model. The customer leveraged ServiceNow to gain real-time operational visibility, optimize dispatch, and automate work order management. This drove efficiency gains that delivered more than 100% ROI.

A global business services company deployed ServiceNow agents for incident classification and resolution, resulting in initial time savings of 13% for agents involved. The company is now processing hundreds of thousands of AI assists monthly on ServiceNow. An international leader in commercial real estate services deployed ServiceNow agents to automate email triage across their service desk, reducing meantime to resolution from two days to minutes, freeing agents for higher-value work. A US insurance company uses ServiceNow out-of-the-box agents to automate email-to-case conversion, achieving 91% accuracy and saving agents up to 12% of their time annually through an AI-first mindset. A diversified industrial multinational conglomerate deployed ServiceNow agents to automate help desk triage.

These ServiceNow agents now handle over 90% of incoming requests. They've reduced triage time by 50%, with 99% routing accuracy. This saves tens of thousands of hours annually. One of Europe's largest drugstore chains uses ServiceNow to transform its customer service, cutting the time it took customers to receive support from nine minutes to thirty seconds and resolving customer issues with 98% accuracy. ServiceNow was selected by a large US county in a 7-figure deal to replace a legacy highly customized IT platform. They are supporting operations by consolidating manual fragmented processes into our AI platform, leveraging native ITSM, asset management, custom app development, and offline mobile capabilities.

A large US agency is using ServiceNow as the foundation of its IT modernization strategy. They're consolidating all IT services on ServiceNow, replacing more than 40 disparate tools currently in use, and looking ahead, they plan to use ServiceNow Agenic AI capabilities to expand self-service and reduce operational overhead. Everyone talks about AI. We deliver business outcomes with AI. Last quarter, we announced a collaboration with FedEx DataWorks. While supply chains are more critical than ever, many companies still lack the predictive intelligence needed to coordinate today's complex value chains. We're combining ServiceNow's orchestration with FedEx's unique data DNA to provide procurement leaders with trusted insights and our source-to-pay solution. FedEx is also expanding beyond just Source To Pay.

Its partnership will leverage the capabilities of the ServiceNow AI platform. Other great brands, like Adobe, Accenture, Siemens, Panasonic Avionics, and BT, have all saved millions and millions, and they're using ServiceNow to grow their business. And we could go on and on. So let's talk a little bit about our great partners. Our ecosystem includes all three hyperscalers. They're all great companies. The language model companies, they're excellent too. Systems integrators, pure play ServiceNow partners, and independent software vendors. They're all building their futures on our AI platform. Think about this.

ServiceNow and Microsoft have announced a deep AI integration, connecting copilots, agents, and data across Microsoft 365 and the ServiceNow AI platform to deliver seamless orchestration, governance, and enterprise-wide automation. The collaboration introduces Microsoft's Agent 365 integration, and it's anchored by ServiceNow's AI control tower. And it sets a whole new standard for enterprise AI interoperability, moving organizations from isolated AI experiences to autonomous AI workflows that drive efficiency and return on investment. ServiceNow and Anthropic have announced an expanded partnership to integrate Claude models more deeply into the ServiceNow AI platform. Through the collaboration, ServiceNow is also bringing leading cloud models into ServiceNow to support secure, compliant AI across numerous industries.

ServiceNow also announced a new collaboration with OpenAI to enable direct customer access to frontier model capabilities, custom ServiceNow AI solutions, and increased speed with no bespoke development required. Under this agreement, OpenAI models will be a preferred intelligence capability for several agentic use cases offered to ServiceNow enterprise customers. ServiceNow and NTT Data have expanded our strategic partnership to accelerate AI-led transformation in global enterprises, designating NTT Data as a strategic AI delivery partner. This includes co-developing and co-selling AI-powered solutions, also scaling NTT Data's use of ServiceNow's AI platform. And together, we will operationalize AI responsibly, advancing new deployment models and embedding AI engineering expertise into transformation projects.

Again, these are just a few of the many strategic partnerships. Before I wrap up, let me give you a few more facts about our strategic expansion in AI security. As you know, we're growing through the regulatory clearance process, but we can say this. The combination of VESA and ARMS with ServiceNow AI platform will create something that is mission-critical for enterprise AI. In the agentic era, if companies want to scale AI, trust and governance that span any cloud, any asset, any AI system, and any device are all non-negotiable. So here's the problem enterprises face today. AI adoption is expanding the attack surface exponentially.

Companies are deploying autonomous agents across their operations, but they're only able to see a small fraction of their digital estate. Traditional security tools do not address connected assets, especially unmanaged IoT devices, operational technology, and medical equipment. To make matters worse, leaders have no control over who and what can access critical systems and data, and they have no coordinated way to remediate vulnerabilities before they become breaches. And here's where ServiceNow's strategic vision comes into play. First, Armis will solve the visibility problem. ARMS provides real-time agentless discovery and classification of every asset across the entire enterprise. IT, OT, IoT, medical devices, industrial controllers, and even shadow IT that bypasses procurement.

This creates a continuously updated map of the enterprise environment. Armis is already protecting over 40% of the Fortune 100, precisely because they've cracked the visibility challenge. Second, VESA will solve the identity governance problem through its patented access graph technology. VESA maps access relationships and privileges across humans, machines, and AI agents in real-time. This is critical because AI agents need dynamic context-aware permissions. An agent working for a senior manager needs different access than the same agent working for a junior employee. And those permissions must be governed continuously, not set once and forgotten. CISOs have told us this is the bottleneck preventing AI agent deployment at scale.

When both of these are integrated into ServiceNow's AI platform and AI control tower, this is how orchestration goes from theory to reality. When we combine ARMS asset visibility with VESA's identity governance and ServiceNow's business context CMDB, which maps every asset to the services, processes, and teams it supports, you create something highly differentiated. A unified end-to-end security exposure and operation stack that can see, decide, and act across the entire technology footprint. Let's make this concrete for you. Armis discovers a vulnerability on an unmanaged IoT device in a manufacturing plant. That exposure insight automatically flows into ServiceNow's AI control tower.

Now you understand which production line depends on that device, which team owns it, and what the financial impact of downtime would be. Simultaneously, VESA maps who and what has access to that device and related systems. ServiceNow then automatically prioritizes the risk based on business impact, triggers the appropriate remediation workflow, routes it to the right team with the right permissions, and tracks resolution. All before an incident has a chance to occur. This is autonomous proactive cybersecurity, not alerts that sit in a queue. Not manual coordination across fragmented tools, not security theater either. This is intelligent action at machine speed, governed by unified policies executed through an automated workflow machine. We just closed the largest quarter ever.

Customers recognize the expanded security capabilities these acquisitions will unlock, and they are encouraging us to go even deeper and broader with them on OT. Our customers are very excited, and so are we. In closing, ServiceNow is exactly where the world needs it to be. The AI control tower for business reinvention. Situated in the core of the enterprise, in the core of enterprise AI. With the capabilities to automate, orchestrate, and integrate any business process. With Moveworks from ServiceNow, we put AI to work for people, a front door to the agentic enterprise for every single employee in the world. We have the workflow data fabric to map the right information to the right workflows.

We have the most innovative technology operating system in the world, the only one capable of delivering fully autonomous IT. We have the customer demand to deliver AI native solutions for the employee experience and the customer experience to modernize expensive legacy systems. With VESA and ARMS, we'll have the most comprehensive approach to secure the agentic enterprise. There's only two measurements that matter in enterprise technology. Is there completeness of vision? Is there proven capability to execute? On both counts? It's an enthusiastic yes for ServiceNow. And two things can be true at the same time. You can have fast-growing new market participants building exciting use cases, especially for personal productivity at work.

You can also have fast-growing market leaders at the core of enterprise-grade AI. Many postmortems have been written in the enterprise over the years. Most of them, ironically, have been dead wrong. The great Lou Gerstner once said, changing business processes in a company is like setting your hair on fire and then using a hammer to put it out. This is hard work. It requires deep domain expertise, industrial-grade technology, and a global distribution engine to reach global enterprises and meet the customer where they are. Operating plans exist to organize a business. Dreams exist to unleash the imagination.

Unprecedented fast time to value for our customers, $30,000,000,000 plus in revenue, consistent expansion of free cash flow, best-in-class profitable growth, $1,000,000,000,000 market cap, our dreams for ServiceNow are clear. And no operating plan will hold us back. The world works with ServiceNow isn't a tagline. It's a hardline. If you have any doubts that we're building to greatness, look forward to your questions later in the call. Thank you for your time and attention. I'll hand it over to our President and Chief Financial Officer, Gina Mastantuono. Gina, over to you.

Gina Mastantuono: Thank you, Bill. Q4 was another strong quarter, concluding a remarkable year of AI innovation. Net new ACV growth accelerated both quarter over quarter and year over year. We exceeded our top-line growth and operating margin guidance metrics, showcasing our team's consistent execution and unwavering strength of our business. Emerging product areas, including Now Assist, workflow data fabric, Raptor, and CPQ, all outperformed in the quarter. Furthermore, AI is also driving significant cost efficiencies that have resulted in full-year profitability beats on top of our recently raised guidance. Turning to our results. Q4 subscription revenues were $3,466,000,000, growing 19.5% year over year in constant currency, exceeding the high end of our guidance range by 150 basis points.

RPO ended the quarter at approximately $28,200,000,000, representing 22.5% year over year constant currency growth. Current RPO was $12,850,000,000, representing 21% year over year constant currency growth, a 200 basis point beat versus our guidance. Moveworks contributed one point to both RPO and CRPO. From an industry perspective, transportation and logistics continued to lead the way with net new ACV growing over 80% year over year. Business and consumer services also posted impressive growth, surpassing 70% year over year, followed by financial services growing over 40% year over year. Telecom, media, and technology also delivered strong growth in the quarter.

We achieved a robust 98% renewal rate in Q4, highlighting the importance and value that customers place in the ServiceNow AI platform. We closed 244 deals greater than $1,000,000 in net new ACV in the quarter, including nine with new logos. Our strategic focus on landing the right new continues to deliver results, as new logo net new ACV in EMEA and Japan were up nearly 30% year over year. We accelerated net new customer adds in 2025 to end the year with over 8,800 customers, including 603 generating over $5,000,000 in ACV. Even more impressive, the number of customers contributing $20,000,000 or more rose over 30% year over year.

These trends reflect the resilient strength in our core accompanied by increasing momentum in our emerging growth sectors. Our technology workflows net new ACV growth accelerated in Q4, both quarter over quarter and year over year, as customers embrace autonomous IT to accelerate ROI, integrated workflows, take out costs, and improve operational resilience. Service ops is in 16 of our top 20 deals, highlighted by a standout performance in ITOM, which grew net new ACV nearly 50% year over year. ITAM was in 17 of our top 20 deals. Security and risk was in 19 of our top 20 deals and drove nearly 40% net new ACV growth year over year.

Core business workflows were in 13 of our top 20 deals, CRM was in 16, and both saw net new ACV accelerate sequentially. As Bill mentioned, CPQ had a phenomenal quarter. Logic is a perfect example of our M&A strategy creating demonstrable ROI. We identified an adjacent opportunity, moved decisively, integrated flawlessly, and we're already seeing outsized returns. Go-to-market synergies have unlocked significant opportunities as Logix's customer count as part of ServiceNow has nearly quadrupled. Finally, creator workflows were in 19 of our top 20 deals year over year in Q4, with an impressive 32 deals over $1,000,000 in ACV.

Moving to our success in driving broader AI adoption, Now Assist continues to outperform all expectations, surpassing $600,000,000 in ACV and tracking well towards our $1,000,000,000 plus target for 2026. In Q4, deals greater than $1,000,000 nearly tripled quarter over quarter, and customers spending more than $1,000,000 grew over 40%. The number of deals that included five or more Now Assist products increased by over 10x year over year as enterprises expand their AgenTik AI capabilities across their deployments. We've also overachieved our initial AI control tower targets by more than 4x for 2025. As we develop prescriptive roadmaps for GenTig deployments, we are seeing the pace of AI monetization accelerate.

For example, our FDA FTEs engaged with a leading American fast-food chain to enable a path to scaling AgenTik AI across their customer service operations. As a result, they expanded their assist entitlements by 13x upon contract renewal in Q4, based upon anticipated value and usage. It's stories like these that have driven customer service now assist deals to see over 70% upsell expansion at renewal in Q4. Turning to profitability. Non-GAAP operating margin was 31%, 100 basis points above our guidance, driven by the top-line outperformance, OpEx efficiencies, and disciplined spend management. Our free cash flow margin was 57%, up 950 basis points year over year, driven by strong collections, lower CapEx, and significant operating leverage.

For the full year 2025, operating margin was 31%, up 150 basis points year over year. Free cash flow margin was 35%, up 350 basis points year over year, and 100 basis points above our guidance, which I would remind you we raised by 200 basis points just last quarter. Total free cash flow for 2025 was a robust $4,600,000,000, up 34% year over year. We ended 2025 with a healthy balance sheet of over $10,000,000,000 in cash and investments. In Q4, we bought back approximately 3,600,000 shares after adjusting for the stock split as part of our share repurchase program. As of the end of the quarter, we had approximately $1,400,000,000 of authorization remaining.

Given our strong cash position, our strategy of managing the impact of dilution, and our confidence in the business, we announced today that the Board of Directors authorized the purchase of up to an additional $5,000,000,000 of common stock under this program. With the recent pullback in our stock, we also plan to launch a $2,000,000,000 accelerated share repurchase program. Together, these results continue to demonstrate our ability to drive a strong balance of world-class growth, profitability, and shareholder value. Moving to our outlook. For 2026, we expect subscription revenues between $15,530,000,000 and $15,570,000,000, representing 19.5% to 20% year over year growth on a constant currency basis. This includes a one-point contribution from Moveworks.

We expect a subscription gross margin of 82%, reflecting incremental data center investments related to public cloud, geo-expansion, and AI. We expect an operating margin of 32%, up 100 basis points year over year, driven by OpEx savings enabled by AI efficiencies. We expect a free cash flow margin of 36%, up 100 basis points year over year, and 350 basis points ahead of our target that we gave at Financial Analyst Day in May. This is driven by significant operational leverage and further opportunities to reduce CapEx. Finally, we expect GAAP diluted weighted average outstanding shares of 1,050,000,000.

For Q1, we expect subscription revenues between $3,650,000,000 and $3,655,000,000, representing 18.5% to 19% year over year growth on a constant currency basis. This includes a one-point contribution from Loopworks and a one and a half point headwind with a mix shift of on-prem to hosted revenue partially driven by the strong adoption of our hyperscaler offerings. We expect CRPO growth of 20% on a constant currency basis. This also includes a one-point contribution from Moveworks. We expect an operating margin of 31.5%, and we expect 1,050,000,000 GAAP diluted weighted average outstanding shares for the quarter. In conclusion, 2025 has been an incredible year, and we're just getting started.

The world is in the midst of an intelligence super cycle, and ServiceNow is capitalizing on this decisive moment in technology, where the strongest companies leverage rapid change to extend their market leadership. Our recent strategic acquisitions bring us incredible talent and create enormous new market opportunities while solidifying our ability to put AI to work securely across every corner of the enterprise. As we integrate these best-in-class capabilities into the ServiceNow AI platform, we're layering on advantages that position us for even stronger, more durable growth over the long term. Our organic growth engine remains fully intact. Our strategy, complete with a disciplined focus on margin expansion, remains unchanged.

But the ambition is larger, and our confidence in sustained high organic growth has never been greater. Finally, Bill and I want to express our deepest gratitude to our employees around the world. Your relentless innovation and unwavering commitment to our customers are the foundation of everything we've accomplished. With that, I'll open it up for Q&A.

Darren Yip: Operator, did we lose you?

Operator: At this time, I would like to remind everyone, in order to ask a question, press star followed by the number one on your telephone keypad. Please limit yourself to one question. And your first question comes from the line of Alex Zukin. Please go ahead.

Alex Zukin: Hey, guys. Thanks for a really inspired and inspiring message. And congrats on a very strong end to the year. Maybe, Bill, first one for you. Just give us a flavor a little bit of the tailwinds and headwinds that you're seeing both in the demand environment, from a budgetary perspective, and also kind of how you're thinking about the monetization of AI in the product set, particularly the consumption component to play out as we get through the year. You've already clearly cleared the $500,000,000 hurdle that you set for yourself, well on your way to $1,000,000,000. How should we think about that layering into the numbers? And then I've got a quick follow-up for you.

Bill McDermott: Well, thank you very much, Alex, for your very nice remarks. And, also, giving me a chance to explain how it's going out there in the marketplace. You know, we have excellent hyperscalers in the marketplace. They're all great companies. We have exciting language models. We have good data lakes that are out there too. And we have, as you know, six plus decades of legacy systems that have really burdened these companies quite substantially. At the same time, they've customized them. They've invested heavily in them. And they're not gonna rip them out, at least the ones that matter. But what they are doing now is they are looking for platforms that really do matter.

And they are recognizing that MIT study that said basically 95% of those projects out there weren't delivering a positive ROI. They're recognizing clearly that you can't have little pet projects. That AgenTic AI is not just a revolution. It's the only way to survive. It's the only way to grow. And so now they're looking for a platform that spans functions and goes across the business process frontier of their enterprise. As I've said repeatedly, it could be recruit to retire. It could be order to cash, procure to pay, design to build. There are many of these processes, but there's only one company that actually has a platform that's a cross-functional platform.

And so our cooperation with all of them has led many of our customers to simply say, we love it. We want to expand with you, which they're doing. But at the same time, they're looking to retire tools that don't matter. And they're looking to thoroughly examine functional platforms. Because if you could do cross-functional AI work, to reinvent the process on the fly and it's autonomous, why do you want to get drugged down by these little toys or large model large systems that perhaps have built up over the years with many different instances and people are swivel sharing between 33 apps a day. So it's the radical simplification that comes with AI.

And one thing I wanted to double down on is you could see our user count is growing. You can see it's growing in harmony with our revenue. And you can also see that our margins are growing. So we're really the winning hand for companies that want the consolidator. And they want a consolidator now. That's different than it was six years ago when I told you we're the platform of platforms, and we work with everybody. We still do. But we have to respond to what the customer wants. They want cost out, want autonomy in, and they want margin improved and growth. We're giving it to them.

In terms of the buying cycle, what's so cool about this buying cycle is if you have an ROI, and you're fast to value, which we are, we're the fastest one, you don't actually need a budget to get approval on your deal. Just need an executive that wants to win. And the CEOs are investing heavily. Our pipelines have never been better. Let me be clear. Never been better. And don't forget, we gave you those numbers without actually a full forty-day cycle and approval of deals in public sector. Because of the government shutdown. So we got a lot going on there. And we got a lot going across industries and across all segments of the company.

And finally, security grew 100% year over year. So our customers are loving on the digital front door from Moveworks, and we're loving having Moveworks. They're really excited about Armas and Beza for all the reasons I stated in the kind of the keynote here. So you should feel really good about ServiceNow. We didn't have to work hard to give you a great guide. It's there.

Amit Zavery: Alex. So we already, of course, have been selling this hybrid pricing model and we're already seeing a lot of customers now add assist packs. We shared in the earnings already that we had many cuts with average deal size of 500k and some in multi 7-figure range. Renewing and adding more assist packs when they're running out of tokens. That adoption and that consumption is starting to happen very, very fast, especially now that they're using agentic use cases and workflows to run the business. And once they start using one, they start using many more. That's where the assist packs are starting to come in.

So the consumption part has been adding to our subscription revenue quickly as well. And the key to that...

Bill McDermott: Building on what Amit said, which is so important, this is where cross-functional also comes in so heavily. Because these deals, in many cases, have seven or more ServiceNow products built into them. So we're not confined by we can make one buyer in the enterprise happy. We're actually making a team that reports to the CEO happy. So the strategic relevance is elevated considerably. And these assists, we've been telling you now for a year that the day was coming with a hockey stick with form around the reload on those tokens. It's happening.

Alex Zukin: Guys, out of respect to my colleagues, I'll leave it there. But congratulations. And no further questions.

Bill McDermott: Thank you very much, Alex.

Operator: Your next question comes from the line of Keith Weiss with Morgan Stanley. Please go ahead.

Sanchez: Yeah. Hi. This is Sanchez speaking for Keith Weiss, and congrats on proving out the durability of growth in the business throughout the year. I wanted to follow-up on some of the themes in Q3, particularly the federal business. So give me some color on how federal performed via your expressed relative to expectations? I know we had a government shutdown to deal with. You know, there's some large deals in the pipeline. Just how that sort of shaped up in Q4 and what the prospects are looking like for the balance of the year in 2026 on the Fed side?

Bill McDermott: Thank you. Yeah. Well, it was really great. About the Fed business is even with the shutdown and less days to do business, you know, you have to comply with the procurement procedures. And as you know, forty days is a minimum standard, we were still able to get very, very nice deals. And our OneGov offering has been really well received. So we're seeing a very big pipeline in the public sector. What didn't happen in 2025 is only good news for 2026. And we're also seeing that we have significant traction that's now developed in state and local. Public sector more broadly is growing not just US Fed, which is great, but also state and local.

And I do want to mention, we shouldn't forget the global government business because that was up 80% year over year. So the global government business is on fire. Across Europe, the Middle East, and obviously Asia. So feel really, really good that the brand is resonating. And what we're doing in the US is now translating beautifully to the rest of the world. We're in great shape.

Operator: Your next question comes from the line of Gabriela Borges with Goldman Sachs. Please go ahead.

Gabriela Borges: Hi, good afternoon. Thank you. My question is for Gina on the gross margin outlook. Tell us a little bit about how you think about the puts and takes to gross margin, particularly around some of the temporary headwinds you have before monetization on the consumption revenue part of the business. How much of the gross margin headwind from LLM costs inference and API calls, how much of that is temporary versus structural? Thanks so much.

Gina Mastantuono: Thanks, Gabriela, for the question. So listen, I'm really excited about the overall guide from a margin perspective. The fact that despite some headwinds in gross margins, we're able to increase operating margin guidance by 100 basis points and free cash flow by another 100 after increasing by 350 basis points this year is pretty remarkable. I'd say on the gross margin headwind, the bulk of it is actually our very strategic focus on moving more towards hyperscalers that have slightly lower gross margins at this stage of the game given our capacity there with them than our internal.

Now those margins are margin business you'd want me to take every single day, and we're offsetting any headwind down below the line with efficiencies. As we continue to scale up, those hyperscaler deals, margins get even better. And so you can count on ServiceNow to ensure that you will see not only best-in-class top-line growth of 20% plus, but also continued margin accretion at the bottom line, both from an operating margin and free cash flow perspective.

Gabriela Borges: Very good. Thanks for all the color.

Operator: Thank you. Next question comes from the line of Samad Samana with Jefferies. Please go ahead.

Samad Samana: The execution scale continues to be very impressive, so congrats on that. Bill, maybe a question for you. I appreciate you digging into the M&A given that it's been such a big focus. You made a point about there may not be more to expand the TAM at least on the security side via M&A. So should we take that as maybe we won't see Armis-sized deals going forward? Or just maybe help us get some clarity on how we should think about the M&A in 2026. And then Gina, if you could give us any details on Armis' financials.

I know it hasn't closed yet, but it would be helpful just to think you know, how fast it's growing, size, scale, etcetera. You both so much.

Bill McDermott: Yeah. Thank you very much, Samad, for the question. First of all, I wanted to underscore what both Gina and I both said. We're an organic growth company. These were very select M&A moves for the talent, the technology, and the moment to capture a $125,000,000,000 market TAM. And this is also where our customers wanted us to be. As I said, our security and operations portfolio right now is doubling year over year. And they wanted us to do more. I wanted to make it very clear to the investors. I hear you. And we did not and never have bought an asset like many others have, and I know that's probably why it's on your mind.

Because we needed the revenue. What we needed is the innovation and the expanded growth opportunity of a great TAM and a customer base that's waiting for us. So I want to knock that one out of the park based on our great 2025 results and our extraordinary guide and as it relates to future M&A. We do not have a large-scale M&A on the roadmap. What happened and I felt for you all we had Moveworks. It took nine months to close. We no sooner closed Moveworks, which we love Moveworks. We love Bob and the founders of the company, and it's a great culture, great fit. We love them.

Amit and I were no sooner celebrating on their campus with their spouses and everything then we also closed on that and then had Armis and Vezza come to you within, like, a few days. So probably, it was a little bit what's going on over there at ServiceNow? And I noticed that we lost about $10,000,000,000 in market cap on that. Because of the worry. So now the worry is gone. You can give us back the market cap. And, no, we're not going after anything large. We now have them in the family, and we're gonna grow them like we do everything else. And I would want to make one thing clear.

And I'll give Amit a chance to do this. It's really important. We chose assets also that were heavily integrated with ServiceNow already. So this isn't one of those, how's the integration gonna go? It already went. So maybe Amit can give you a little color on that.

Amit Zavery: Yeah. Thanks, Bill. So the way we've been doing clearly, we have this one platform philosophy, and we continue to invest that way. What Armis and Vezza have been doing is we have been integrating those products using a technology called universal agentic network. Which is built on MCP and workflow data fabric making it easy for us to really have processes as well as a lot of the domain expertise which come from Vezza and Armis. Make it integrated into a lot of the capabilities we provide in our one platform.

Over time, some of the capabilities which we have in our one platform will be available through Armis and Vezza, but they are right now completely integrated in a process-oriented way and allowing customers to get advantage of those integrations straight away without having to wait, replatform, or do things which are not going to be more architecturally correct. So with architecturally, we've been very thoughtful about how we bring all these technologies while getting customer adoption quickly as well as value created for customers. And this UAN is a very modern way of integrating and providing a superior way of integrating and bringing products together.

So this will be very straightforward for our customers, and there's no real-time loss when we bring all these capabilities into one platform mindset.

Gina Mastantuono: And then lastly, Samad, on your question on the impact. So we expect to close Armis at this point, second half, early second half of this year. And based on that timing and estimated revenue adjustments that always happen in acquisitions, we expect subscription revenue contribution to be about a point, 100 basis points in 2026. We expect potentially up to maybe 50 bps on headwind to operating margin in '26. Up to 50, so not that large. And given our strong organic operating leverage, we expect to absorb any headwinds to that dilution in 2027 and continue delivering operating margin expansion.

And so we're very committed in our M&A strategy to continue delivering expansion both on the operating margin and free cash flow perspective. We'll obviously provide more details around all of that at Financial Analyst Day as we get closer to close. But, again, not that big of an impact either on the top line or bottom line. It's really about the incredible capabilities and the addressable market that we're opening up for us to go after.

Samad Samana: Great. Thank you all for the thoughtful answers. Have a good night. Thank you so much. Thanks so much. Thank you.

Operator: Your next question comes from the line of Peter Weed with AllianceBernstein. Please go ahead.

Peter Weed: Thank you, and congrats on the really strong finish to the year and guidance for the upcoming year. You know, I think one of the exciting announcements that have come out are your partnerships with OpenAI and Anthropic, you know, one obviously today and one a few days ago. And I couldn't help but notice in reading those, you know, it looks like both of them are making some investments in helping with your customers and getting traction and scaling. Maybe you can share a little bit more about those partnerships. And, obviously, now with multiple of them, there's also kind of the question of decisions for customers, like which one would you focus on?

Like, how do you think through which partner to pull in when? And how are the partners investing and kind of helping you get even more out of the customer opportunity and really driving the business faster?

Amit Zavery: Yeah. Peter, thanks for the question. So as you know, we've been always working with many of the hyperscalers as well as the large language model providers. And we really had an open ecosystem as a mindset. With the large language providers like OpenAI, Anthropic, as well as Google and Gemini, we allow customer choice. We have prompt engineered and made sure that those models work with our products. And customers don't really have to worry about what the underneath the covers, what LLMs we are using. They can choose if they want to and, and let's, use anyone which we provide out of the box.

What we have done over time now is with each of these providers, there's some unique capabilities we think we can take to market. So for example, OpenAI, what we're doing around voice AI. And speech to speech, real-time, multimodal, as well as multilingual capabilities. So our CRM products can now have voice capabilities with OpenAI as a preferred model so that we can have a much more differentiated offering using what we know from domain as well as context and adding the OpenAI speech capabilities into our product. Similarly, with Anthropic, they have a very good coding agent. A build agent, which is a white coding tool, allows anyone to build any workflow on top of ServiceNow.

And we use Claude as the underlying technology to generate some of the code. Then we provide the context, the security, the governance on top of that using build agent to run those workflows on top of ServiceNow as well. So we're finding those unique use cases which might be useful with one of these individual providers, and they want to take those products to go to market with us. We, of course, collaborate with them and tell them about what's the issues with any model maybe, what efficiencies we can get out of it, and how can we optimize it so our customers get value.

But we still keep this idea of openness and availability of default choices for customers. So they can choose anything they want to. And then we'll provide some unique use cases, which will be done with individual providers like OpenAI and Anthropic where they have interest to come with to go jointly to market and build those unique solutions as well. So customer guidance is pretty straightforward. They can choose any of the models. Everything will work. But there might be some of these individual use cases. We believe could really be turbocharged with some of these providers.

And typically in the infrastructure, the model providers are providing 5-10% of value and 90% of IP has been built by ServiceNow to really provide that context-driven enterprise use cases out of the box for our customers who get value instantly.

Bill McDermott: And, Peter, because your question is so strategic and so important, I'd just like to build on this excellent answer. We have to recognize the harmony and the synchronicity between these models and ServiceNow. And the idea that these models are eating enterprise software may be true in some cases, but, obviously, it's not true in our case. They're actually leaning into us because of the innovation on our platform and the broad reach of our go-to-market global engine. So these are very enticing and interesting factors in their decision to team up with us. But it also really does manifest itself.

I think it's something that Dario said when he said, obviously, the cofounder of Anthropic, he said a common error that enterprises make with AI is to treat it as a kind of bolt-on tool that you access now and then. The way to get much better results is to make AI an integral part of how we get work done. And it has to be woven into the whole range of things workers do every day. That's where you actually start to see where these systems are adding value. And it's also why we're partnering with ServiceNow.

So it's kind of like where the decisions in the business take place is in the workflow, and the models need that to have the business impact and really to be resolute with the c-suite of these corporations. So I think that it's really a match made in heaven. I think it's gonna be a great tailwind for our growth. And I hope that we help them grow too. So it's really a nice, nice thing. And I'm glad today we had a chance to clear it all up.

Operator: Thank you. Thanks, Peter. Your next question comes from the line of Patrick Walravens with JMP Securities. Please go ahead.

Patrick Walravens: Oh, great. Thank you. And let me add my congratulations and my appreciation of the hitting the three bear cases upfront. So, Bill, I was talking to a senior executive at a Fortune 500 company. And they really want to transform the enterprise using AI, but there's some sort of specific concerns holding them back. And I'm just there's four of them. I'm just gonna reel them really quick. And I'm sure you have these kinds of conversations all the time with customers, and I just wonder how you address them. Number one was how do we monitor the agents in real-time? Number two was, how do we have kill switches? Number three was, how do we have grading agents?

And then number four was red teaming. So are those the kinds of things that come up all the time, or was this unusual? And how do you address them?

Amit Zavery: No, Pat. I'll address those. I mean, think this I mean, no doubt, every customer we speak to in enterprise are wondering how to adopt the AI, how to make it easy to manage, and really have controls. And no doubt, that questions come up every time in terms of what technology to use and do that very well. So the way we addressed it the reason we launched AI Control Tower early last year and why it's getting so much traction is because we addressing these things head-on. Right? How do you manage and monitor agents real-time? Not just our agents, third-party agents in one system.

It's really built on top of CMDB, so we can now all the kind of assets, be it hardware, software, and AI agent assets. Assets in the same system. And then we can really give you full-time real-time monitoring, observability, as well as cost management, auditing, security in one place. And that allows you to do kill switches where you can now go and shut down any agent which is going rogue, prevent any kind of nefarious activities, as well as do red teaming and ensure you're making security as a prevalent and most important aspect of what you're doing before you go and deliver any AI agents.

And that's it really has opened up a lot of customers' ability to now adopt agentic use cases. Because before, they were worried about losing control, security, governance, and compliance. Now with AI, Control Tower, be able to give them that ability and remove that barrier out of the way. And that's where we saw this huge amount of new use cases emerge with customers and starting to adopt things around incident management, triaging, and things like that. Very quickly because we can give you that real-time visibility and full control. So these are real questions and things we've been addressing and has really worked out.

And AI control tower has grown so fast for us because that takes on head-on as a heterogeneous product out there.

Bill McDermott: And, Patrick, one thing I would say as an example, I'll give you an example of a public sector entity and the man himself who runs this particular entity has literally thousands and thousands of employees, nearly 100,000. And it's set up in three different divisions. What you're seeing a lot of now is they want to consolidate these divisions. They want to consolidate the action onto one platform. Because I keep going back to east to west AI as a cross-functional sport. There's only one CMDB in the world that behaves like ServiceNow's. They know all the people are, all the places are, and all the things are on one platform.

And then you apply the AI and all of our know-how that Amit just outlined and they're running quickly. So he's gotta make change fast. He doesn't have years. He has weeks and months. So we give him a business case to show them an incredible benefit on the ServiceNow platform. And then they looked at what we did with Armas and Vezza, and they said, we're all in. Please roadmap that into the thinking because I want to have one instance. I want to have one single view of my entire enterprise. And I'm going with ServiceNow. In that conversation, we were basically consolidating them out of about 479 legacy tools. And that's what's happening out there.

Because AI is changing the game. This is the consolidator platform.

Patrick Walravens: That's fantastic. Thank you, Bill and Amit.

Amit Zavery: Thank you, Pat. Thanks, Pat. Thank you, Pat.

Operator: Your next question comes from the line of Matt Hedberg with RBC Capital Markets. Please go ahead.

Matt Hedberg: Great. Thanks for taking my question, guys. And congrats from me as well, really strong results here. I guess for Bill or Amit, in an agentic world, it really does seem like now with assist packs, are resonating with customers, and it's great to see the $600,000,000 ACV number already. I guess, while we're entering this period of hybrid pricing and paid seats are still growing strong, do you envision a time in the future when ServiceNow pivots completely away from seats due to maybe consumption or some form of value-based pricing, for instance?

Amit Zavery: Matt, maybe I'll give you my perspective. Of course, Bill and Gina can add that. You know, we keep on thinking about what's the best way to give value and show them what they can get out of the products. Right? So we keep on getting input from them in terms of what kind of pricing and packaging works for them. Typically, we've seen customers do want flexibility, but they also want predictability. So without having some kind of guardrails and understanding how much they're going to spend and what they're going to get out of it, going to complete 100% consumption may be too early in some of the cases.

So I think that the hybrid model has seemed to be resonating with my customers. They know what the envelope they have, what they will be consuming beyond that much will it cost them. And a lot of times, customers even have come back and say, you know what? I've been using a lot more than I'm entitled to. I will just renew on do an on the thing with another higher subscription. So it might not be just consumption-driven. So we just want to give that flexibility. There's some products we do consumption only already, by the way. Right? So we do things like storage, or additional things you might want to use for capacity.

We're doing that, build some tokens around workflow data fabric from an integration perspective. So wherever it makes sense, we will do that. As we go more and more AI native in terms of packaging, we want to continue still to make sure that we don't confuse our customers too much. And make it so difficult for them to predict what they're gonna spend. That they can keep on staying on the sidelines.

Bill McDermott: So we just wanna manage that very well. And, Matt, you know, just building on Amit here for a second. You know? Let me give you a real example. So Amit's 100% right. That the customer wants predictability, which is why against some of the theories out there that there would be seat compression, which is why our active user base is growing 25%. Okay? It's because they want that predictability. The other thing they want is with the assist, when we sell a pro plus version of this platform, we have contemplated all the puts and takes on their business innovation and what the ROI is gonna be to get the sale in the first place.

And so when they derive more value from the assist that they have that comes with the Pro Plus, they're happy to renew it. In fact, they're looking for more ways to use us. You never have a dissatisfied software customer. When you deploy the software and you have happy users. You have an eager customer that wants to expand, and that trend is really big in the AI world. And finally, we're so flexible because what we do is where the rubber hits the road. We're delivering the ROI, and we know it. So I'll give you one example where we replaced the legacy CRM system. By the way, it's not the one I referenced in the script.

And the customer saved $682,000,000. And we would be very happy to take a percentage of that savings and give it to our great shareholders. But the customer will quickly pull back and say, no. No. I like the predictability of the seats. I'm good with that. I'm good with the assist. Let's keep that going. And it's so strong, these business cases, that we now have large SIs that are actually underwriting the savings on ServiceNow. Underwriting it. And guaranteeing it to the customer. Just think about the swagger we can walk into a c-level meeting with knowing that sharing the logos and the examples.

So no matter where the customer needs us to be, if they'd rather split the profits with us, we're open for business.

Operator: We have time for one more question. And our final question comes from the line of Brian Schwartz with Oppenheimer. Please go ahead.

Brian Schwartz: Yes. Hi. Thanks for taking my question this afternoon, squeezing me in. I'm not sure if this is for Bill or Amit. It's on the topic of the mega LLM provider partnerships. Bill, in your introductory comments, you're clearly making it clear you view these anthropics open AI as more complementary to ServiceNow's product set than as competitors. Guess the question I wanted to ask you or Amit, if we think about the percentage of AI inferencing and training workloads that are gonna run on the platform in 2026? How do you think that mix would break out between those workloads running on ServiceNow LLMs versus those third-party foundation models? Thanks.

Amit Zavery: Yeah. Brian, I think, as I said, we definitely want to make sure customers have choice, and they can use any of those foundational models as well as now LLM. In many cases, we've seen customers may line up using frontier models because some of the use cases might make sense to the frontier models. Inferencing as part of the overall workload is still very low as a percentage of cost or usage-wise. Right? As they use tokens, we have a lot of other works we do on top of the inferencing part of it.

Which is really the whole context, data management, the integration, understanding that the particular workflow required for a use case they want to go and deliver on it. So that's really where most of the power goes in. And, I would say in the long term, I would see more of the frontier models as the inferencing models. Versus now LLM, but their sovereign requirements, private data center requirements. Things customers want to deploy in, like, on-prem. But all these models don't work. And that's where we would probably still continue using a lot of third-party our own now LLM as well.

We just want to make sure we have choices and flexibility and let the customer really choose it out. From us, the cost perspective doesn't matter really.

Brian Schwartz: Thank you.

Operator: Ladies and gentlemen, that concludes today's call. Thank you all for joining. You may now disconnect.
            """,
        ),
    ],

    # Add consensus estimates if you have them (optional).
    # e.g. from sell-side research, FactSet, Bloomberg, or public analyst notes.
    consensus_notes=[
        "Management guided FY2026 subscription revenue growth of 19.5-20% constant currency, including ~1 point from Moveworks.",
        "FY2026 operating margin guidance of 32% (up 100bps YoY). Free cash flow margin guidance of 36% (up 100bps YoY).",
        "Now Assist ACV surpassed $600M exiting 2025, with management targeting $1B+ in 2026.",
        "Consensus broadly in line with guidance. Key debate: durability of Now Assist monetization and whether agentic AI consumption drives upside to seat-based revenue assumptions.",
    ],
)

REQUESTS["FIVN"] = ManualMemoRequest(
    company=CompanyMetadata(
        company_name="Five9",
        ticker="FIVN",
        memo_date=date.today(),
    ),
    ten_k_excerpts=[
        ManualSourceExcerpt(
            source="Five9 FY2025 10-K Item 1",
            text="""
Five9 is a leading provider of intelligent customer experience, or CX, platform for enterprise contact centers. With a foundation in our cloud-native solution, Five9 is now evolving into an AI-native CX platform, empowering enterprises to scale seamlessly, innovate faster, and deliver enhanced customer experiences as the market opportunity continues to expand. We have become an established leader in the AI-powered CX market with more than 3,000 customers.

We believe there are two key industry trends driving growth in the cloud contact center market. First is the increasing adoption of cloud-based solutions within companies around the world, which is creating strong demand for integrated cloud contact center software solutions. On-premises systems require large up-front investments, long deployment cycles, and are burdensome to scale and maintain. AI technologies generally require cloud deployment and therefore provide additional incentives for customers to migrate away from their legacy on-premises solutions.

Second is advancements in artificial intelligence, or AI. AI is a significant advancement to improve customer experience across self-service, agent assistance, managerial insights, and workflow automation use cases. The recent advances in Generative AI, including Large Language Models, enable new capabilities in contact centers that were not previously possible. Our Genius AI suite is a comprehensive portfolio of AI solutions that uses Generative AI to power agentic CX.

We provide our solution through a software-as-a-service, or SaaS, business model. We generate subscription revenue from our Intelligent CX Platform, and also generate usage-based telephony revenue. We charge our customers monthly subscription fees for access to our solution, primarily based on the number of licenses. Our AI solutions are sold to our customers on a consumption or capacity basis.

Our revenue has consistently grown. For the years ended December 31, 2025, 2024 and 2023, our revenue was $1,149.1 million, $1,041.9 million and $910.5 million, respectively, representing year-over-year growth of 10% and 14%, respectively. We recorded net income (losses) of $39.4 million, $(12.8) million and $(81.8) million for the years ended December 31, 2025, 2024 and 2023. Our recurring revenue model combined with our Annual Dollar-Based Retention Rate, which was 105% as of December 31, 2025, have enhanced our ability to forecast our financial performance and plan future investments.

We have a large, diverse and global customer base comprised of more than 3,000 organizations as of December 31, 2025, with no single customer representing more than 10% of our revenues in 2025, 2024 or 2023. Our customer base spans organizations of all sizes across multiple industries, including banking and financial services, business process outsourcers, retail, healthcare, technology and education.

The market for contact center software is fragmented, highly competitive and rapidly evolving. We currently compete with large legacy vendors such as Avaya and Cisco. We compete with cloud contact center vendors such as Genesys and NICE. Amazon, Twilio, and Microsoft have introduced developer-oriented solutions. CRM vendors are increasingly offering features and functionality, including AI contact center solutions, that were traditionally provided by contact center service providers. CRM and customer experience vendors also continue to partner with contact center service providers to provide integrated solutions and may, in the future, acquire competitive contact center service providers. We also compete with new market entrants in AI that offer Generative AI solutions that compete as point products in the market.
            """,
        ),
        ManualSourceExcerpt(
            source="Five9 FY2025 10-K Item 1A",
            text="""
Our quarterly and annual results of operations may fluctuate significantly. Our installed base business, which contributes a significant portion of our annual revenue growth, continues to experience macroeconomic challenges. Factors that may cause fluctuations include: if our existing customers terminate their subscriptions or reduce their subscriptions and related usage, or fail to grow subscriptions at the rate they have in the past; our ability to attract new customers and grow our business with existing customers; our ability to capitalize on the transition by our customers to AI solutions; and adverse economic conditions, including the impact of macroeconomic challenges, global tariff increases, continued inflation, uncertainty regarding consumer spending, and high interest rates.

Our strategy is to sell our solution to both smaller and larger organizations. Our gross margins vary depending on the features and number of licenses purchased by our customers, the increasing reliance on public cloud providers, and the level of usage and professional services required by our customers. Larger customers typically require more professional services, and because our professional services offerings typically have negative margins, any increase in sales of professional services could harm our gross margins and operating results. We also have lower margins on our usage revenues.

Prior to 2025, we had a history of losses, and we may be unable to sustain profitability. We incurred net income (losses) of $39.4 million, $(12.8) million and $(81.8) million for the years ended December 31, 2025, 2024 and 2023, respectively. As of December 31, 2025, we had an accumulated deficit of $378.2 million. We expect to continue to make further investments for the foreseeable future as we continue to expand our business, which may cause us to experience losses in the future. Accordingly, there is no assurance that we will sustain our current profitability.

For the years ended December 31, 2025, 2024 and 2023, our revenues were $1,149.1 million, $1,041.9 million and $910.5 million, respectively, representing year-over-year growth of 10% and 14%, respectively. In the future, as our revenue increases, our annual revenue growth rate may continue to decline. We believe our revenue growth will depend on our ability to: offset any losses or lower growth in license revenue with subscriptions for our AI solutions; maintain our existing customers and their level of subscriptions and related usage; and respond to adverse economic conditions.

If our existing customers terminate their subscriptions or reduce their subscriptions and related usage, our revenues and gross margins will be harmed. We expect to continue to derive a significant portion of our revenues from existing customers. Our customers are able to adjust the number of licenses or level of consumption or capacity to meet their changing contact center volume needs. Subscriptions and related usage by our existing customers may decrease if our customers' business or demand for our services slows or declines; we are unable to offset any losses or lower growth in license revenue with subscriptions for our AI solutions; or customers favor products offered by other contact center providers, particularly as competition continues to increase.

The loss of one or more of our key customers, or a failure to renew our subscription agreements with one or more of our key customers, could harm our ability to market our solution. In addition, acquisitions of our customers could lead to cancellation of our contracts with those customers.

Our growth depends in part on the success of our strategic relationships with third parties. These relationships are typically not exclusive and our partners often also offer products of our competitors. CRM vendors are increasingly offering features and functionality, including AI contact center solutions, that were traditionally provided by contact center service providers. CRM and customer experience vendors also continue to partner with contact center service providers to provide integrated solutions and may, in the future, acquire competitive contact center service providers.
            """,
        ),
        ManualSourceExcerpt(
            source="Five9 FY2025 10-K Item 7",
            text="""
In August 2024, we announced a reduction in force plan as part of our broader efforts to drive balanced, profitable growth. The 2024 Plan reduced our global full-time employees by approximately 6%. On March 31, 2025, our Board of Directors approved a second reduction in force plan. On April 3, 2025, we commenced execution of the 2025 Plan, which resulted in the reduction of our global full-time employees by approximately 4%.

Our revenue increased to $1,149.1 million for the year ended December 31, 2025, from $1,041.9 million for the year ended December 31, 2024. Revenue growth was primarily attributable to our larger customers. We had a net income of $39.4 million for the year ended December 31, 2025, compared to a net loss of $(12.8) million for the year ended December 31, 2024.

Annual Dollar-Based Retention Rate was 105% for the twelve months ended December 31, 2025, compared to 108% for the twelve months ended December 31, 2024. Our Dollar-Based Retention Rate decreased year-over-year, reflecting a combination of factors, including continued macroeconomic headwinds, as well as year-over-year challenges related to a single large new customer ramping significantly throughout 2024 and seasonal increases being stronger in the second half of 2024, offset in part by ongoing momentum in AI and expansions of larger existing customers in 2025.

Adjusted EBITDA was $269.7 million for the year ended December 31, 2025, compared to $196.0 million for the year ended December 31, 2024.

Revenue: $1,149.1 million in 2025 vs $1,041.9 million in 2024 (+10%). Cost of revenue: 45% of revenue (down from 46%). Gross profit: 55% of revenue (up from 54%). R&D: 13% of revenue (down from 16%). Sales and marketing: 27% (down from 30%). Operating income: 3% of revenue in 2025 vs operating loss of 5% in 2024.

While the implications of macroeconomic events on our business remain uncertain over the long term, we expect that macroeconomic challenges will continue to have an adverse impact on our revenue in future periods. For example, despite increases in up-sells and cross-sells, our installed base business, which contributes a significant portion of our annual revenue growth, continues to experience macroeconomic challenges.
            """,
        ),
    ],
    transcript_excerpts=[
        ManualSourceExcerpt(
            source="Five9 Q1 2026 Earnings Call",
            text="""
            Amit Mathradas, Brian Lee, and Andy Dignan. During today's conference call, certain statements will be made that are not historical facts and are considered forward-looking statements within the meaning of the Private Securities Litigation Reform Act of 1995. These forward-looking statements include, but are not limited to, statements regarding our Q2 2026 and full year 2026 guidance, expected improvements in operating and financial metrics, CCaaS and AI revenue growth trends, industry trends, including with respect to AI, our strategy, priorities and execution, our product roadmap and technology investment, our markets, customer demand trends, our market position and opportunity, our capital allocation strategy including our share repurchase programs, and other future events or results. Such statements are simply beliefs and predictions and should not be unduly relied upon by investors. Actual events or results may differ materially, and the company undertakes no obligation to update the information in such statements. These statements are subject to substantial risks and uncertainties that could adversely affect Five9, Inc.'s future results and cause these forward-looking statements to be inaccurate, including the impact of adverse economic conditions, lower growth rates within our installed base of customers, failure to manage our technical operations infrastructure, unsuccessful development of our AI solutions, failure to maintain and develop our contact center solutions, failure to achieve the anticipated benefits of our share repurchase activity, and the other risks discussed under the caption Risk Factors and elsewhere in Five9, Inc.'s annual and quarterly reports filed with the Securities and Exchange Commission. In addition, management will make reference to non-GAAP financial measures during this call. A discussion of why we use non-GAAP financial measures and a reconciliation of our GAAP versus non-GAAP results and guidance is currently available in our press release issued earlier this afternoon, as well as in the appendix of our investor deck that can be found in the Investor Relations section of Five9, Inc.'s website at investors.five9.com. Also, please note that the information provided on this call speaks only to management's views as of today and may no longer be accurate at the time of a replay. Lastly, a reminder: Unless otherwise indicated, financial figures discussed are non-GAAP. I will now turn the call over to Five9, Inc.'s CEO. Please go ahead, Amit.

Amit Mathradas: Thank you, and welcome, everyone, to our first quarter 2026 earnings call. We delivered an encouraging start to the year, and I am particularly pleased to report an acceleration in subscription revenue growth with top and bottom line results coming in above the high end of the guidance ranges. While we are still early in our work, this quarter marks an important step in showing that our actions are beginning to translate into better business performance, with the indicators we care about moving in the right direction again. This is my first full earnings call as CEO. I want to frame our work around four priorities that I believe are essential to driving long-term value at Five9, Inc.


AD
First, building a performance-driven culture rooted in accountability and transparency. Second, optimizing operations. Third, stabilizing and strengthening the core business. And fourth, winning in AI-empowered customer experiences. Let me start with our first priority: culture. Over the past three months, I have spent a significant amount of time with our teams and leaders across the company and had frank conversations with employees across functions and geographies. What is clear to me is that Five9, Inc. has talented people, highly strategic assets, and a real desire to win. But winning also requires clarity of mission, high standards, urgency, and accountability. We need a culture where performance is measured rigorously, decisions are made quickly, and leadership is held to a high standard.

That starts with me. Transparency with the investor community is equally important. Over time, our story has become harder for investors to underwrite than I believe it should be. Some of that was about how we executed, how we communicated, and how clearly we translated our strategy into measurable progress. Going forward, we will demonstrate progress through clearer, relevant, and trackable metrics that help investors assess the health of the business and hold management accountable. We understand that investors want evidence, not ambition. And our job is to convert our vision into results that are quantifiable. Turning to operations.

Over the past year, and with the support and oversight of the board, the company has been executing a significant operational review designed to improve efficiency and simplify execution. This work, which was well underway before I joined, helped drive the 470 basis points increase in EBITDA margin from 2024 to 2025. This foundational work is crucial, but it is only the beginning. We are now in a better position to move faster and reinvest in critical areas. Building on this foundation and with the support of external advisors, I am leading a series of deep dives across the product portfolio to align investments with our long-term competitive priorities.

To help accelerate this effort, we are filling gaps and making changes in leadership and adjusting our organizational design, including reducing spans and layers, to improve focus, speed, and accountability. These changes will help us operate more efficiently and effectively and build a more disciplined foundation for innovation, growth, and continued operating leverage over time. An example of this was our recent hire of Jay Lee, our new chief marketing and growth officer. In this newly created role, Jay will unify global marketing with revenue strategy and operations to build a more aligned, insights-driven go-to-market engine that delivers a seamless experience for customers and partners.

Let me shift to my point of view on the strategic outlook for our industry and our business specifically. AI is one of the most important shifts underway in our industry, and customer experience is one of the most compelling application areas. In my conversations with customers, I am consistently hearing that AI is fundamentally increasing the importance and value of every customer interaction. Historically, contact center spending has been overwhelmingly weighted towards labor, creating a difficult trade-off between lowering costs and delivering better experiences. AI is acting as a catalyst to change this.


AD
Customers now see the potential to reallocate a portion of their labor spend to fund the combination of AI and enhanced CX, better addressing the trade-off between cost and quality. This makes the move to a modern cloud-based platform more urgent than ever. This shift is forcing a critical decision: customers must now consider how AI is incorporated into their CCaaS platform because they want to avoid a sprawling collection of disparate AI tools that cannot seamlessly coordinate with their human agents. This means that AI point solutions are not enough because they only solve a fraction of the problem.

Enterprises are looking for a complete customer experience platform they can trust to handle the entire lifecycle—the orchestration, the data, the integrations, and the governance needed to run reliably in production. This is precisely what Five9, Inc. provides. What is interesting is that as AI handles a large share of routine customer requests, the role of agents is elevated, not eliminated. People become experts who manage complex escalations and provide essential oversight, a necessity in several regulated industries. A platform infused with AI and CX technology empowers these agents with real-time guidance and suggested next steps while simultaneously giving supervisors unprecedented visibility into every interaction, not just a sampling.

Importantly, human-based intelligence and case resolution provide a critical feedback loop for training AI agents, which in turn drives continuous performance improvements of the entire unified platform and further differentiates Five9, Inc. This evolution is about more than just efficiency; it is about value capture. As AI reduces the customer's traditional labor spend, that budget shifts towards technology. We believe this fundamentally expands our monetizable surface area by enabling entirely new use cases and more customer experiences. Our path to success is no longer about simply selling seats. Instead, it is about selling a complete solution based on capabilities and consumption.

This is where we believe our category is going, and we plan to lead it by pairing these and other powerful agentic capabilities into our platform that has the trust and governance that enterprises seek. But we are not assuming success here; we must earn it. And we will measure ourselves not by demos, but by production, adoption, and customer outcomes. We are seeing signs that our strategy is working. In the first quarter, we posted our second consecutive quarter of year-on-year accelerating subscription revenue growth, an important indicator that the core business is strengthening.

We are also seeing customers adopt our AI solutions in production as an integrated part of our CX platform, leading to multiple quarters of strong AI revenue growth. This effort is amplified by the strength of our platform and our ecosystem. Our cloud-native CCaaS platform is built for high reliability and features open integrations, which has allowed us to build an ecosystem of over 1,400 partners. Our deep strategic relationships with market leaders within this ecosystem are critical, serving to validate our technology, strengthen our go-to-market reach, and accelerate enterprise adoption. This is a large opportunity, and we believe Five9, Inc. is one of the few key players truly positioned to capture it.

We intend to do so with both urgency and discipline. Before I hand it over to Brian, let me say a few words about capital allocation. We take our role as stewards of shareholder capital seriously. Our approach will be disciplined, return-oriented, and balanced. This includes investing organically in our business, evaluating inorganic opportunities against a high strategic and financial bar, and, when appropriate, returning capital to shareholders. On the last point, reflecting our confidence in the company's intrinsic value, we intend to complete the remaining amount of our $150 million share repurchase authorization by the end of Q3. In addition, our board has authorized an additional $200 million share repurchase program.

We see this as a compelling use of capital, and Brian will provide more details in a moment. Since joining in February, it has become even clearer to me that Five9, Inc. has talented employees, a portfolio of highly strategic assets, and significant upside potential. It has also become clear to me that we must operate with greater urgency, better execution, and higher accountability as we build toward an AI-driven future. That work is underway, and I intend to drive meaningful change as we work to turn Five9, Inc. from a good company into a great business, with a disciplined focus on creating long-term shareholder value. With that, I will turn the call over to Brian.

Brian Lee: Thank you, Amit, and good afternoon, everyone. I would like to begin by underscoring our commitment to transparency in our reporting. To that end, starting today, you will find supplemental metric disclosures in the investor relations section of our website. While many of these metrics have been disclosed previously, we believe this new format will help simplify your modeling. As Amit noted, we have taken decisive action on returning capital to shareholders. After repurchasing $10 million of shares in the first quarter, we intend to enter into an accelerated share repurchase program for the remaining $90 million under the current authorization, which we expect to be completed by Q3.

The board has also approved a new share repurchase program of $200 million, which we expect to execute opportunistically. These actions reflect our deep conviction in our long-term opportunity and confidence in continuing to generate strong free cash flow while also providing ample strategic flexibility. Now turning to our financials. Q1 revenue was $305 million, up 9% year over year. Of the total for the quarter, the contributions from subscription, telecom, and professional services were approximately [inaudible], respectively. Our subscription revenue grew 13% year over year. This was driven by our CCaaS revenue, which grew 8%, and our AI revenue, which grew 68% to an annual run rate of over $125 million.

For clarity, please note that this AI revenue figure now includes both enterprise and commercial, providing a complete view of this growth driver. Our AI revenue now represents approximately 13% of total subscription revenue, compared to approximately 8% a year ago. And the year-over-year growth rate accelerated from 49% in Q4 2025 to 68% in Q1 2026, primarily driven by our backlog ramping earlier than anticipated. Looking ahead, we expect total subscription and CCaaS growth to trend with our overall revenue guidance. AI revenue growth is expected to fluctuate quarter to quarter given varying ramp schedules, with full year 2026 growth anticipated to exceed 40% year over year.

LTM dollar-based retention rate, defined in our filings as the retention rate of recurring revenue from subscription plus telecom, was 105%, which is the same as Q4 2025. Given our focus on subscription revenue going forward, we will transition our DBRR disclosure to LTM subscription DBR, which came in at 107% in Q1, compared to 106% in Q4 2025. Please refer to the previously mentioned supplemental metric disclosure on our investor relations website with nine quarters of historical dollar-based retention rates. As anticipated, both DBR metrics stabilized in Q1, and we expect Q2 to be at relatively similar levels, plus or minus one percentage point, before inflecting in the second half of the year.

Adjusted gross margin in Q1 was 64% compared to 62% in Q1 last year. Adjusted EBITDA was $74 million, or 24% of revenue, compared to $53 million, or 19% of revenue, in the same quarter last year. In terms of cash flow, cash from operations was $64 million, or 21% of revenue, and free cash flow was $49 million, or 16% of revenue. These profitability and cash flow margins benefited by slightly more than one percentage point in the first quarter from a one-time discount negotiated with a key vendor that we do not expect to recur in future periods. From a balance sheet perspective, we ended the quarter with $724 million in cash, cash equivalents, and short-term investments.

On to guidance. For the second quarter, we are guiding total revenue to a midpoint of $306 million with a range of $303 million to $309 million. For the same period, our guidance for non-GAAP EPS is a midpoint of $0.67 per diluted share, with a range of $0.65 to $0.69. The largest driver of the sequential decline versus Q1 is the one-time discount I mentioned a moment ago that benefited Q1. Additionally, this guidance includes an estimated 3.6 million shares being retired through our accelerated share repurchase. For the second half, we continue to expect total revenue growth to accelerate to double digits driven by our backlog of both new logo and installed base bookings.

For non-GAAP EPS, we expect steady sequential increases in the second half. For the full year 2026, we are guiding total revenue to a midpoint of $1.26 billion with a range of $1.254 billion to $1.266 billion, up from our initial midpoint guidance of $1.254 billion. Our guidance for 2026 non-GAAP EPS is a midpoint of $3.26 per diluted share, with a range of $3.22 to $3.30, which is up from our initial midpoint guidance of $3.18 per diluted share. Additionally, we continue to anticipate annual adjusted EBITDA margin to exceed 24% and annual free cash flow to be approximately $175 million.

That said, our organizational design initiatives are expected to initially result in higher temporary expenses that provide longer-term cost efficiencies along with improved focus, speed, and effectiveness. To assist with modeling, please note the following. Purchases of PP&E are expected to be approximately 3.5% of revenue for 2026 due to a global data center refresh. Please refer to the presentation posted on our investor relations website for additional estimates including share count and taxes, as well as GAAP to non-GAAP reconciliations. We will now open the call for questions. I would like to ask our president, Andy Dignan, to join us for Q&A. Operator, please go ahead.

Operator: We will begin with Sitikantha Panigrahi from Mizuho. Please go ahead and unmute at this time.

Amit Mathradas: Great.

Sitikantha Panigrahi: Thank you, and congrats on a good quarter. Amit, thanks for outlining all those four priorities. Just wondering, what are the two or three most concrete, measurable milestones you think investors should track over the next twelve months to assess the progress of each of those areas?

Amit Mathradas: Thank you, Siti, and thank you for the question. As I am going deeper into the business, the number one thing that I mentioned is I am spending time really diving deep into the market, our tech, and our products, and where Five9, Inc. should be positioned. One benchmark you should be looking for is, in the near future, me coming out and laying that out for you all and being very clear with how that is progressing and where we are taking the business. There are two or three other major areas I have been diving into.

One is culture—how we drive more accountability, more ownership, and organizational design improvements within spans and layers, faster location strategy, and reducing a lot of the bureaucracy and processes internally. The right measure of that should be reflected in the pace that we bring to the market in terms of delivery, as well as underpinning metrics such as margin improvements and growth improvements. That is probably the best way to hold us accountable, and we will be laying that out for you.

Sitikantha Panigrahi: That is helpful. And then one more follow-up. You must have talked to customers and partners over this quarter, and AI is moving much faster than any other trend we have seen before. What are your customers doing in terms of adapting to this faster pace on AI? And what is your assessment of Five9, Inc.’s opportunity there, and why do you think Five9, Inc. is well positioned versus some of the other emerging vendors?

Amit Mathradas: Another good question. As I have been talking to customers, it is clear that everyone is excited about AI, what it can do, and where it is going, particularly in the contact center. The big thing customers are realizing is that AI is allowing for greater interactions and driving an increase in their ability to connect with customers—maybe tier two, tier three—who they had relegated into different channels because of OpEx. Customer experience is a reflection of your OpEx. I know how to make hold times go to zero—double your OpEx. It is challenging. As AI comes in, there is one big thing happening.

As AI replaces seats, those dollars are not leaving the contact center; they are getting reallocated towards software. Companies are looking to platforms like us that can marry voice, digital, and AI and present it in a format where it is all connected under one roof, allowing them to get far larger outputs in efficiency through that system. That is where AI is going. That is why Five9, Inc. is well positioned because of this shift. The TAM for CCaaS plus support AI is nearly 2x the displacement of seats that will happen, and so we now get to play in a much larger market as we evolve and build into this platform.

Operator: Our next question will come from Terrell Frederick Tillman from Truist. Please unmute and ask your question at this time.

Giancarlo Secchiano: Hey, guys. Thanks for taking the question. This is Giancarlo on for Terry. You mentioned seat counts, and we were wondering how the end market has been for contact center seat counts. Are we seeing it stay stable, growing, or declining? And what are customers sharing in terms of their plans for seats as we look into the next six to twelve months?

Brian Lee: Let me start on the actual seat count, and then Amit can chime in as well. We mentioned that the seat count continues to grow at a healthy rate, relatively in line with the CCaaS revenue growth that we had provided. That was commentary we provided last quarter, and it continues to be the case. If you look at the backlog of our customers that we have already won, there is a large portion that is CCaaS-oriented and a smaller but fast-growing portion that is AI. So definitely, the seat growth from a customer perspective has been healthy.

Amit Mathradas: To the second part of your question around what customers are telling us, it is what I mentioned to Siti, which is as they see the ability to get more efficient with their human agents, they want to start investing into software tools, platform tools, and AI tools that allow overall efficiency to grow and for them to increase overall interactions. A number of customers that we are working with today are exactly in that use case.

Giancarlo Secchiano: Got it. Thank you. Appreciate it.

Operator: Our next question will come from Raimo Lenschow from Barclays. Please unmute and ask your question.

Raimo Lenschow: Hey. Thank you. Can you hear me okay?

Brian Lee: Yes.

Raimo Lenschow: Perfect. Congrats. Great start, Amit. Quick question. If you think about the industry at the moment, there is all this talk about AI disruption. But one thing we pick up when we talk with people in the field is how much of the call centers are still on-premise and how we need to think about first cloud migrations and then AI. What have you picked up in your customer conversations in your first three months on that dynamic because for many years, you were the cloud provider that had the structural tailwind? In theory, that should be coming your way even more now given that people have to modernize finally.

Amit Mathradas: Thank you for that question. There are still a vast number of customers on-prem, and eventually they will have to make that decision to move to the cloud. A lot of them are testing out AI right now and asking if they can deploy AI on-prem. We have seen a pickup of those requests. They want to come in and test AI first. The results have been a mixed bag. When you are on-prem, the Achilles’ heel of AI working is data and architecture and how it is connected to the rest of your ecosystem. In some cases, it works; in others, it does not. You will see more customers testing AI on-prem.

My hunch is that for some it may be okay, but a lot will realize that you have to move to the cloud for best-of-breed, full adoption, and the scalability they want. Andy, anything to add?

Andy Dignan: The only thing I would add is we are seeing more of those conversations. Throughout the process of working an opportunity, customers often worry that they need a year to move to the cloud and only then get AI. We have done a lot within our product and our delivery processes so we can deliver AI at the beginning and migrate them at the same time. They can get the best of both worlds, which is really what they are looking for.

Raimo Lenschow: Thank you. That is very clear. And then, Brian, thanks for tightening up disclosure—that is really helpful. On guidance, it is Q1; usually people think, do I change my annual guidance or not? Can you talk a little about the puts and takes for you to change annual guidance a little bit as well and why you took the level? Thank you. Congrats.

Brian Lee: Absolutely, Raimo. Let me take that in two parts. First, Q1: subscription was the key driver of revenue growth—the second quarter of acceleration to 13%. Breaking that down between CCaaS and AI, CCaaS was stable at 8%, and AI accelerated to 68%, primarily driven by the strength of backlog converting to revenue. For modeling purposes, I want to point out that this time the AI revenue disclosure is different from past periods in the sense that we are including enterprise and commercial to give you a full picture of our AI revenue as well as total subscription.

AI as a percent of total subscription revenue a year ago in Q1 2025 was approximately 8%, and it stepped up by roughly one percentage point each quarter to 9%, 10%, and 11% in Q2, Q3, and Q4. The most recent quarter was 13% of total subscription revenue. Going forward into Q2 and the rest of the year, revenue is really driven by the backlog we have been talking about. It is growing at a healthy rate. We have great visibility into it. It is comprised of both new logo and installed base bookings that are converting to revenue, and every customer has a unique ramp schedule.

It just happens to be back-end loaded, which is driving the acceleration to double-digit growth in the second half. The visibility we have gives us the confidence to increase the midpoint of our annual guidance from $1.254 billion to $1.26 billion, essentially covering all of the Q1 beat plus a little bit more.

Operator: Our next question will come from Catharine Trebnick of Rosenblatt. Please unmute and ask your question.

Catharine Trebnick: Thank you very much. Nice quarter. You hired a new chief marketing officer—Jay Lee. I noticed he has a really strong data background, so it does not look like your typical branding type of marketing person. Can you give us some details on why this particular hire with that background?

Amit Mathradas: Thank you for that question. We are super excited to have Jay here. We also adjusted his title to reflect what he is here to do: chief marketing and growth officer. Jay brings a tremendous amount of experience not only in marketing but also in analytics and data and piecing those together. As we look at driving a unified go-to-market and improvements in efficiency in how we serve our customer, you have to look at the full lifecycle. That implies that we all need to be working off one sheet in terms of the data, in terms of the funnel, in how it translates into revenue operations, and the strategies tied to it.

Under one roof, you are going to have one go-to-market strategy, one go-to-market delivery mechanism, and one measurable dataset that drives all of that.

Operator: Our next question will come from Analyst. Michael, you can go ahead and unmute at this time. Michael, you can go ahead and unmute at this time. Okay. Next question will come from Scott Berg of Needham. Scott, you can go ahead and unmute at this time.

Scott Randolph Berg: Nice quarter here. Amit, in your four priorities, one of them was winning in AI. It is obviously the key question most investors are asking on Five9, Inc. given the state of the contact center environment. How do you see the company today, and do you think you are winning effectively? Is this a product item? Do you think you need to lean into product or potentially lean into distribution more to really capture what is a pretty interesting AI opportunity today?

Amit Mathradas: Thank you, Scott. Starting with performance of our AI capabilities today, looking at the 68% year-on-year growth, the acceleration, and the full-year view, I feel like we have strong momentum in what we are doing. That said, the market is moving fast, and we have announced some new products in beta that will be coming into general availability in the next quarter or so. The question for me is how we stay on top of that and speed it up. Near term and long term, to be disciplined, we cannot serve every piece of AI in CX.

We will have to be selective as to what we build into the platform and where our advantages are—whether that is done organically or inorganically—and then where we partner with other players to fill gaps, including vertical or CX-centric needs. It is not one or the other; it is a combination of continuing to deliver and build faster, bringing more products tied to where our platform is going and where we want to own the market, and partnering to fill gaps so end users can work with Five9, Inc. because it is all available in one place.

Scott Randolph Berg: Helpful. And then my follow-up is for Andy. What are you seeing in sales pipelines today? In Q1 maybe versus a year ago in this fast-changing environment—has the composition of deals substantially changed in terms of feature functionality, etc., or has it stayed pretty steady?

Andy Dignan: We track our RFP and pipeline levels, and they have been at elevated levels we have talked about for the last two years; that continues. In terms of the makeup, we are seeing more conversations around AI-first. We have a strong go-to-market around that, as well as a product strategy, and that will continue to play to our strength.

Operator: Our next question comes from Rishi Jaluria of RBC. Rishi, you can go ahead and unmute at this time.

Rishi Jaluria: Thanks so much for taking my questions. I will keep it to just one. Great to see the continued momentum and appreciate the greater transparency. One thing we are all trying to figure out is the impact of AI broadly—whether that is your portfolio, DIY, or third party. I appreciate that you are talking about not doing everything yourselves and partnering where it makes sense. To what extent has that had an impact on the nature of conversations you are having with net new customers around migrating from on-premise to cloud? How has that changed some of your competitive dynamics in the RFP process?

And is there a point at which AI in contact center becomes widespread enough that it actually starts to speed up some of the sales cycles?

Amit Mathradas: In the on-prem solutions, what we are getting a lot of requests for are AI apps that augment humans—like Agent Assist and some of our AI agents—while they contemplate voice changeouts. My view as a new set of eyes on this business is that as AI replaces humans over time, those dollars go back into software, making both humans and AI more efficient. Fast-forward six to twelve months: people may think about point-solution AI as a solve, but most customers are saying if they will still have humans, they need it all on one platform. There are certain functions that cannot be done effectively through point solutions. Agent Assist does not work unless it is in real-time conversations.

For AI voice—agentic scenarios—think about what a platform offers. If someone chooses to speak to a human and goes into hold time, that hold time becomes a window in which AI agents can perform checks or get the call ready for the human—things that cannot happen with independent point products. As humans get elevated, human agents will start monitoring AI agents. If an AI agent is stuck on pronouncing Mathradas, my last name, and does it three or four times, a supervisor can see something go yellow and step into that call and take it over. That cannot happen with point products; it has to happen on a platform.

Everyone is talking about agentic; at Five9, Inc., we are talking about “humanic,” which is the combination of humans and agents doing things that have not been thought about before. That is the direction we are going, and that is where I see this all coming together.

Operator: Our next question comes from Analyst. You can go ahead and unmute at this time. DJ, you can go ahead and unmute at this time. Okay. Our next question will come from Analyst. Elizabeth, you can go ahead and unmute at this time.

Analyst: Great. Thanks. This is Jamie on for Elizabeth. Congrats on the strong results. Going back to some of the earlier commentary, I think I heard you say that some of the strength you saw this quarter was from more of that backlog coming in ahead of expectations. Could you unpack that a little bit more? Was that more attributable to strong execution on your side? Was it customers accelerating deployment timelines? And how has that influenced your thinking for the path of those deployments for the rest of the year for what is still in the backlog?

Brian Lee: It was a combination of factors and not just one customer; it was many customers. As I mentioned earlier in the year, we did have some contingency built into our guidance. Part of it is timing coming in earlier than anticipated. Also, our professional services resources are always there and ready to deploy as quickly as the customer wants. Sometimes customers align faster internally, and the deployment cycle speeds up. We saw some of that. The deployment was strongest on the AI side this quarter, which is why you saw the acceleration from 49% to 68% year-over-year growth.

Going into Q2 and beyond, the total revenue guide implies 9% in Q1, [inaudible] in Q2, and then double-digit growth acceleration in the back half. The CCaaS portion from the backlog will more or less mirror that shape, and AI will fluctuate up and down because of varying deployment schedules. For the annual number, we are anticipating AI revenue growth to exceed at a minimum 40% year over year.

Operator: Our next question comes from Peter Marc Levine of Evercore ISI. You can go ahead and unmute at this time.

Peter Marc Levine: Thank you very much for taking my question. Amit, you made a comment in prepared remarks about not really selling seats anymore and moving more toward a consumption model. Walk us through what that progression looks like. What are you hearing from your customers, and how does the model change over time if it becomes more consumption? And second, Bryan, last quarter we talked about the guide for 2027 being anywhere from 10% to 15%. Is that still the path forward as you think about the business now and as we go into the second half?

Amit Mathradas: Thank you, Peter. We have started to transition with all our new logos, and with existing customers as they renew, to more of a fixed revenue commitment model. They are committing to a revenue number. That brings predictability to them and to us. The thesis is that as seats potentially compress over time, customers get the option to fill that committed revenue with our AI tools and others. They love it because it brings predictability, and they are also betting on our roadmap—saying that as new products come in, they will keep consuming those AI tools to make the human-and-AI combination more efficient. We are seeing that starting to happen.

A lot of our business is starting to move this way. It is early days, but it is picking up. This ties to my original comment: as seats compress, customers are saying those dollars are not leaving the contact center; they will be utilized in other forms of AI and software tools, and that is what they are committing to.

Andy Dignan: We have seen strong traction out of the gate. Customers have great interest in buying into that motion. Often they are making three- and five-year decisions. Their belief in the roadmap—what we have today and what we will deliver—gives them the confidence to sign up for three to five years and make these revenue commitments. It helps protect our downside and makes it easier for Bryan to forecast.

Brian Lee: On your 2027 question, we are not providing 2027 guidance today. We have our 2026 guidance, which keeps us on the path toward double-digit growth exiting the year and expanding EBITDA margin. We are in the middle of deep dives across the portfolio, and we have our new chief marketing and growth officer. We want to let that process play out before revisiting the longer-range framework.

Operator: Our next question comes from Analyst.

Analyst: Hi, guys. This is Ryan on for Jim Fish. Congrats on the quarter. As you think about the guide going forward and your backlog that is driving that guide, how much upside do you have and view into pipeline through the end of the year? How much of that is go-gets versus what you already have in the pipeline?

Brian Lee: If you break down our guide for the last three remaining quarters, it implies we need to get about $80 million of incremental recurring revenue. Roughly two-thirds of that will be coming from our DBR, which we said will stabilize in the second quarter, plus or minus one percentage point, and inflect upward in the second half. The remaining third is coming from new logos—but all from our backlog that is converting to revenue. Each customer has a different schedule, and it is more back-end loaded. There is essentially no dependency on new-logo go-gets for the rest of the year.

Operator: Our next question comes from Tom Blakey of Cantor. Tom, you can go ahead and unmute at this time.

Tom Blakey: Thank you for taking my questions. I want to talk about that AI volatility. Brian, thank you for all the extra color—it is very helpful. Maybe start with what is driving that volatility in terms of a dynamic inflection in AI usage across the space?

Brian Lee: This is really the way bookings have come into our backlog from 2025 and the deployment schedules of each of those customers. AI is a fast-growing part of our business but still small—13% of total subscription revenue. When customers ramp at different times throughout the year, it causes lumpiness. When we say it will fluctuate up and down throughout the year, we are looking bottoms-up at every customer in our backlog and their deployment schedules; that is how it plays out for the rest of the year.

Tom Blakey: As a follow-up, was there an element of use cases or seasonality or non-recurring type of revenue in the AI line?

Brian Lee: No. Not at all. There was no seasonality. It was more on new-logo AI backlog ramping.

Operator: Our next question comes from Jackson Ader of KeyBanc. Jackson, you can go ahead and unmute at this time.

Jackson Ader: Evening, guys. Thanks for taking our questions. We have seen in some other areas of software that the pace of AI innovation has led to some spending paralysis as customers feel it is too early and things are changing too quickly, making them nervous to pick a winner too early. Since customer experience was an early environment for AI to infiltrate, did you feel like you saw that, and did it play out in your base? And if so, are we starting to get past that where there is no longer this uncertainty about picking winners, and it is time to act and spend and deploy?

Amit Mathradas: Given the use case for CX and AI, the number of startups in this space is mind-boggling, and customers are inundated daily. There are early adopters who try a few things, but what they appreciate from companies like Five9, Inc. is that what we bring is tried and tested, with security and governance. It may not be the bleeding edge of everything, but it works and drives meaningful outcomes. That is why many customers pick us over time versus the hundreds of options out there. My sense is you are going to see more of this where trust and governance, especially in large organizations, become a more meaningful part of decision-making.

Operator: Okay, this concludes the Q&A portion of our call. I will now hand the call back over to CEO, Amit Mathradas, for closing remarks.

Amit Mathradas: Thank you all for participating in our Q1 2026 earnings call. As you can see, we have had a good start to the year, but there is more work to be done. We will continue to build upon this momentum and look to capitalize on the larger market opportunity for AI and CX. We look forward to updating you as the progress unfolds throughout the year. Thank you.
            """,
        ),
    ],
    consensus_notes=[
        "FY2025 revenue was $1.149B, growing 10% YoY (down from 14% in 2024). FY2026 revenue guidance of $1.26B midpoint (~10% growth), with double-digit growth expected in H2.",
        "Q1 2026: subscription revenue grew 13% YoY; AI revenue grew 68% YoY to ~$125M annual run rate (13% of total subscription revenue vs 8% a year ago).",
        "Dollar-based retention rate declined from 108% (2024) to 105% (2025). Subscription DBR at 107% in Q1 2026, expected to inflect in H2 2026.",
        "Key debate: whether AI revenue growth (consumption-based assist packs) can offset seat-count pressure and macro headwinds to installed base, and whether new CEO (joined Feb 2026) can re-accelerate growth.",
        "Consensus broadly skeptical given 10% growth, macro headwinds to installed base, and competitive pressure from Genesys, NICE, and CRM vendors. Bull case: AI revenue inflection and fixed-revenue-commitment model expanding TAM.",
    ],
)


# ── Boilerplate for next company — copy, fill in, change ticker ───────────────
#
# REQUESTS["TICK"] = ManualMemoRequest(
#     company=CompanyMetadata(
#         company_name="Company Name",
#         ticker="TICK",
#         memo_date=date.today(),
#     ),
#     ten_k_excerpts=[
#         ManualSourceExcerpt(
#             source="Company FY2025 10-K Item 1",
#             text="""
#             PASTE ITEM 1 EXCERPT HERE
#             """,
#         ),
#         ManualSourceExcerpt(
#             source="Company FY2025 10-K Item 1A",
#             text="""
#             PASTE ITEM 1A (RISK FACTORS) EXCERPT HERE
#             """,
#         ),
#         ManualSourceExcerpt(
#             source="Company FY2025 10-K Item 7",
#             text="""
#             PASTE MD&A EXCERPT HERE
#             """,
#         ),
#     ],
#     transcript_excerpts=[
#         ManualSourceExcerpt(
#             source="Company Q4 2025 Earnings Call",
#             text="""
#             PASTE EARNINGS CALL TRANSCRIPT EXCERPT HERE
#             """,
#         ),
#     ],
#     consensus_notes=[
#         "PASTE CONSENSUS NOTES HERE",
#     ],
# )


# ── Alphabet / Google (GOOGL) — PDF workflow ─────────────────────────────────
# Source documents uploaded directly to Claude.ai; no excerpts needed here.

REQUESTS["GOOGL"] = ManualMemoRequest(
    company=CompanyMetadata(
        company_name="Alphabet",
        ticker="GOOGL",
        memo_date=date.today(),
    ),
    ten_k_excerpts=[
        ManualSourceExcerpt(
            source="Alphabet FY2025 10-K",
            text="Source documents uploaded directly to Claude.ai.",
        ),
    ],
    transcript_excerpts=[
        ManualSourceExcerpt(
            source="Alphabet Q1 2026 Earnings Call",
            text="Source documents uploaded directly to Claude.ai.",
        ),
    ],
    consensus_notes=[
        "Current share price approximately $165 (June 2026). Market cap approximately $2 trillion.",
        "Consensus expects approximately 11-12% total revenue growth in FY2026, with Google Cloud growing ~28-30%.",
        "Street broadly values Alphabet as a Search-dependent advertising business with Cloud as a long-dated option, not yet pricing in a structural AI platform re-rating.",
        "Key debate: whether rising CapEx ($91B in FY2025, guided $180-190B in FY2026) compresses margins before Cloud revenue inflects enough to absorb it.",
        "Unresolved antitrust overhang (Search distribution case, ad-tech case) treated by most analysts as a discount to fair value rather than existential risk.",
    ],
)


# ── Costco (COST) — PDF workflow ──────────────────────────────────────────────
# Source documents uploaded directly to Claude.ai; no excerpts needed here.

REQUESTS["COST"] = ManualMemoRequest(
    company=CompanyMetadata(
        company_name="Costco",
        ticker="COST",
        memo_date=date.today(),
    ),
    ten_k_excerpts=[
        ManualSourceExcerpt(
            source="Costco FY2025 10-K",
            text="Source documents uploaded directly to Claude.ai.",
        ),
    ],
    transcript_excerpts=[
        ManualSourceExcerpt(
            source="Costco Q3 FY2026 Earnings Call",
            text="Source documents uploaded directly to Claude.ai.",
        ),
    ],
    consensus_notes=[
        "Current share price approximately $1,050 (June 2026). Market cap approximately $470 billion.",
        "Consensus expects approximately 8-10% revenue growth in FY2026, with comparable sales growth of 6-8%.",
        "Street broadly values Costco at a premium multiple (~50x forward earnings) reflecting its membership model, renewal rates above 90%, and consistent execution.",
        "Key debate: whether Costco's valuation premium is justified given slowing unit growth, e-commerce competition, and whether membership fee increases can sustain earnings growth.",
        "Bears argue the stock is priced for perfection with limited upside from current levels. Bulls point to international expansion runway and resilient member loyalty as underappreciated.",
    ],
)


# ── Meta Platforms (META) — PDF workflow ──────────────────────────────────────
REQUESTS["META"] = ManualMemoRequest(
    company=CompanyMetadata(
        company_name="Meta Platforms",
        ticker="META",
        memo_date=date.today(),
    ),
    ten_k_excerpts=[
        ManualSourceExcerpt(
            source="Meta FY2025 10-K",
            text="Source documents uploaded directly to Claude.ai.",
        ),
    ],
    transcript_excerpts=[
        ManualSourceExcerpt(
            source="Meta Q1 2026 Earnings Call",
            text="Source documents uploaded directly to Claude.ai.",
        ),
    ],
    consensus_notes=[
        "Current share price approximately $580 (June 2026). Market cap approximately $1.45 trillion.",
        "Consensus expects approximately 15-18% revenue growth in FY2026, driven by advertising and early monetization of AI features.",
        "Street values Meta as a digital advertising duopoly with Alphabet, trading at ~22-24x forward earnings — a discount to its growth rate.",
        "Key debate: whether Reality Labs losses and AI infrastructure CapEx ($60-65B guided for FY2026) will weigh on free cash flow, or whether AI-driven ad targeting gains justify the spend.",
        "Bears: AI CapEx is open-ended and ROI unclear; regulatory risk in EU around data privacy and ad targeting. Bulls: core ad business is accelerating, Threads gaining traction, Llama ecosystem broadening the moat.",
    ],
)


# ── RUN ───────────────────────────────────────────────────────────────────────

def _flag_arg(flag: str) -> str | None:
    for i, arg in enumerate(sys.argv):
        if arg == flag and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return None


def main() -> None:
    stub_mode = "--stub" in sys.argv
    paste_mode = "--paste" in sys.argv
    response_file = _flag_arg("--response-file")
    skip_validation = "--skip-validation" in sys.argv
    ticker = (_flag_arg("--ticker") or next(iter(REQUESTS))).upper()

    if ticker not in REQUESTS:
        raise SystemExit(
            f"Unknown ticker: {ticker}\n"
            f"Available: {', '.join(REQUESTS)}"
        )
    request = REQUESTS[ticker]

    if response_file:
        # Parse a saved JSON response directly — no LLM call needed.
        response_path = Path(response_file)
        if not response_path.exists():
            raise SystemExit(f"Response file not found: {response_path}")
        print(f"Reading response from {response_path}...")
        raw_response = response_path.read_text()
        if skip_validation:
            print("Skipping evidence validation (PDF workflow — source text not in script).")
            import json as _json
            from pydantic import ValidationError
            try:
                payload = _json.loads(raw_response)
                from backend.models.schemas import InvestmentMemo
                memo = InvestmentMemo.model_validate(payload)
            except Exception as e:
                raise SystemExit(f"Schema validation failed: {e}")
        else:
            memo = parse_investment_memo_response(
                raw_response,
                source_documents=source_documents_from_request(request),
            )
        output = json.dumps(memo.model_dump(mode="json"), indent=2)
        out_path = (
            Path(__file__).resolve().parents[1]
            / "data" / "raw"
            / f"{request.company.ticker}.json"
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output)
        print(output)
        print(f"\nSaved to {out_path}")
        return

    if stub_mode:
        print("Running in stub mode — no API key needed. Output is a pre-written example memo.")
        llm = _StubLLM()
    elif paste_mode:
        print("Running in paste mode — the prompt will be saved to a file for upload to Claude.ai.")
        llm = _PasteLLM(ticker=request.company.ticker)
    else:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise SystemExit(
                "Options:\n"
                "  --paste              save prompt to file for upload to Claude.ai\n"
                "  --response-file PATH parse a saved JSON response from Claude.ai\n"
                "  --stub               use a pre-written example memo to test the pipeline\n"
                "  or set ANTHROPIC_API_KEY to call the API directly"
            )
        llm = _AnthropicLLM()

    print(f"Generating memo for {request.company.ticker}...")
    memo = ManualMemoGenerator(llm).generate(request)

    output = json.dumps(memo.model_dump(mode="json"), indent=2)

    out_path = (
        Path(__file__).resolve().parents[1]
        / "data" / "raw"
        / f"{request.company.ticker}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(output)

    print(output)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
