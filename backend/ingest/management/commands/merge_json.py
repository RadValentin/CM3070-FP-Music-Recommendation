import os, time, orjson
from dotenv import dotenv_values
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Merges the large number of individual JSON files from AcousticBrainz dataset into NDJSON for faster loading."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sample",
            action="store_true",
            help="Use the sample dataset instead of full high-level paths.",
        )
        parser.add_argument(
            "--parts",
            type=int,
            default=None,
            help="How many of the 30 AB dumps to use, each folder has 1M records (optional).",
        )
        parser.add_argument(
            "--parts_list",
            type=str,
            default=None,
            help="List of part indexes to process (optional).",
        )

    def handle(self, *args, **options):
        try:
            if options["parts_list"]:
                parts_list = [int(part) for part in options["parts_list"].split(",")]
                merge_json(use_sample=options["sample"], parts_list=parts_list)
            elif options["parts"]:
                merge_json(use_sample=options["sample"], num_parts=options["parts"])
            else:
                merge_json(use_sample=options["sample"])
        except Exception as e:
            raise CommandError(str(e))

        self.stdout.write(self.style.SUCCESS("Merge complete."))


WORKERS = max(8, (os.cpu_count() or 8))
BATCH = 4000


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
            out.append(orjson.dumps(obj) + b"\n")
        except Exception as e:
            print(f"Error processing {path}: {e}")
    return b"".join(out)


def merge_json(use_sample: bool, num_parts: int = None, parts_list: list = None):
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
    config = dotenv_values(BASE_DIR / ".env")

    if use_sample:
        # 100k records
        dataset_path = config.get("AB_SAMPLE_ROOT")
    else:
        # 1M records
        dataset_path = config.get("AB_HIGHLEVEL_ROOT")

    # Dumps are split into parts of 1M, restrict how many we load
    parts_dirs = [
        os.path.join(dataset_path, fname)
        for fname in os.listdir(dataset_path)
        if os.path.isdir(os.path.join(dataset_path, fname))
    ]
    if parts_list:
        parts_dirs = [parts_dirs[i] for i in parts_list]
    elif num_parts:
        parts_dirs = parts_dirs[:num_parts]

    for i, dir in enumerate(parts_dirs):
        start = time.perf_counter()
        files = list_jsons(dir)
        total = len(files)
        print(
            f"({i+1}/{len(parts_dirs)}) Found {total:,} JSON files. Using {WORKERS} threads, batch={BATCH}",
            flush=True,
        )

        written = 0
        # if you specify --parts_list 2,5,7, the output files will be 
        # merged-2.ndjson, merged-5.ndjson, merged-7.ndjson
        part_index = parts_list[i] if parts_list else i
        OUT = os.path.join(dataset_path, f"merged-{part_index}.ndjson")
        with ThreadPoolExecutor(max_workers=WORKERS) as ex, open(
            OUT, "wb", buffering=1024 * 1024
        ) as out:
            for block in ex.map(process_batch, chunks(files, BATCH), chunksize=8):
                if block:
                    out.write(block)
                    written += block.count(b"\n")

        end = time.perf_counter() - start
        rate = written / end if end else 0
        print(f"Wrote {written:,} lines to {OUT} in {end:.2f}s  (~{rate:,.0f} rec/s)")
