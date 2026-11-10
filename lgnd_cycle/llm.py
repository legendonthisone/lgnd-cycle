"""One door to the AI model, with three modes.

live   : calls Amazon Bedrock and saves the answer to fixtures/ (a recording)
replay : reads a saved recording instead of calling AWS (no keys, no cost)
mock   : reads a hand-written test answer (for tests only)
"""
import json, os

MODEL_ID = os.getenv("LGND_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
REGION = os.getenv("AWS_REGION", "us-east-1")


def call_tool(mode, name, system, user_text, tool_schema, fixture_key):
    rec_path = os.path.join("fixtures", f"recorded_{fixture_key}.json")
    mock_path = os.path.join("fixtures", f"mock_{fixture_key}.json")
    if mode == "replay":
        with open(rec_path, encoding="utf-8") as fh:
            return json.load(fh)
    if mode == "mock":
        with open(mock_path, encoding="utf-8") as fh:
            return json.load(fh)

    import boto3  # only needed in live mode
    client = boto3.client("bedrock-runtime", region_name=REGION)
    resp = client.converse(
        modelId=MODEL_ID,
        system=[{"text": system}],
        messages=[{"role": "user", "content": [{"text": user_text}]}],
        toolConfig={
            "tools": [{"toolSpec": {"name": name, "description": "Return the structured result.",
                                    "inputSchema": {"json": tool_schema}}}],
            "toolChoice": {"tool": {"name": name}},
        },
        inferenceConfig={"maxTokens": 1500, "temperature": 0},
    )
    for block in resp["output"]["message"]["content"]:
        if "toolUse" in block:
            result = block["toolUse"]["input"]
            os.makedirs("fixtures", exist_ok=True)
            with open(rec_path, "w", encoding="utf-8") as fh:
                json.dump(result, fh, indent=2)
            return result
    raise RuntimeError("model did not return structured output")
