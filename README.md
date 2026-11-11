# LGND Cycle

A quote-to-payment agent loop for small web studios, built for the PayPal AI Hackathon.

The AI reads the client's enquiry. Plain code sets the price and checks the AI. A human approves. PayPal invoices the deposit. And only PayPal's own record can mark it paid, never the AI.

## Live demo and video
- Live demo: https://legendonthisone.github.io/lgnd-cycle/
- Demo video (under 3 minutes): https://youtu.be/PLvkqaeUYM4

The demo page downloads the real lgnd_cycle package from this repo and runs it in your browser with Pyodide. No server, no keys. Intake answers are replayed from real Claude on Amazon Bedrock recordings. The PayPal stations show a real sandbox run (docs/recorded/), marked in blue, because invoice keys cannot live in a public web page.

## Status
Complete for the hackathon. One full turn of the cycle has run end to end in the PayPal sandbox: a $475 deposit invoice was created, sent, paid by a sandbox buyer and confirmed PAID from PayPal's own record. The tracker then started the build clock and queued the $475 balance invoice. 18 tests pass.

## The cycle
enquiry -> Intake agent (AI, must quote the client's words) -> Pricing tool (code) -> Checker (code) -> Approval gate (human types 'approve') -> PayPal sandbox invoice for the 50% deposit (code, re-checked against the approved quote fingerprint) -> send -> client pays -> confirm PAID from PayPal (code, never the AI) -> Tracker starts the build clock and queues the balance invoice

It is modelled on the Krebs cycle: the client record is regenerated at the end of every turn, ready for the next invoice.

## PayPal technology used
All calls go to the PayPal sandbox only (https://api-m.sandbox.paypal.com).
- OAuth 2.0 client credentials: POST /v1/oauth2/token
- Invoicing API v2: POST /v2/invoicing/invoices to create the deposit invoice, then POST /v2/invoicing/invoices/{id}/send to send it to the client
- Invoicing API v2: GET /v2/invoicing/invoices/{id} to confirm payment. The loop accepts "paid" only if the status is PAID, the amount matches to the cent and PayPal returns a real transaction id. MARKED_AS_PAID is refused.

## AI tools used
1. **Claude Sonnet 4.5 on Amazon Bedrock** (inside the product). This is the Intake agent. It is called through the Bedrock Converse API with forced tool use and temperature 0, reads the client's enquiry and returns pages, features and deadline as structured data. Every feature must quote the client's exact words, so the Checker can prove it was asked for. The AI never sets a price, approves a quote or marks anything paid. Its answers are recorded to fixtures/ so the demo and tests replay them without keys.
2. **Claude by Anthropic, in Claude Cowork** (to build the product). Used as a coding and writing assistant: it helped write and review the Python code, the tests, the browser demo page, this README and the demo video script. The PayPal sandbox runs were done on my own laptop with my own sandbox keys.

## Run it (Windows PowerShell)
    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    python -m unittest discover tests
    python -m lgnd_cycle.run samples/enquiry_spa.txt --mode mock
    python -m lgnd_cycle.run samples/enquiry_spa.txt --mode replay --paypal sandbox
    python -m lgnd_cycle.close send  runs/<run>.jsonl
    python -m lgnd_cycle.close check runs/<run>.jsonl

If .venv\Scripts\activate is blocked by PowerShell, call .venv\Scripts\python.exe directly instead.

The PayPal step only ever talks to the PayPal sandbox. Keys live in a local .env file (see .env.example) and are never committed.

## Prior work disclosure
LGND's pricing rules (USD 100 per page plus fixed add-ons, 50% deposit) existed before the hackathon. All code in this repo was written during the hackathon.

All clients in samples/ are fictional.

## License
MIT. See LICENSE.
