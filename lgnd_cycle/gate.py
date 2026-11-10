"""Approval gate: a human says yes before any money is requested.

Why: the AI and the checker can both be right and the deal can still be wrong
(the client changed their mind on the phone, the price needs a discount).
Only Ayobami knows that, so nothing leaves the building without him.

How it stays honest:
1. A BLOCKED quote can never be approved. The gate does not even ask.
2. Approval must be typed in full ("approve"). Enter, "y" or "yes" do not count.
3. The approval is tied to a fingerprint of the exact quote. If the quote
   changes by one dollar after approval, the payment step refuses to run.
"""
import hashlib, json
from dataclasses import asdict


def fingerprint(quote):
    """Short SHA-256 of the quote. Same quote, same fingerprint, every time."""
    raw = json.dumps(asdict(quote), sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def review(quote, verdict, ask=input):
    """Show the quote to a human and return the decision.

    `ask` is the function that collects the answer. In real use it is input();
    tests pass a fake one so they never wait for a keyboard.
    """
    fp = fingerprint(quote)
    if verdict["status"] == "BLOCKED":
        return {"decision": "refused_blocked", "fingerprint": fp,
                "note": "checker blocked this quote; fix the problems first"}

    if verdict["status"] == "NEEDS_REVIEW":
        print("\nBefore you approve, look at these:")
        for w in verdict["warnings"]:
            print("  -", w)

    print(f"\nDeposit invoice to be created: ${quote.deposit} (50% of ${quote.total})")
    print(f"Quote fingerprint: {fp}")
    answer = ask("Type 'approve' to create the deposit invoice, anything else to stop: ")
    if answer.strip().lower() == "approve":
        return {"decision": "approved", "fingerprint": fp, "deposit": quote.deposit}
    return {"decision": "rejected", "fingerprint": fp}


def still_matches(quote, approval):
    """True only if the quote is exactly the one the human approved."""
    return approval.get("decision") == "approved" and approval.get("fingerprint") == fingerprint(quote)
