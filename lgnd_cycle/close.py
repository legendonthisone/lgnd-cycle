"""Close the cycle: send the deposit invoice, then confirm it was paid.

Usage (Windows PowerShell, inside the venv):
  python -m lgnd_cycle.close send  runs/<run>.jsonl
  python -m lgnd_cycle.close check runs/<run>.jsonl

Rule: only PayPal decides that money arrived. The AI never says "paid".
'check' asks PayPal for the invoice and accepts it only if:
1. the status is PAID (not MARKED_AS_PAID, which is just the seller's word),
2. the paid amount equals the approved deposit, to the cent,
3. there is a real PayPal transaction id.
Then the tracker updates the client record.
"""
import argparse, json
from .audit import Audit
from . import paypal, tracker


def read_run(path):
    """Pull what we need out of a run's audit log."""
    steps = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rec = json.loads(line)
                steps[rec["step"]] = rec          # last one of each step wins
    inv = steps.get("invoice_created")
    if not inv or inv.get("mode") != "sandbox":
        raise RuntimeError("this run has no sandbox invoice; run the cycle with --paypal sandbox first")
    if steps.get("gate", {}).get("decision") != "approved":
        raise RuntimeError("this run was never approved at the gate")
    return {"run_id": inv["run"], "invoice_id": inv["invoice_id"],
            "client_name": steps.get("intake_done", {}).get("intake", {}).get("client_name"),
            "quote": steps["priced"]["quote"], "deposit": steps["gate"]["deposit"]}


def reopen(run_id):
    """Append to the same audit log, so one run tells the whole story."""
    a = Audit.__new__(Audit)
    a.run_id = run_id
    a.path = f"runs/{run_id}.jsonl"
    return a


def verify_paid(inv, expected_deposit):
    """Pure check of PayPal's invoice. Returns (ok, reason, payment_id, paid_value)."""
    status = inv.get("status")
    pay = inv.get("payments") or {}
    paid = (pay.get("paid_amount") or {}).get("value")
    txs = [t for t in pay.get("transactions", []) if t.get("payment_id")]
    if status != "PAID":
        return False, f"PayPal status is {status}, not PAID", None, paid
    if paid is None or round(float(paid), 2) != round(float(expected_deposit), 2):
        return False, f"paid {paid} does not match approved deposit {expected_deposit}", None, paid
    if not txs:
        return False, "no PayPal transaction id on the invoice", None, paid
    return True, "paid in full", txs[-1]["payment_id"], paid


def payer_link(inv):
    return (inv.get("detail", {}).get("metadata") or {}).get("recipient_view_url")


def cmd_send(run):
    paypal.load_env()
    token = paypal._token()
    path = f"/v2/invoicing/invoices/{run['invoice_id']}"
    inv = paypal._call("GET", path, token=token)
    audit = reopen(run["run_id"])
    if inv.get("status") == "DRAFT":
        has_email = any(r.get("billing_info", {}).get("email_address")
                        for r in inv.get("primary_recipients", []))
        r = paypal._call("POST", path + "/send", token=token,
                         body={"send_to_recipient": has_email, "send_to_invoicer": False},
                         headers={"PayPal-Request-Id": run["run_id"] + "-send"})
        inv = paypal._call("GET", path, token=token)
        link = r.get("href") or payer_link(inv)
        audit.log("invoice_sent", invoice_id=run["invoice_id"], status=inv.get("status"),
                  emailed=has_email, payer_link=link)
        print(f"Sent. PayPal status now {inv.get('status')}.")
    else:
        link = payer_link(inv)
        print(f"Already sent earlier. PayPal status is {inv.get('status')}.")
    print("Open this link and pay as the SANDBOX buyer:\n ", link)


def cmd_check(run):
    paypal.load_env()
    token = paypal._token()
    inv = paypal._call("GET", f"/v2/invoicing/invoices/{run['invoice_id']}", token=token)
    ok, reason, payment_id, paid = verify_paid(inv, run["deposit"])
    audit = reopen(run["run_id"])
    if not ok:
        audit.log("payment_not_confirmed", invoice_id=run["invoice_id"], reason=reason)
        print("NOT PAID YET:", reason)
        return
    audit.log("deposit_confirmed", invoice_id=run["invoice_id"], payment_id=payment_id, amount=paid)
    paid_at = None
    for t in inv["payments"].get("transactions", []):
        if t.get("payment_id") == payment_id and t.get("payment_date"):
            paid_at = t["payment_date"][:10] + "T00:00:00"
    rec, changed = tracker.record_deposit(run["run_id"], run["client_name"], run["quote"],
                                          run["invoice_id"], payment_id, paid, paid_at=paid_at)
    if changed:
        audit.log("tracker_updated", status=rec["status"], due_by=rec["build_clock"]["due_by"],
                  queued=rec["next_invoices"])
    print(f"PAID. ${paid} confirmed by PayPal (payment {payment_id}).")
    print(f"Tracker: {rec['client_name']} is {rec['status']}, build due by {rec['build_clock']['due_by']}, "
          f"balance invoice ${rec['next_invoices'][0]['amount']} queued for launch."
          + ("" if changed else " (already recorded, nothing changed)"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["send", "check"])
    ap.add_argument("run_log")
    a = ap.parse_args()
    run = read_run(a.run_log)
    (cmd_send if a.action == "send" else cmd_check)(run)


if __name__ == "__main__":
    main()
