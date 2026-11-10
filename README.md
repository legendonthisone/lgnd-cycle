# LGND Cycle

A quote-to-payment agent loop for small web projects, built for the PayPal AI Hackathon.

Status: day 3 of the build. The full cycle turns once: enquiry to approved quote to PayPal sandbox invoice, paid, confirmed from PayPal's own record, and the client record updated.

## Live demo
https://legendonthisone.github.io/lgnd-cycle/

The demo page downloads the real lgnd_cycle package from this repo and runs it in your browser with Pyodide. No server, no keys. Intake answers are replayed from real Claude on Amazon Bedrock recordings. The PayPal stations show a real sandbox run (docs/recorded/), because invoice keys cannot live in a public web page.

## The cycle
enquiry -> Intake agent (AI, must quote the client's words) -> Pricing tool (code) -> Checker (code) -> Approval gate (human types 'approve') -> PayPal sandbox invoice for the 50% deposit (code, re-checked against the approved quote fingerprint) -> send -> client pays -> confirm PAID from PayPal (code, never the AI) -> Tracker starts the build clock and queues the balance invoice

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
