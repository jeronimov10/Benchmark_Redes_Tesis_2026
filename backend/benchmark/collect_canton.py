"""Recolecta una ventana reciente de eventos de Canton desde la Scan API del espejo publico (resultados/raw/canton)."""
import json
import os
import time
import urllib.request
import urllib.error

BASE = "https://api.cantonnodes.com"
OUT_RAW = "resultados/raw/canton"
PAGE_SIZE = 200
MAX_PAGES = int(os.environ.get("MAX_PAGES", 40))
START_AFTER = {"after_record_time": os.environ.get("CANTON_START_AFTER", "2026-09-07T14:00:00Z"), "after_migration_id": int(os.environ.get("CANTON_MIGRATION_ID", 4))}


def post(path, payload, retries=8):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        BASE + path, data=body, headers={"Content-Type": "application/json", "User-Agent": "bench/1.0"}
    )
    delay = 5.0
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(delay)
                delay *= 1.6
                continue
            raise


def get(path, retries=6):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "bench/1.0"})
    delay = 4.0
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(delay)
                delay *= 1.6
                continue
            raise


def main():
    dso = get("/v0/dso")
    with open(f"{OUT_RAW}/dso_state.json", "w") as f:
        json.dump(dso, f, indent=2)
    print("amuletPrice:", dso["data"].get("amulet_rules", {}) if False else "ver dso_state.json")

    events = []
    cursor = START_AFTER
    for page in range(MAX_PAGES):
        payload = {"after": cursor, "page_size": PAGE_SIZE}
        resp = post("/v0/events", payload)
        batch = resp.get("events", [])
        print(f"pagina {page}: {len(batch)} eventos, cursor={cursor}")
        if not batch:
            break
        events.extend(batch)
        last = batch[-1]
        rt = (last.get("verdict") or last.get("update") or {}).get("record_time")
        mid = (last.get("verdict") or last.get("update") or {}).get("migration_id", 4)
        if not rt:
            break
        cursor = {"after_record_time": rt, "after_migration_id": mid}
        time.sleep(1.5)

    with open(f"{OUT_RAW}/events_sample.json", "w") as f:
        json.dump(events, f)
    print(f"Total eventos recolectados: {len(events)}")


if __name__ == "__main__":
    main()
