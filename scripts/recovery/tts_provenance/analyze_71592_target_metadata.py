from __future__ import annotations
import csv, json, re, zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(".cache/aihub71592")
LABEL_ROOT = ROOT / "labels_tl"
EXT = ROOT / "interviewer_clustering_extended"
NEW = ROOT / "seeded_new_matches"
OUT = ROOT / "target_metadata_analysis"
OUT.mkdir(parents=True, exist_ok=True)

# Experienced target clusters recovered at threshold 0.982.
exp_rows = list(csv.DictReader((EXT / "cluster_members.csv").open(encoding="utf-8-sig")))
targets = {
    "questioner": [r for r in exp_rows if r["cluster"] == "C008"],
    "coach": [r for r in exp_rows if r["cluster"] == "C027"],
}

# Add only high-confidence New matches from the 3 scanned New archives.
new_rows = list(csv.DictReader((NEW / "matches.csv").open(encoding="utf-8-sig")))
for role in ("questioner", "coach"):
    targets[role] += [
        r for r in new_rows
        if r["best_role"] == role and r["confidence"] == "high"
    ]

wanted = {}
for role, rows in targets.items():
    for r in rows:
        wanted[r["wav"]] = role

def numeric_id(wav):
    m = re.search(r"_(\d+)\.wav$", wav)
    return int(m.group(1)) if m else None

metadata = {}
for zpath in sorted(LABEL_ROOT.rglob("*.zip")):
    with zipfile.ZipFile(zpath) as zf:
        for name in zf.namelist():
            if not name.lower().endswith(".json"):
                continue
            base = Path(name).name
            # Convert ckmk_d_* -> ckmk_q_*
            wav = re.sub(r"^ckmk_d_", "ckmk_q_", base[:-5] + ".wav")
            if wav not in wanted:
                continue
            obj = json.loads(zf.read(name).decode("utf-8-sig"))
            ds = obj["dataSet"]
            info = ds["info"]
            qraw = ds["question"]["raw"]
            rawa = obj["rawDataInfo"]["question"]
            metadata[wav] = {
                "role": wanted[wav],
                "wav": wav,
                "id": numeric_id(wav),
                "label_zip": zpath.name,
                "date": info.get("date"),
                "occupation": info.get("occupation"),
                "gender": info.get("gender"),
                "ageRange": info.get("ageRange"),
                "experience": info.get("experience"),
                "question": qraw.get("text", ""),
                "wordCount": qraw.get("wordCount"),
                "duration_ms": rawa.get("duration"),
                "audioPath": rawa.get("audioPath"),
            }

missing = sorted(set(wanted) - set(metadata))
print("wanted", len(wanted), "metadata", len(metadata), "missing", len(missing))
if missing:
    print("missing examples:", missing[:20])

fields = [
    "role","wav","id","date","occupation","gender","ageRange","experience",
    "wordCount","duration_ms","question","label_zip","audioPath"
]
with (OUT/"target_metadata.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(sorted(metadata.values(), key=lambda r:(r["role"],r["id"] or -1)))

for role in ("questioner","coach"):
    rows = [r for r in metadata.values() if r["role"] == role]
    print(f"\n=== {role} n={len(rows)} ===")
    print("dates:", Counter(r["date"] for r in rows))
    print("experience:", Counter(r["experience"] for r in rows))
    print("occupation:", Counter(r["occupation"] for r in rows))
    print("gender(applicant):", Counter(r["gender"] for r in rows))
    print("ageRange(applicant):", Counter(r["ageRange"] for r in rows))

    durs = sorted(int(r["duration_ms"]) for r in rows if r["duration_ms"] is not None)
    words = sorted(int(r["wordCount"]) for r in rows if r["wordCount"] is not None)
    if durs:
        import statistics
        print("duration_ms min/median/max:", durs[0], int(statistics.median(durs)), durs[-1])
    if words:
        import statistics
        print("wordCount min/median/max:", words[0], int(statistics.median(words)), words[-1])

    qcount = Counter(re.sub(r"\s+"," ",r["question"].strip()) for r in rows)
    repeated = [(q,n) for q,n in qcount.items() if n>1]
    repeated.sort(key=lambda x:(-x[1],x[0]))
    print("unique questions:", len(qcount), "repeated exact texts:", len(repeated))
    for q,n in repeated[:10]:
        print("  repeat",n,":",q[:120])

    # Near-consecutive numeric ID runs. Global IDs often reveal recording-session batches.
    ids = sorted((r["id"],r["wav"]) for r in rows if r["id"] is not None)
    gaps = Counter()
    for (a,_),(b,_) in zip(ids, ids[1:]):
        gaps[min(b-a, 9999)] += 1
    print("ID gaps <=10:", {g:gaps[g] for g in range(1,11) if gaps[g]})

    runs=[]
    cur=[]
    for item in ids:
        if not cur or item[0]-cur[-1][0] <= 10:
            cur.append(item)
        else:
            if len(cur)>=2: runs.append(cur)
            cur=[item]
    if len(cur)>=2: runs.append(cur)
    runs.sort(key=lambda x:(-len(x),x[0][0]))
    print("near-ID runs (gap<=10), top:")
    for run in runs[:15]:
        print(" ",len(run),run[0][0],"..",run[-1][0],
              ",".join(str(x[0]) for x in run[:12]) + ("..." if len(run)>12 else ""))

    # Date + archive counts are useful as a pseudo-session view.
    da = Counter((r["date"], r["label_zip"]) for r in rows)
    print("top date/archive:")
    for (date,z),n in da.most_common(15):
        print(" ",date,n,z)

print("\nCSV:", OUT/"target_metadata.csv")
