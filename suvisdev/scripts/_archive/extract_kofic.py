import json
import os

TRANSCRIPT = (
    r"C:\Users\hi\.cursor\projects\c-Users-hi-Documents-cloud-suvisdev\agent-transcripts"
    r"\28f8454d-09f0-4e1f-bc66-c2a6face1ab6\28f8454d-09f0-4e1f-bc66-c2a6face1ab6.jsonl"
)
OUT = os.path.join(
    os.path.dirname(__file__),
    "..",
    "apps",
    "mova",
    "adapter",
    "outbound",
    "http",
    "kofic_adapter.py",
)

lines = open(TRANSCRIPT, encoding="utf-8").readlines()
for idx in (1629, 1632, 1637):
    if idx >= len(lines):
        continue
    obj = json.loads(lines[idx])
    for part in obj.get("message", {}).get("content", []):
        if part.get("name") != "ApplyPatch":
            continue
        patch = part.get("input")
        if isinstance(patch, str) and "kofic_adapter" in patch:
            body = []
            for ln in patch.split("\n"):
                if ln.startswith("+") and not ln.startswith("+++"):
                    body.append(ln[1:])
            if len(body) > 20:
                os.makedirs(os.path.dirname(OUT), exist_ok=True)
                with open(OUT, "w", encoding="utf-8") as f:
                    f.write("\n".join(body))
                print("wrote from line", idx, "lines", len(body))
                raise SystemExit(0)
print("not found")
