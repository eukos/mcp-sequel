#!/usr/bin/env bash
# Runs inside a smoke-test container (mounted and run by run.py). Env: SPEC, PYV, EXPECTED.
set -eu
export HOME=/tmp/home
mkdir -p "$HOME/.config/mcp-sequel" /tmp/work

# throwaway sqlite db with two empty tables + a connection config pointing at it
uv run --no-project --python "$PYV" python - <<'PY'
import json, os, sqlite3
db = "/tmp/work/smoke.db"
c = sqlite3.connect(db)
c.executescript(
    "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);"
    "CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, total REAL);"
)
c.commit()
c.close()
cfg = {"type": "sqlite", "path": db, "readonly": True, "description": "smoke test db"}
with open(os.path.expanduser("~/.config/mcp-sequel/smoke.json"), "w") as f:
    json.dump(cfg, f)
PY

# install + import check (also warms the uv cache so the server below starts fast)
uv run --no-project --python "$PYV" --with "$SPEC" python -c \
    "import sys, mcp_sequel, pymysql, psycopg, paramiko, sqlglot, pydantic; print('python', sys.version.split()[0], 'imports ok')"

cat > /tmp/work/in.jsonl <<'MSG'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"smoke","version":"0"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_version","arguments":{}}}
{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"list_connections","arguments":{}}}
{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"query","arguments":{"connection":"smoke","sql":"SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"}}}
{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"query","arguments":{"connection":"smoke","sql":"DROP TABLE users"}}}
MSG

# keep stdin open long enough for all responses, then EOF stops the server
( cat /tmp/work/in.jsonl; sleep 10 ) \
    | timeout 180 uvx --python "$PYV" --from "$SPEC" mcp-sequel \
    > /tmp/work/out.jsonl 2> /tmp/work/err.txt || true

uv run --no-project --python "$PYV" python - <<'PY'
import json, os, sys

resp = {}
for line in open("/tmp/work/out.jsonl"):
    line = line.strip()
    if line.startswith("{"):
        m = json.loads(line)
        if "id" in m:
            resp[m["id"]] = m

def text(i):
    return resp[i]["result"]["content"][0]["text"]

checks = [
    ("initialize", lambda: "serverInfo" in resp[1]["result"]),
    ("tools/list has get_version, list_connections, query",
     lambda: {"get_version", "list_connections", "query"}
     <= {t["name"] for t in resp[2]["result"]["tools"]}),
    ("get_version == expected", lambda: text(3) == os.environ["EXPECTED"]),
    ("list_connections shows smoke [sqlite]",
     lambda: "smoke" in text(4) and "[sqlite]" in text(4)),
    ("query lists tables users + orders",
     lambda: not text(5).startswith("ERROR") and "users" in text(5) and "orders" in text(5)),
    ("readonly rejects DROP TABLE",
     lambda: text(6).startswith("ERROR") and "readonly" in text(6).lower()),
]

failed = 0
for name, fn in checks:
    try:
        ok = bool(fn())
    except Exception as e:
        ok = False
        name += f" ({type(e).__name__}: {e})"
    print(("  ok    " if ok else "  FAIL  ") + name)
    failed += not ok

if failed:
    print("--- server stderr ---")
    print(open("/tmp/work/err.txt").read()[-2000:])
    print("--- server stdout ---")
    print(open("/tmp/work/out.jsonl").read()[-2000:])
sys.exit(1 if failed else 0)
PY
