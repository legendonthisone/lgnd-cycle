import unittest
from lgnd_cycle.pricing import price
from lgnd_cycle.checker import check
from lgnd_cycle import gate, paypal

SPA = "Clients should be able to book an appointment online and pay a deposit when they book."

class PricingTests(unittest.TestCase):
    def test_spa_quote(self):
        q = price(4, ["booking", "payments"])
        self.assertEqual(q.total, 4 * 100 + 250 + 300)
        self.assertEqual(q.deposit, 475)

    def test_refuses_unknown_feature(self):
        with self.assertRaises(ValueError):
            price(2, ["mobile_app"])

    def test_cap_needs_human(self):
        self.assertTrue(price(15, ["payments", "booking", "cms", "user_accounts"]).needs_human)

class CheckerTests(unittest.TestCase):
    def test_pass_with_real_evidence(self):
        intake = {"pages": 4, "pages_stated": True, "out_of_scope": [],
                  "features": [{"name": "booking", "evidence": "book an appointment online"}]}
        self.assertEqual(check(SPA, intake, price(4, ["booking"]))["status"], "PASS")

    def test_blocks_invented_feature(self):
        intake = {"pages": 1, "pages_stated": True, "out_of_scope": [],
                  "features": [{"name": "booking", "evidence": "clients can book online"}]}
        v = check("A simple one-page site with our opening hours.", intake, price(1, ["booking"]))
        self.assertEqual(v["status"], "BLOCKED")

    def test_blocks_tampered_price(self):
        intake = {"pages": 2, "pages_stated": True, "out_of_scope": [], "features": []}
        q = price(2, []); q.total = 50
        self.assertEqual(check("two pages", intake, q)["status"], "BLOCKED")

class GateTests(unittest.TestCase):
    def setUp(self):
        self.q = price(4, ["booking", "payments"])
        self.ok = {"status": "PASS", "problems": [], "warnings": []}

    def test_blocked_is_never_approved(self):
        v = {"status": "BLOCKED", "problems": ["x"], "warnings": []}
        self.assertEqual(gate.review(self.q, v, ask=lambda _: "approve")["decision"], "refused_blocked")

    def test_yes_is_not_approve(self):
        self.assertEqual(gate.review(self.q, self.ok, ask=lambda _: "yes")["decision"], "rejected")

    def test_approve_then_tamper_is_refused(self):
        approval = gate.review(self.q, self.ok, ask=lambda _: "approve")
        self.q.deposit = 1
        with self.assertRaises(PermissionError):
            paypal.create_deposit_invoice(self.q, approval, "Tola", "20261023-120000-abc123")

class PayPalTests(unittest.TestCase):
    def test_dry_run_amount_is_the_deposit(self):
        q = price(4, ["booking", "payments"])
        approval = gate.review(q, {"status": "PASS", "problems": [], "warnings": []}, ask=lambda _: "approve")
        r = paypal.create_deposit_invoice(q, approval, "Tola", "20261023-120000-abc123")
        self.assertEqual(r["amount"], "475.00")
        self.assertLessEqual(len(r["invoice_number"]), 25)

    def test_sandbox_only(self):
        self.assertIn("sandbox", paypal.SANDBOX)

from lgnd_cycle import close, tracker
import os, tempfile

def fake_invoice(status="PAID", value="475.00", payment_id="5TY05013RG002845M"):
    tx = [{"payment_id": payment_id, "method": "PAYPAL", "payment_date": "2026-11-10"}] if payment_id else []
    return {"status": status, "payments": {"paid_amount": {"currency_code": "USD", "value": value},
                                           "transactions": tx}}

class CloseTests(unittest.TestCase):
    def test_paid_in_full_is_accepted(self):
        ok, _, pid, _ = close.verify_paid(fake_invoice(), 475)
        self.assertTrue(ok)
        self.assertEqual(pid, "5TY05013RG002845M")

    def test_marked_as_paid_is_not_money(self):
        self.assertFalse(close.verify_paid(fake_invoice(status="MARKED_AS_PAID"), 475)[0])

    def test_unpaid_is_refused(self):
        self.assertFalse(close.verify_paid(fake_invoice(status="UNPAID", value=None, payment_id=None), 475)[0])

    def test_wrong_amount_is_refused(self):
        self.assertFalse(close.verify_paid(fake_invoice(value="47.50"), 475)[0])

    def test_no_transaction_id_is_refused(self):
        self.assertFalse(close.verify_paid(fake_invoice(payment_id=None), 475)[0])

class TrackerTests(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "clients.json")
        self.quote = {"total": 950, "deposit": 475, "weeks": "3 to 4 weeks", "pages": 4,
                      "features": ["booking", "payments"]}

    def test_deposit_starts_clock_and_queues_balance(self):
        rec, changed = tracker.record_deposit("run1", "Tola", self.quote, "INV2-X", "PAY1", "475.00",
                                              paid_at="2026-11-10T00:00:00", path=self.path)
        self.assertTrue(changed)
        self.assertEqual(rec["status"], "BUILD_STARTED")
        self.assertEqual(rec["build_clock"]["due_by"], "2026-12-08")
        self.assertEqual(rec["next_invoices"][0]["amount"], 475)

    def test_same_payment_twice_changes_nothing(self):
        tracker.record_deposit("run1", "Tola", self.quote, "INV2-X", "PAY1", "475.00", path=self.path)
        _, changed = tracker.record_deposit("run1", "Tola", self.quote, "INV2-X", "PAY1", "475.00", path=self.path)
        self.assertFalse(changed)


if __name__ == "__main__":
    unittest.main()
