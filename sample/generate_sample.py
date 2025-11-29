"""Generate a multi-page sample PDF for testing the Document Processor.

Produces a fictional company annual report with several sections and concrete
facts (numbers, names, dates) so you can meaningfully test both the summary and
the page-cited chat. Uses PyMuPDF (fitz), which ships in the backend image.
"""
import fitz  # PyMuPDF

TITLE = "Acme Robotics, Inc. — Annual Report 2025"

SECTIONS = [
    (
        "1. Executive Summary",
        """Acme Robotics, Inc. is a developer of autonomous warehouse robots and
fleet-orchestration software. The company was founded in 2014 and is
headquartered in Austin, Texas. In fiscal year 2025, Acme reported total
revenue of $482 million, an increase of 18% over the prior year. Net income
was $54 million, and the company ended the year with $310 million in cash and
equivalents.

The chief executive officer is Dr. Lena Ortiz, who has led the company since
2019. During 2025 the company shipped its 50,000th robot, expanded into three
new countries, and launched its second-generation fleet operating system,
codenamed "Helios". This report summarizes the company's financial performance,
product lines, market risks, research investments, and outlook for 2026.""",
    ),
    (
        "2. Financial Highlights",
        """Revenue grew to $482 million in 2025 from $408 million in 2024, driven
primarily by a 27% increase in software subscription revenue. Hardware sales
accounted for $300 million of total revenue, while recurring software and
support contracts contributed $182 million. Gross margin improved to 61%, up
from 57% in 2024, reflecting a higher software mix and lower component costs.

Operating expenses were $228 million, of which research and development was
$96 million. The company repurchased $40 million of common stock and did not
pay a dividend. Deferred revenue, a leading indicator of future software
revenue, rose 31% year over year to $145 million. Management reaffirmed its
long-term target of 25% software revenue growth and 60%+ gross margins.""",
    ),
    (
        "3. Product Lines",
        """Acme sells three primary hardware products. The AR-100 is an
entry-level shelf-picking robot aimed at small and mid-sized warehouses. The
AR-300 is a heavy-payload model rated to 500 kg, used in distribution centers.
The AR-X is a research platform sold to universities and corporate labs.

All hardware is orchestrated by the Helios fleet operating system, which
schedules tasks, routes robots, and integrates with common warehouse
management systems. Helios is sold as an annual per-robot subscription. In
2025 the attach rate of Helios to new hardware sales reached 92%. The company
also introduced "Helios Insights", an analytics add-on that surfaces
throughput bottlenecks; it was adopted by 140 customers in its first year.""",
    ),
    (
        "4. Market and Operational Risks",
        """The company faces several risks. First, customer concentration: the
top five customers accounted for 34% of 2025 revenue, and the loss of a major
customer could materially affect results. Second, supply chain exposure: Acme
sources high-precision motors from a limited number of suppliers, and a
disruption could delay shipments. Third, competition: several well-funded
entrants have introduced lower-cost robots, which may pressure hardware
pricing.

Regulatory risk is also relevant as autonomous-system safety standards evolve
across jurisdictions. The company maintains product liability insurance and
conducts independent safety audits. A contract may be terminated by either
party with 90 days' written notice; early termination by a customer incurs a
fee equal to three months of subscription value.""",
    ),
    (
        "5. Research and Development",
        """R&D spending was $96 million in 2025, or 20% of revenue. The largest
program was the Helios operating system, which moved to a new motion-planning
engine that reduced average task time by 14%. A second program focused on
battery management, extending average robot uptime between charges from 6.2 to
8.1 hours.

The company holds 73 issued patents and has 41 applications pending. It
employs 280 engineers across offices in Austin, Toronto, and Munich. In 2025
Acme established a research partnership with a major university to study
multi-robot coordination, contributing $4 million over two years. Management
considers software differentiation, not hardware, to be its primary moat.""",
    ),
    (
        "6. Sustainability",
        """Acme published its second sustainability report in 2025. The company's
robots are designed for a service life of at least eight years, and a
refurbishment program returned 3,200 units to service during the year. Scope 1
and 2 greenhouse gas emissions were 11,400 metric tons of CO2 equivalent, down
9% from 2024, largely due to a transition to renewable electricity at the
Austin facility.

The company set a target to reach net-zero operational emissions by 2032. It
also committed to sourcing 100% of aluminum from certified recycled suppliers
by 2028. Employee turnover was 9%, below the industry average, and the company
reported a workforce that is 38% women across all roles.""",
    ),
    (
        "7. Outlook for 2026",
        """For 2026, management guided to revenue between $560 million and $585
million, representing growth of 16% to 21%. Software revenue is expected to
exceed $235 million as the Helios attach rate approaches 95%. The company plans
to open a fourth office, likely in Singapore, to support Asia-Pacific
expansion.

Capital expenditure is expected to be approximately $35 million, focused on
manufacturing automation. Management expects gross margin to remain above 60%
and intends to keep R&D near 20% of revenue. Key milestones for 2026 include
the general availability of an outdoor-rated robot and the launch of a
usage-based pricing tier for Helios. The board authorized a new $75 million
share repurchase program effective January 2026.""",
    ),
]


def build(path: str) -> None:
    doc = fitz.open()
    # Title page
    page = doc.new_page()
    page.insert_textbox(
        fitz.Rect(72, 200, 523, 400),
        f"{TITLE}\n\nConfidential — For Testing Purposes Only",
        fontsize=22,
        fontname="helv",
        align=1,
    )
    # One section per page.
    for heading, body in SECTIONS:
        page = doc.new_page()  # default A4
        page.insert_textbox(
            fitz.Rect(72, 72, 523, 760),
            f"{heading}\n\n{body}",
            fontsize=12,
            fontname="helv",
            align=0,
        )
    doc.save(path)
    print(f"Wrote {path} ({doc.page_count} pages)")


if __name__ == "__main__":
    build("/tmp/sample-report.pdf")
