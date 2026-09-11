import json
import os

TRANSCRIPT = os.environ.get(
    "TRANSCRIPT",
    r"C:\Users\hi\.cursor\projects\c-Users-hi-Documents-cloud-suvisdev\agent-transcripts"
    r"\28f8454d-09f0-4e1f-bc66-c2a6face1ab6\28f8454d-09f0-4e1f-bc66-c2a6face1ab6.jsonl",
)
BASE = os.path.join(
    os.path.dirname(__file__),
    "..",
    "apps",
    "mova",
    "adapter",
    "outbound",
    "http",
)
os.makedirs(BASE, exist_ok=True)

for line in open(TRANSCRIPT, encoding="utf-8"):
    if "tmdb_adapter.py" not in line:
        continue
    obj = json.loads(line)
    for part in obj.get("message", {}).get("content", []):
        inp = part.get("input") or {}
        if str(inp.get("path", "")).endswith("tmdb_adapter.py") and inp.get("contents"):
            path = os.path.join(BASE, "tmdb_adapter.py")
            with open(path, "w", encoding="utf-8") as f:
                f.write(inp["contents"])
            print("wrote", path, len(inp["contents"]))
            break
    else:
        continue
    break

for line in open(TRANSCRIPT, encoding="utf-8"):
    if "kofic_adapter.py" not in line:
        continue
    obj = json.loads(line)
    for part in obj.get("message", {}).get("content", []):
        inp = part.get("input")
        if isinstance(inp, dict) and str(inp.get("path", "")).endswith("kofic_adapter.py"):
            contents = inp.get("contents")
            if contents:
                path = os.path.join(BASE, "kofic_adapter.py")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(contents)
                print("wrote", path, len(contents))
                raise SystemExit(0)
        if not isinstance(inp, dict):
            continue
        patch = inp.get("input", "")
        if "kofic_adapter.py" not in str(patch):
            continue
        body = []
        for ln in str(patch).split("\n"):
            if ln.startswith("+") and not ln.startswith("+++"):
                body.append(ln[1:])
        if body:
            path = os.path.join(BASE, "kofic_adapter.py")
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(body))
            print("wrote", path, len(body))
            raise SystemExit(0)
