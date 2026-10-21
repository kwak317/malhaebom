from __future__ import annotations

import argparse
import csv
import importlib.util
import io
import math
import shutil
import sys
import zipfile
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PILOT = PROJECT_ROOT / ".cache" / "aihub71592" / "interviewer_clustering_pilot"
EMBED_DIR = PILOT / "embeddings"
DOWNLOAD_DIR = PILOT / "downloads"
EXTENDED = PROJECT_ROOT / ".cache" / "aihub71592" / "interviewer_clustering_extended"
SOURCE_ROOT = PROJECT_ROOT / ".cache" / "tts-provenance" / "listening_validation_top"
HELPER_PATH = PROJECT_ROOT / ".cache" / "recheck_aihub71592_top_archives_multi_sample.py"
DATASET_KEY = "71592"

WORK = PROJECT_ROOT / ".cache" / "aihub71592" / "seeded_new_matches"
MATCH_CSV = WORK / "matches.csv"
AUDIO_DIR = WORK / "high_confidence_audio"

QUESTIONER_CLUSTER = "C008"
COACH_CLUSTER = "C027"
HIGH_THRESHOLD = 0.991
RELAXED_THRESHOLD = 0.989

SMALL_NEW = [
    ("495125", "3 GB", "TS_06.Design_Male_New.zip"),
    ("495115", "4 GB", "TS_04.RND_Female_New.zip"),
    ("495119", "4 GB", "TS_05.ICT_Female_New.zip"),
]


def normalize(v):
    v = np.asarray(v, dtype=np.float32)
    n = float(np.linalg.norm(v))
    if not math.isfinite(n) or n <= 0:
        raise RuntimeError("invalid vector norm")
    return v / n


def load_helper():
    spec = importlib.util.spec_from_file_location("tts_scan_helper", HELPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load helper: {HELPER_PATH}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_all_cached():
    Xs, rows = [], []
    for p in sorted(EMBED_DIR.glob("*.npz")):
        d = np.load(p)
        X = np.asarray(d["embeddings"], dtype=np.float32)
        X /= np.linalg.norm(X, axis=1, keepdims=True)
        Xs.append(X)
        for i in range(len(X)):
            rows.append({
                "wav": str(d["wav"][i]),
                "archive": str(d["archive"][i]),
                "filekey": str(d["filekey"][i]),
            })
    if not Xs:
        raise RuntimeError("no cached embeddings")
    return np.concatenate(Xs, axis=0), rows


def build_seed_centroids():
    members = list(csv.DictReader((EXTENDED / "cluster_members.csv").open(encoding="utf-8-sig")))
    cluster_by_key = {(r["filekey"], r["wav"]): r["cluster"] for r in members}
    X, rows = load_all_cached()

    seeds = {}
    for role, cid in (("questioner", QUESTIONER_CLUSTER), ("coach", COACH_CLUSTER)):
        idxs = [
            i for i, r in enumerate(rows)
            if cluster_by_key.get((r["filekey"], r["wav"])) == cid
        ]
        if not idxs:
            raise RuntimeError(f"no members found for {role} {cid}")
        seeds[role] = normalize(X[idxs].mean(axis=0))
        print(f"[seed] {role} {cid}: {len(idxs)} members", flush=True)

    print(f"[seed] q-vs-coach={float(seeds['questioner'] @ seeds['coach']):.6f}", flush=True)
    return seeds


def locate_archive(name):
    matches = list(DOWNLOAD_DIR.rglob(name))
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one downloaded {name}, found {len(matches)}")
    return matches[0]


def npz_path(filekey):
    return EMBED_DIR / f"{filekey}.npz"


def process_archive(helper, encoder, device, seeds, filekey, archive_name, keep_zip=False):
    from aihub_download_common import download

    print(f"\n[download] {archive_name} ({filekey})", flush=True)
    download(DATASET_KEY, DOWNLOAD_DIR, filekeys=[filekey])
    zpath = locate_archive(archive_name)

    names, embs = [], []
    raw_for_match = {}
    with zipfile.ZipFile(zpath) as zf:
        members = sorted(
            n for n in zf.namelist()
            if n.lower().endswith(".wav") and Path(n).name.startswith("ckmk_q_")
        )
        print(f"[archive] q_wavs={len(members)}", flush=True)

        for idx, member in enumerate(members, 1):
            base = Path(member).name
            try:
                raw = zf.read(member)
                wav, sr = sf.read(io.BytesIO(raw), dtype="float32", always_2d=False)
                emb = helper.embed_audio(encoder, device, wav, sr)
                if emb is None:
                    continue
                emb = normalize(emb)
                names.append(base)
                embs.append(emb)

                q = float(emb @ seeds["questioner"])
                c = float(emb @ seeds["coach"])
                if max(q, c) >= HIGH_THRESHOLD:
                    raw_for_match[base] = raw
            except Exception as exc:
                print(f"[warn] {base}: {type(exc).__name__}: {exc}", flush=True)

            if idx % 100 == 0 or idx == len(members):
                print(f"[progress] {idx}/{len(members)} embedded={len(embs)}", flush=True)

    if not embs:
        raise RuntimeError(f"no embeddings for {archive_name}")

    EMBED_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        npz_path(filekey),
        embeddings=np.stack(embs).astype(np.float32),
        wav=np.asarray(names),
        archive=np.asarray([archive_name] * len(names)),
        filekey=np.asarray([filekey] * len(names)),
        audio_path=np.asarray([""] * len(names)),
    )

    rows = []
    for base, emb in zip(names, embs):
        q = float(emb @ seeds["questioner"])
        c = float(emb @ seeds["coach"])
        best_role = "questioner" if q >= c else "coach"
        best = max(q, c)
        margin = abs(q - c)
        if best >= RELAXED_THRESHOLD:
            confidence = "high" if best >= HIGH_THRESHOLD else "relaxed"
            rows.append({
                "wav": base,
                "archive": archive_name,
                "filekey": filekey,
                "questioner_seed_score": q,
                "coach_seed_score": c,
                "margin": margin,
                "best_role": best_role,
                "best_score": best,
                "confidence": confidence,
            })

    for row in rows:
        if row["confidence"] != "high":
            continue
        raw = raw_for_match.get(row["wav"])
        if raw is None:
            continue
        out = AUDIO_DIR / row["best_role"] / f"{filekey}_{row['wav']}"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(raw)

    if not keep_zip:
        zpath.unlink(missing_ok=True)
        print(f"[cleanup] deleted {zpath}", flush=True)

    print(
        f"[match] high={sum(r['confidence']=='high' for r in rows)} "
        f"relaxed_only={sum(r['confidence']=='relaxed' for r in rows)}",
        flush=True,
    )
    return rows


