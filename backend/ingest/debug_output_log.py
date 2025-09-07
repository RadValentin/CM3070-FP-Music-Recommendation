import re
from collections import Counter

LOG_PATH = "output.txt" 

def summarize_missing_data_reasons(path: str):
    pattern = re.compile(r"^Missing data in JSON string \((.*?)\)")
    counts = Counter()
    total = 0
    
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = pattern.search(line)
            if m:
                total += 1
                counts[m.group(1).strip()] += 1

    print(f"Total 'Missing data in JSON string (...)' lines: {total}")
    if counts:
        for reason, n in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
            print(f"{reason}: {n}")
    else:
        print("No matching lines found.")

summarize_missing_data_reasons(LOG_PATH)
