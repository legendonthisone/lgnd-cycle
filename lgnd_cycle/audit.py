"""Audit log: every step of a run is written down, one JSON line per step.

Why: so anyone can see exactly what each agent did, and replay a run later
without AWS keys.
"""
import json, os, time, uuid

class Audit:
    def __init__(self, folder="runs"):
        os.makedirs(folder, exist_ok=True)
        self.run_id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
        self.path = os.path.join(folder, f"{self.run_id}.jsonl")

    def log(self, step, **data):
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "run": self.run_id, "step": step, **data}
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
        return rec
