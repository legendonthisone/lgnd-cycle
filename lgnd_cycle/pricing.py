"""Pricing tool. Plain code, no AI.

Why: an AI that does maths in its head will sometimes get it wrong. Prices live
here, in code, so the same project always gets the same price.

Note for judges: these pricing RULES are LGND's existing business rules (used
before the hackathon). This code was written during the hackathon.
"""
from dataclasses import dataclass, field

PRICE_PER_PAGE = 100          # USD per page
ADDONS = {                    # USD, one-off
    "payments": 300,
    "booking": 250,
    "cms": 200,
    "user_accounts": 200,
}
PRICE_CAP = 2000              # anything above this needs a human conversation
DEPOSIT_RATE = 0.5            # 50% deposit starts the build clock
MAX_PAGES = 15


@dataclass
class Quote:
    pages: int
    features: list
    line_items: list = field(default_factory=list)
    total: int = 0
    deposit: int = 0
    weeks: str = ""
    needs_human: bool = False
    reasons: list = field(default_factory=list)


def timeline(pages: int, features: list) -> str:
    heavy = len(features) >= 2
    if heavy:
        return "3 to 4 weeks"
    if pages <= 1:
        return "about 1 week"
    if pages <= 5:
        return "about 2 weeks"
    return "3 to 4 weeks"


def price(pages: int, features: list) -> Quote:
    """Return a Quote. Raises ValueError on input the tool must never guess at."""
    if not isinstance(pages, int) or pages < 1:
        raise ValueError("pages must be a whole number of at least 1")
    unknown = [f for f in features if f not in ADDONS]
    if unknown:
        raise ValueError(f"unknown features: {unknown}")
    features = sorted(set(features))

    q = Quote(pages=pages, features=features)
    if pages > MAX_PAGES:
        q.needs_human = True
        q.reasons.append(f"{pages} pages is above the {MAX_PAGES}-page limit")

    q.line_items.append({"item": f"{pages} page(s) x ${PRICE_PER_PAGE}", "usd": pages * PRICE_PER_PAGE})
    for f in features:
        q.line_items.append({"item": f"Add-on: {f}", "usd": ADDONS[f]})
    q.total = sum(li["usd"] for li in q.line_items)
    if q.total > PRICE_CAP:
        q.needs_human = True
        q.reasons.append(f"total ${q.total} is above the ${PRICE_CAP} cap")
    q.deposit = round(q.total * DEPOSIT_RATE)
    q.weeks = timeline(pages, features)
    return q
