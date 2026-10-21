from __future__ import annotations

import argparse
import csv
import heapq
import importlib.util
import io
import json
import math
import sys
import zipfile
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORK = PROJECT_ROOT / ".cache" / "aihub71592" / "speaker_scan_training_centroid"
DOWNLOAD_DIR = WORK / "downloads"
STATE_PATH = WORK / "state.json"
TOP_CSV = WORK / "top_matches.csv"
HITS_CSV = WORK / "likely_same_speaker.csv"

SOURCE_ROOT = PROJECT_ROOT / ".cache" / "tts-provenance" / "listening_validation_top"
HELPER_PATH = PROJECT_ROOT / ".cache" / "recheck_aihub71592_top_archives_multi_sample.py"
DATASET_KEY = "71592"
TOP_K = 200
LIKELY_THRESHOLD = 0.990

# Exact live-tree filekeys, verified 2026-09-19.
# Ordered from smallest to largest so --max-archives N is a useful pilot.
ARCHIVES = [
    ("495114", "161 MB", "TS_04.RND_Female_Experienced.zip"),
    ("495118", "351 MB", "TS_05.ICT_Female_Experienced.zip"),
    ("495124", "356 MB", "TS_06.Design_Male_Experienced.zip"),
    ("495126", "473 MB", "TS_07.ProductionManufacturing_Female_Experienced.zip"),
    ("495116", "642 MB", "TS_04.RND_Male_Experienced.zip"),
    ("495122", "792 MB", "TS_06.Design_Female_Experienced.zip"),
    ("495120", "1002 MB", "TS_05.ICT_Male_Experienced.zip"),
    ("495128", "1 GB", "TS_07.ProductionManufacturing_Male_Experienced.zip"),
    ("495102", "2 GB", "TS_01.Management_Female_Experienced.zip"),
    ("495106", "2 GB", "TS_02.SalesMarketing_Female_Experienced.zip"),
    ("495108", "2 GB", "TS_02.SalesMarketing_Male_Experienced.zip"),
    ("495112", "2 GB", "TS_03.PublicService_Male_Experienced.zip"),
    ("495104", "3 GB", "TS_01.Management_Male_Experienced.zip"),
    ("495125", "3 GB", "TS_06.Design_Male_New.zip"),
    ("495110", "4 GB", "TS_03.PublicService_Female_Experienced.zip"),
    ("495115", "4 GB", "TS_04.RND_Female_New.zip"),
    ("495119", "4 GB", "TS_05.ICT_Female_New.zip"),
    ("495117", "6 GB", "TS_04.RND_Male_New.zip"),
    ("495129", "6 GB", "TS_07.ProductionManufacturing_Male_New.zip"),
    ("495109", "7 GB", "TS_02.SalesMarketing_Male_New.zip"),
    ("495121", "8 GB", "TS_05.ICT_Male_New.zip"),
    ("495127", "8 GB", "TS_07.ProductionManufacturing_Female_New.zip"),
    ("495105", "9 GB", "TS_01.Management_Male_New.zip"),
    ("495113", "9 GB", "TS_03.PublicService_Male_New.zip"),
    ("495123", "9 GB", "TS_06.Design_Female_New.zip"),
    ("495107", "14 GB", "TS_02.SalesMarketing_Female_New.zip"),
    ("495103", "17 GB", "TS_01.Management_Female_New.zip"),
    ("495111", "23 GB", "TS_03.PublicService_Female_New.zip"),
]


def load_helper():
    spec = importlib.util.spec_from_file_location("tts_scan_helper", HELPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load helper: {HELPER_PATH}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def normalize(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=np.float32)
    n = float(np.linalg.norm(v))
    if not math.isfinite(n) or n <= 0:
        raise RuntimeError("invalid vector norm")
    return v / n


def load_centroids(helper, encoder, device):
    out = {}
    for role in ("questioner", "coach"):
        vecs = []
        files = sorted((SOURCE_ROOT / role).glob("rank*.wav"))
        if len(files) != 5:
            raise RuntimeError(f"expected 5 {role} source WAVs, found {len(files)}")
        for p in files:
            wav, sr = sf.read(p, dtype="float32", always_2d=False)
            emb = helper.embed_audio(encoder, device, wav, sr)
            if emb is None:
                raise RuntimeError(f"failed to embed centroid source: {p}")
            vecs.append(emb)
        centroid = normalize(np.mean(np.stack(vecs), axis=0))
        out[role] = centroid
        print(f"[centroid] {role}: {len(vecs)} source WAVs", flush=True)
    print(f"[centroid] q-vs-coach cosine={float(np.dot(out['questioner'], out['coach'])):.6f}", flush=True)
    return out


def load_state():
    if not STATE_PATH.exists():
        return {"processed": [], "top": {"questioner": [], "coach": []}, "hits": []}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE_PATH)


def push_top(heap, role, row):
    item = (float(row[f"{role}_score"]), row["wav"], row)
    heapq.heappush(heap, item)
    if len(heap) > TOP_K:
        heapq.heappop(heap)


def rows_from_heap(heap):
    return [item[2] for item in sorted(heap, key=lambda x: (x[0], x[1]), reverse=True)]


def write_outputs(state):
    rows = []
    for role in ("questioner", "coach"):
        for rank, row in enumerate(state["top"][role], 1):
            rows.append({
                "target": role,
                "rank": rank,
                **row,
            })
    fields = [
        "target", "rank", "wav", "archive", "filekey",
        "questioner_score", "coach_score", "margin_q_minus_coach",
    ]
    with TOP_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    hit_fields = [
        "wav", "archive", "filekey",
        "questioner_score", "coach_score", "margin_q_minus_coach",
        "likely_target",
    ]
    with HITS_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=hit_fields)
        w.writeheader()
        w.writerows(state["hits"])


