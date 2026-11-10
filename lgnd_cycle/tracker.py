"""Tracker: the client record. This is the oxaloacetate of the cycle.

When PayPal confirms the deposit, the tracker:
1. Marks the client's deposit as paid (with PayPal's own payment id as proof).
2. Starts the build clock and sets a due date from the quoted timeline.
3. Queues the balance invoice for the next turn of the cycle.

Plain code, no AI. Idempotent: recording the same PayPal payment twice changes
nothing, so a retry can never double count money.
"""
import json, os, re
from datetime import datetime, timedelta

DEFAULT_PATH = os.path.join("tracker", "clients.json")


def _load(path):
    if not os.path.exists(path):
        return {"clients": {}}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _save(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    os.replace(tmp, path)


def build_weeks(weeks_text):
    """'3 to 4 weeks' -> 4, 'about 2 weeks' -> 2. Plan for the longest promise."""
    nums = [int(n) for n in re.findall(r"\d+", weeks_text or "")]
    return max(nums) if nums else 2


def record_deposit(run_id, client_name, quote, invoice_id, payment_id, paid_amount,
                   paid_at=None, path=DEFAULT_PATH):
    """Write the paid deposit into the client record. Returns (record, changed)."""
    data = _load(path)
    rec = data["clients"].get(run_id)
    if rec and rec.get("deposit", {}).get("payment_id") == payment_id:
        return rec, False                     # already recorded, do nothing

    start = datetime.fromisoformat(paid_at) if paid_at else datetime.now()
    weeks = build_weeks(quote.get("weeks"))
    balance = quote["total"] - quote["deposit"]
    rec = {
        "client_name": client_name,
        "run_id": run_id,
        "status": "BUILD_STARTED",
        "quote": {"total": quote["total"], "deposit": quote["deposit"], "weeks": quote.get("weeks"),
                  "pages": quote.get("pages"), "features": quote.get("features", [])},
        "deposit": {"invoice_id": invoice_id, "payment_id": payment_id,
                    "amount": paid_amount, "paid_at": start.isoformat(timespec="seconds"),
                    "confirmed_by": "PayPal invoice status PAID"},
        "build_clock": {"started_at": start.isoformat(timespec="seconds"),
                        "due_by": (start + timedelta(weeks=weeks)).date().isoformat()},
        "next_invoices": [{"type": "balance", "amount": balance, "trigger": "at launch",
                           "status": "QUEUED"}],
    }
    data["clients"][run_id] = rec
    _save(path, data)
    return rec, True
