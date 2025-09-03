import os, sys, time, orjson
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

ROOT = Path("D:/Datasets/AcousticBrainz/Sample/acousticbrainz-highlevel-sample-json-20220623-0")  # change if needed
OUT = Path("D:/Datasets/AcousticBrainz/Sample/merged-highlevel-0.ndjson")
WORKERS = max(8, (os.cpu_count() or 8))  # threads; orjson releases the GIL
BATCH = 4000  # files per task; tune 2000–20000


def list_jsons(root: Path):
    json_paths = []
    for root, dirs, files in os.walk(root):
        for name in files:
            if name.lower().endswith(".json"):
                json_paths.append(os.path.join(root, name))
            else:
                print(f"Non-JSON file skipped: {name}")
    return json_paths


def chunks(iterable, n):
    buf = []
    for x in iterable:
        buf.append(x)
        if len(buf) >= n:
            yield buf
            buf = []
    if buf:
        yield buf


def process_batch(paths):
    out = []
    for path in paths:
        try:
            with open(path, "rb") as f:
                obj = orjson.loads(f.read())
            out.append(orjson.dumps(obj) + b"\n")  # compact NDJSON line
        except Exception:
            # skip bad JSON; keep it lean
            pass
    return b"".join(out)


def main():
    t0 = time.perf_counter()
    files = list_jsons(ROOT)
    total = len(files)
    print(
        f"Found {total:,} JSON files. Using {WORKERS} threads, batch={BATCH}",
        flush=True,
    )

    written = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex, open(
        OUT, "wb", buffering=1024 * 1024
    ) as out:
        for block in ex.map(process_batch, chunks(files, BATCH), chunksize=8):
            if block:
                out.write(block)
                written += block.count(b"\n")

    dt = time.perf_counter() - t0
    rate = written / dt if dt else 0
    print(f"Wrote {written:,} lines to {OUT} in {dt:.2f}s  (~{rate:,.0f} rec/s)")


if __name__ == "__main__":
    main()
