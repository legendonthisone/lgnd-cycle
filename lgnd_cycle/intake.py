"""Intake agent: reads a client's message and pulls out the facts.

Rule: every feature it lists must come with an EXACT quote from the message
as evidence. That makes its claims checkable by plain code later.
"""
from .llm import call_tool
from .pricing import ADDONS

SYSTEM = (
    "You are the intake agent for LGND, a Lagos web studio. Read the client's enquiry "
    "and extract only what the client actually asked for. Never add features they did not ask for. "
    "For each feature, copy the exact words from the enquiry that show they asked for it. "
    "If the number of pages is not stated, estimate it from the pages they name and set pages_stated to false. "
    "Allowed features: " + ", ".join(ADDONS) + ". If they ask for something outside this list, put it in out_of_scope."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "client_name": {"type": "string"},
        "business_type": {"type": "string"},
        "pages": {"type": "integer"},
        "pages_stated": {"type": "boolean"},
        "page_names": {"type": "array", "items": {"type": "string"}},
        "features": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string", "enum": list(ADDONS)},
            "evidence": {"type": "string"}}, "required": ["name", "evidence"]}},
        "out_of_scope": {"type": "array", "items": {"type": "string"}},
        "deadline": {"type": "string"},
    },
    "required": ["client_name", "pages", "pages_stated", "features", "out_of_scope"],
}


def run(enquiry_text, mode, fixture_key):
    return call_tool(mode, "record_intake", SYSTEM, enquiry_text, SCHEMA, f"intake_{fixture_key}")
