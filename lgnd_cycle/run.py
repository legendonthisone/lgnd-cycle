"""The cycle: enquiry -> Intake -> Pricing -> Checker -> Approval gate -> PayPal deposit invoice.

Usage:
  python -m lgnd_cycle.run samples/enquiry_spa.txt --mode mock
  python -m lgnd_cycle.run samples/enquiry_spa.txt --mode live     (needs AWS)
  python -m lgnd_cycle.run samples/enquiry_spa.txt --mode replay   (re-uses a live recording)
  add --paypal sandbox to create a real PayPal SANDBOX invoice after you approve
"""
import argparse, json, os
from dataclasses import asdict
from .audit import Audit
from . import intake as intake_agent
from .pricing import price
from .checker import check
from . import gate, paypal


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("enquiry")
    ap.add_argument("--mode", choices=["live", "replay", "mock"], default="mock")
    ap.add_argument("--paypal", choices=["off", "sandbox"], default="off",
                    help="off = dry run, sandbox = create a PayPal sandbox invoice")
    ap.add_argument("--client-email", default=None, help="sandbox buyer email (optional)")
    a = ap.parse_args()

    key = os.path.splitext(os.path.basename(a.enquiry))[0]
    text = open(a.enquiry, encoding="utf-8").read()
    audit = Audit()
    audit.log("enquiry_received", source=a.enquiry, mode=a.mode, paypal=a.paypal)

    facts = intake_agent.run(text, a.mode, key)
    audit.log("intake_done", intake=facts)

    try:
        quote = price(facts["pages"], [f["name"] for f in facts.get("features", [])])
    except ValueError as e:
        audit.log("pricing_refused", reason=str(e))
        print("PRICING REFUSED:", e)
        return
    audit.log("priced", quote=asdict(quote))

    verdict = check(text, facts, quote)
    audit.log("checked", verdict=verdict)

    print(f"\nClient: {facts.get('client_name')}  |  pages: {quote.pages}  |  features: {', '.join(quote.features) or 'none'}")
    for li in quote.line_items:
        print(f"  {li['item']:<35} ${li['usd']}")
    print(f"  {'TOTAL':<35} ${quote.total}   deposit (50%): ${quote.deposit}   timeline: {quote.weeks}")
    print(f"\nChecker: {verdict['status']}")
    for p in verdict["problems"]:
        print("  BLOCK:", p)
    for w in verdict["warnings"]:
        print("  REVIEW:", w)

    approval = gate.review(quote, verdict)
    audit.log("gate", **approval)
    if approval["decision"] != "approved":
        print("\nStopped at the approval gate:", approval["decision"])
        print("Audit log:", audit.path)
        return

    try:
        inv = paypal.create_deposit_invoice(quote, approval, facts.get("client_name"),
                                            audit.run_id, mode=a.paypal, client_email=a.client_email)
    except Exception as e:
        audit.log("invoice_failed", error=str(e))
        print("\nINVOICE FAILED:", e)
        print("Audit log:", audit.path)
        return
    audit.log("invoice_created", **inv)
    if inv["mode"] == "dry_run":
        print(f"\nDry run: would create invoice {inv['invoice_number']} for ${inv['amount']}. Add --paypal sandbox to do it for real (sandbox).")
    else:
        print(f"\nPayPal sandbox invoice created: {inv['invoice_id']}  status {inv['status']}  amount ${inv['amount']}")
    print("Audit log:", audit.path)


if __name__ == "__main__":
    main()
