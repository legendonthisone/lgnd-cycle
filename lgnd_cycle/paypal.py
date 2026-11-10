"""PayPal step: turn an approved quote into a 50% deposit invoice (sandbox only).

Plain code, no AI. The amount comes from the pricing tool, never from a model.

Safety rails:
1. Sandbox only. The live PayPal address is not in this file, so real money
   cannot move even by mistake.
2. Keys come from the local .env file and are never printed or logged.
3. Re-check before money: the quote must match the human's approval fingerprint.
4. Idempotent: each run sends a PayPal-Request-Id, so a network retry returns
   the same invoice instead of creating a second one.
5. After PayPal replies, the invoice amount is compared with the deposit.
   If they differ, the run stops loudly.
"""
import base64, json, os, urllib.request, urllib.error
from .gate import still_matches

SANDBOX = "https://api-m.sandbox.paypal.com"


def load_env(path=".env"):
    """Read KEY=VALUE lines from .env into the environment (no extra library)."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def invoice_body(quote, client_name, run_id, client_email=None):
    """Build the invoice PayPal will store. Pure function, easy to test."""
    number = "LGND-" + run_id.replace("-", "")[2:]          # PayPal allows max 25 chars
    recipient = {"billing_info": {"name": {"full_name": client_name or "Client"}}}
    if client_email:
        recipient["billing_info"]["email_address"] = client_email
    return {
        "detail": {
            "invoice_number": number,
            "currency_code": "USD",
            "note": f"50% deposit to start the build. Total project: ${quote.total}. "
                    f"Timeline: {quote.weeks}. The balance is due at launch.",
            "payment_term": {"term_type": "DUE_ON_RECEIPT"},
        },
        "invoicer": {"business_name": "LGND Studio", "website": "https://legendonthisone.com"},
        "primary_recipients": [recipient],
        "items": [{
            "name": "Deposit (50%)",
            "description": f"{quote.pages} page(s); add-ons: {', '.join(quote.features) or 'none'}",
            "quantity": "1",
            "unit_amount": {"currency_code": "USD", "value": f"{quote.deposit:.2f}"},
            "unit_of_measure": "AMOUNT",
        }],
    }


def _call(method, path, token=None, body=None, headers=None, basic=None):
    h = {"Content-Type": "application/json", **(headers or {})}
    if token:
        h["Authorization"] = f"Bearer {token}"
    if basic:
        h["Authorization"] = "Basic " + base64.b64encode(basic.encode()).decode()
    data = body.encode() if isinstance(body, str) else (json.dumps(body).encode() if body else None)
    req = urllib.request.Request(SANDBOX + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        raise RuntimeError(f"PayPal said {e.code}: {detail}") from None


def _token():
    cid, secret = os.getenv("PAYPAL_CLIENT_ID"), os.getenv("PAYPAL_CLIENT_SECRET")
    if not cid or not secret:
        raise RuntimeError("PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET missing from .env")
    r = _call("POST", "/v1/oauth2/token", body="grant_type=client_credentials",
              headers={"Content-Type": "application/x-www-form-urlencoded"}, basic=f"{cid}:{secret}")
    return r["access_token"]


def create_deposit_invoice(quote, approval, client_name, run_id, mode="off", client_email=None):
    """mode 'off' = dry run (shows what would be sent). mode 'sandbox' = real sandbox call."""
    if not still_matches(quote, approval):
        raise PermissionError("quote does not match the approved fingerprint; refusing to invoice")

    body = invoice_body(quote, client_name, run_id, client_email)
    if mode == "off":
        return {"mode": "dry_run", "invoice_number": body["detail"]["invoice_number"],
                "amount": body["items"][0]["unit_amount"]["value"]}
    if mode != "sandbox":
        raise ValueError("mode must be 'off' or 'sandbox'")

    load_env()
    token = _token()
    inv = _call("POST", "/v2/invoicing/invoices", token=token, body=body,
                headers={"PayPal-Request-Id": run_id, "Prefer": "return=representation"})

    got = inv.get("amount", {}).get("value")
    if got is None or float(got) != float(quote.deposit):
        raise RuntimeError(f"PayPal invoice amount {got} does not match deposit {quote.deposit}; stop")
    return {"mode": "sandbox", "invoice_id": inv.get("id"), "status": inv.get("status"),
            "invoice_number": inv.get("detail", {}).get("invoice_number"), "amount": got}
