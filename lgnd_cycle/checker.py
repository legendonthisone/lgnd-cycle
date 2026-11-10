"""Checker: plain code that refuses anything the evidence does not support.

Why no AI here? The checker's job is to catch the AI. If it were another AI,
it could make the same mistake. Code cannot be talked into agreeing.
"""
import re
from .pricing import ADDONS, price


def _norm(s):
    return re.sub(r"\s+", " ", s.lower()).strip()


def check(enquiry_text, intake, quote):
    problems, warnings = [], []
    text = _norm(enquiry_text)

    # 1. Every feature must quote the client's own words, exactly.
    for f in intake.get("features", []):
        if f.get("name") not in ADDONS:
            problems.append(f"unknown feature '{f.get('name')}'")
        ev = _norm(f.get("evidence", ""))
        if len(ev) < 4 or ev not in text:
            problems.append(f"feature '{f.get('name')}' has no real evidence in the enquiry (invented?)")

    # 2. The quote must match a fresh recalculation by the pricing tool.
    fresh = price(intake["pages"], [f["name"] for f in intake.get("features", [])])
    if fresh.total != quote.total or fresh.deposit != quote.deposit:
        problems.append(f"price mismatch: quote says ${quote.total}, pricing tool says ${fresh.total}")

    # 3. Things a human should look at before anything is sent.
    if not intake.get("pages_stated", False):
        warnings.append(f"page count was estimated ({intake['pages']}), confirm with client")
    if intake.get("out_of_scope"):
        warnings.append("client asked for things we don't price: " + "; ".join(intake["out_of_scope"]))
    if quote.needs_human:
        warnings.extend(quote.reasons)

    status = "BLOCKED" if problems else ("NEEDS_REVIEW" if warnings else "PASS")
    return {"status": status, "problems": problems, "warnings": warnings}
