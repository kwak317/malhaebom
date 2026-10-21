from __future__ import annotations
import csv
from collections import Counter
from pathlib import Path

ROOT = Path(".cache/aihub71592")
META = ROOT / "target_metadata_analysis" / "target_metadata.csv"
OUT = ROOT / "recovered_tts_sources"
OUT.mkdir(parents=True, exist_ok=True)

rows = list(csv.DictReader(META.open(encoding="utf-8-sig")))

stats = {}
for role in ("questioner", "coach"):
    xs = [r for r in rows if r["role"] == role]
    durs = [int(r["duration_ms"]) for r in xs if r["duration_ms"]]
    total_sec = sum(durs) / 1000
    stats[role] = (len(xs), total_sec)
    exp = Counter(r["experience"] for r in xs)
    occ = Counter(r["occupation"] for r in xs)
    print(role, "count", len(xs), "seconds", round(total_sec, 2), "minutes", round(total_sec/60, 2))
    print(" experience", dict(exp))
    print(" occupation", dict(occ))
    out = OUT / f"{role}_recovered_manifest.csv"
    fields = ["wav","id","date","occupation","gender","ageRange","experience","wordCount","duration_ms","question","label_zip","audioPath"]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in sorted(xs, key=lambda x:int(x["id"])):
            w.writerow({k:r.get(k,"") for k in fields})

q_n, q_sec = stats["questioner"]
c_n, c_sec = stats["coach"]
lines = [
    "# Recovered TTS source provenance",
    "",
    "This folder freezes the current recovery result for the old proj1-b Qwen3-TTS pilot.",
    "",
    "## Recovered source speakers",
    "",
    f"- candidate_04_questioner -> anonymous AI Hub 71592 interviewer cluster A",
    f"  - recovered manifest rows: {q_n}",
    f"  - recovered audio duration represented by labels: {q_sec/60:.2f} minutes",
    f"- candidate_01_coach -> distinct anonymous AI Hub 71592 interviewer cluster B",
    f"  - recovered manifest rows: {c_n}",
    f"  - recovered audio duration represented by labels: {c_sec/60:.2f} minutes",
    "",
    "These rows combine the recovered Experienced clusters and high-confidence matches from the three scanned New archives. They are a provenance recovery set, not proof that every row was in the original fine-tuning subset.",
    "",
    "## Strong evidence",
    "",
    "- Both surviving checkpoints are Qwen3-TTS 12Hz 0.6B Base-derived custom-voice models.",
    "- Historical project documentation records both as 1-epoch pilot fine-tunes.",
    "- Speaker-embedding clustering consistently maps the questioner and coach checkpoints to two distinct interviewer clusters.",
    "- The same anonymous interviewer voices recur across occupation/applicant metadata groups.",
    "- All currently matched label records have date=20230116.",
    "- Base-vs-fine-tuned teacher-forced loss pilot did not separate Training candidates from same-speaker Validation controls, so exact training membership cannot be recovered reliably from loss.",
    "",
    "## Working estimate of the original corpus",
    "",
    "Most plausible reconstruction:",
    "",
    "1. A speaker-selection step identified candidate interviewer voices from AI Hub 71592 question audio.",
    "2. For each selected candidate, multiple utterances from that interviewer were assembled into a single-speaker corpus.",
    "3. The 0.6B Base model was fine-tuned for one epoch and candidate outputs were judged by listening.",
    "4. candidate_04_questioner was selected for the questioner voice; candidate_01_coach was retained temporarily for coach.",
    "5. The exact utterance subset is no longer recoverable from surviving Git/model metadata. A duration/ID/archive-only rule is not supported by the recovered data.",
    "",
    "Do not treat questioner_recovered_manifest.csv or coach_recovered_manifest.csv as the exact original training manifest. They are the best recovered same-speaker source sets currently available.",
]
(OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("wrote", OUT / "README.md")