def write_matches(all_rows):
    WORK.mkdir(parents=True, exist_ok=True)
    fields = [
        "wav", "archive", "filekey",
        "questioner_seed_score", "coach_seed_score", "margin",
        "best_role", "best_score", "confidence",
    ]
    with MATCH_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(sorted(all_rows, key=lambda r: float(r["best_score"]), reverse=True))


def score_cached(seeds, filekey, archive_name):
    d = np.load(npz_path(filekey))
    X = np.asarray(d["embeddings"], dtype=np.float32)
    X /= np.linalg.norm(X, axis=1, keepdims=True)
    rows = []
    for i, emb in enumerate(X):
        q = float(emb @ seeds["questioner"])
        c = float(emb @ seeds["coach"])
        best = max(q, c)
        if best >= RELAXED_THRESHOLD:
            rows.append({
                "wav": str(d["wav"][i]),
                "archive": archive_name,
                "filekey": filekey,
                "questioner_seed_score": q,
                "coach_seed_score": c,
                "margin": abs(q-c),
                "best_role": "questioner" if q >= c else "coach",
                "best_score": best,
                "confidence": "high" if best >= HIGH_THRESHOLD else "relaxed",
            })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--keep-zips", action="store_true")
    args = ap.parse_args()

    missing = [x for x in SMALL_NEW if not npz_path(x[0]).exists()]
    print(f"[plan] small-new selected={len(SMALL_NEW)} cached={len(SMALL_NEW)-len(missing)} missing={len(missing)}")
    for key, size, name in missing:
        print(f"  NEED {key} {size:>4} {name}")
    print(f"[threshold] high={HIGH_THRESHOLD:.3f} relaxed={RELAXED_THRESHOLD:.3f}")
    print("[storage] embeddings cached; only high-confidence WAVs retained; ZIPs deleted after success")

    if not args.run:
        print("[safe] no --run: nothing downloaded")
        return

    sys.path.insert(0, str((PROJECT_ROOT / "backend" / "scripts").resolve()))
    helper = load_helper()
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"[device] {device}", flush=True)
    encoder = helper.load_encoder(device)
    seeds = build_seed_centroids()

    all_rows = []
    for filekey, _, archive_name in SMALL_NEW:
        if npz_path(filekey).exists():
            print(f"[cached] {archive_name}", flush=True)
            all_rows.extend(score_cached(seeds, filekey, archive_name))
        else:
            all_rows.extend(
                process_archive(
                    helper, encoder, device, seeds, filekey, archive_name, args.keep_zips
                )
            )

    write_matches(all_rows)
    print(f"\n[result] matches={len(all_rows)}")
    for role in ("questioner", "coach"):
        rs = [r for r in all_rows if r["best_role"] == role]
        high = [r for r in rs if r["confidence"] == "high"]
        print(f"[{role}] high={len(high)} relaxed_total={len(rs)}")
        for r in sorted(rs, key=lambda x: float(x["best_score"]), reverse=True)[:10]:
            print(
                f"  {r['wav']} score={float(r['best_score']):.6f} "
                f"margin={float(r['margin']):.6f} {r['confidence']} "
                f"archive={r['archive']}"
            )
    print(f"[csv] {MATCH_CSV.relative_to(PROJECT_ROOT)}")
    print(f"[audio] {AUDIO_DIR.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