def locate_archive(name):
    matches = list(DOWNLOAD_DIR.rglob(name))
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one downloaded {name}, found {len(matches)}")
    return matches[0]


def scan_archive(helper, encoder, device, centroids, filekey, archive_name):
    from aihub_download_common import download

    print(f"\n[download] {archive_name} filekey={filekey}", flush=True)
    download(DATASET_KEY, DOWNLOAD_DIR, filekeys=[filekey])
    zpath = locate_archive(archive_name)

    top_heaps = {"questioner": [], "coach": []}
    hits = []
    scanned = 0

    with zipfile.ZipFile(zpath) as zf:
        members = [
            n for n in zf.namelist()
            if n.lower().endswith(".wav") and Path(n).name.startswith("ckmk_q_")
        ]
        print(f"[archive] q_wavs={len(members)}", flush=True)

        for idx, member in enumerate(members, 1):
            try:
                wav, sr = sf.read(io.BytesIO(zf.read(member)), dtype="float32", always_2d=False)
                emb = helper.embed_audio(encoder, device, wav, sr)
                if emb is None:
                    continue
                q = float(np.dot(centroids["questioner"], emb))
                c = float(np.dot(centroids["coach"], emb))
                row = {
                    "wav": Path(member).name,
                    "archive": archive_name,
                    "filekey": filekey,
                    "questioner_score": q,
                    "coach_score": c,
                    "margin_q_minus_coach": q - c,
                }
                push_top(top_heaps["questioner"], "questioner", row)
                push_top(top_heaps["coach"], "coach", row)

                best = max(q, c)
                if best >= LIKELY_THRESHOLD:
                    hits.append({
                        **row,
                        "likely_target": "questioner" if q >= c else "coach",
                    })

                scanned += 1
                if idx % 100 == 0 or idx == len(members):
                    print(
                        f"[progress] {idx}/{len(members)} "
                        f"bestQ={max((x[0] for x in top_heaps['questioner']), default=0):.6f} "
                        f"bestC={max((x[0] for x in top_heaps['coach']), default=0):.6f} "
                        f"hits>={LIKELY_THRESHOLD:.3f}:{len(hits)}",
                        flush=True,
                    )
            except Exception as exc:
                print(f"[warn] {Path(member).name}: {type(exc).__name__}: {exc}", flush=True)

    return scanned, top_heaps, hits, zpath


def merge_top(existing_rows, new_heap, role):
    heap = []
    for row in existing_rows:
        push_top(heap, role, row)
    for row in rows_from_heap(new_heap):
        push_top(heap, role, row)
    return rows_from_heap(heap)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-archives", type=int, default=8, help="Process first N size-ordered archives; default 8")
    parser.add_argument("--all", action="store_true", help="Process all 28 training source archives")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--keep-zips", action="store_true")
    args = parser.parse_args()

    selected = ARCHIVES if args.all else ARCHIVES[: max(0, args.max_archives)]
    print(f"[plan] selected={len(selected)}/{len(ARCHIVES)} archive(s)")
    for i, (key, size, name) in enumerate(selected, 1):
        print(f"  {i:02d}. {key} {size:>6} {name}")
    if args.plan_only:
        return

    WORK.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str((PROJECT_ROOT / "backend" / "scripts").resolve()))
    helper = load_helper()
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"[device] {device}", flush=True)
    encoder = helper.load_encoder(device)
    centroids = load_centroids(helper, encoder, device)

    state = load_state()
    processed = set(state.get("processed", []))

    for filekey, size, archive_name in selected:
        if archive_name in processed:
            print(f"[skip] already processed: {archive_name}", flush=True)
            continue

        scanned, heaps, hits, zpath = scan_archive(
            helper, encoder, device, centroids, filekey, archive_name
        )

        for role in ("questioner", "coach"):
            state["top"][role] = merge_top(state["top"].get(role, []), heaps[role], role)

        seen_hit_keys = {(r["archive"], r["wav"]) for r in state.get("hits", [])}
        for row in hits:
            key = (row["archive"], row["wav"])
            if key not in seen_hit_keys:
                state.setdefault("hits", []).append(row)
                seen_hit_keys.add(key)

        state.setdefault("processed", []).append(archive_name)
        state.setdefault("archive_stats", {})[archive_name] = {
            "filekey": filekey,
            "size": size,
            "q_wavs_scanned": scanned,
            "likely_hits": len(hits),
        }
        save_state(state)
        write_outputs(state)

        print(f"[done] {archive_name}: scanned={scanned} likely_hits={len(hits)}", flush=True)
        for role in ("questioner", "coach"):
            top3 = state["top"][role][:3]
            print(f"[top {role}]")
            for r in top3:
                print(
                    f"  {r['wav']} score={r[f'{role}_score']:.6f} "
                    f"other={r['coach_score' if role == 'questioner' else 'questioner_score']:.6f} "
                    f"archive={r['archive']}",
                    flush=True,
                )

        if not args.keep_zips:
            zpath.unlink(missing_ok=True)
            print(f"[cleanup] deleted {zpath}", flush=True)

    write_outputs(state)
    print(f"\n[state] {STATE_PATH.relative_to(PROJECT_ROOT)}")
    print(f"[top]   {TOP_CSV.relative_to(PROJECT_ROOT)}")
    print(f"[hits]  {HITS_CSV.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
