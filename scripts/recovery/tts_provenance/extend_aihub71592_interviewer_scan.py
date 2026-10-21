from __future__ import annotations

import argparse
import csv
import importlib.util
import io
import math
import sys
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from sklearn.cluster import AgglomerativeClustering

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORK = PROJECT_ROOT / ".cache" / "aihub71592" / "interviewer_clustering_pilot"
DOWNLOAD_DIR = WORK / "downloads"
EMBED_DIR = WORK / "embeddings"
SOURCE_ROOT = PROJECT_ROOT / ".cache" / "tts-provenance" / "listening_validation_top"
HELPER_PATH = PROJECT_ROOT / ".cache" / "recheck_aihub71592_top_archives_multi_sample.py"
DATASET_KEY = "71592"

OUT_DIR = PROJECT_ROOT / ".cache" / "aihub71592" / "interviewer_clustering_extended"
SUMMARY_CSV = OUT_DIR / "cluster_summary.csv"
MEMBERS_CSV = OUT_DIR / "cluster_members.csv"

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

EXPERIENCED_KEYS = {
    "495114", "495118", "495124", "495126", "495116", "495122", "495120", "495128",
    "495102", "495106", "495108", "495112", "495104", "495110",
}


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


def load_refs(helper, encoder, device):
    refs = {}
    for role in ("questioner", "coach"):
        vecs = []
        paths = sorted((SOURCE_ROOT / role).glob("rank*.wav"))
        if len(paths) != 5:
            raise RuntimeError(f"expected 5 reference WAVs for {role}, got {len(paths)}")
        for p in paths:
            wav, sr = sf.read(p, dtype="float32", always_2d=False)
            emb = helper.embed_audio(encoder, device, wav, sr)
            if emb is None:
                raise RuntimeError(f"failed to embed {p}")
            vecs.append(normalize(emb))
        refs[role] = normalize(np.mean(np.stack(vecs), axis=0))
    return refs


def locate_archive(name):
    matches = list(DOWNLOAD_DIR.rglob(name))
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one downloaded {name}, found {len(matches)}")
    return matches[0]


def npz_path(filekey):
    return EMBED_DIR / f"{filekey}.npz"


def embed_archive(helper, encoder, device, filekey, archive_name, keep_zip=False):
    from aihub_download_common import download

    print(f"\n[download] {archive_name} ({filekey})", flush=True)
    download(DATASET_KEY, DOWNLOAD_DIR, filekeys=[filekey])
    zpath = locate_archive(archive_name)

    names, embs = [], []
    with zipfile.ZipFile(zpath) as zf:
        members = sorted(
            n for n in zf.namelist()
            if n.lower().endswith(".wav") and Path(n).name.startswith("ckmk_q_")
        )
        print(f"[archive] q_wavs={len(members)}", flush=True)
        for idx, member in enumerate(members, 1):
            try:
                raw = zf.read(member)
                wav, sr = sf.read(io.BytesIO(raw), dtype="float32", always_2d=False)
                emb = helper.embed_audio(encoder, device, wav, sr)
                if emb is not None:
                    names.append(Path(member).name)
                    embs.append(normalize(emb))
            except Exception as exc:
                print(f"[warn] {Path(member).name}: {type(exc).__name__}: {exc}", flush=True)
            if idx % 100 == 0 or idx == len(members):
                print(f"[progress] {idx}/{len(members)} embedded={len(embs)}", flush=True)

    if not embs:
        raise RuntimeError(f"no embeddings produced for {archive_name}")

    EMBED_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        npz_path(filekey),
        embeddings=np.stack(embs).astype(np.float32),
        wav=np.asarray(names),
        archive=np.asarray([archive_name] * len(names)),
        filekey=np.asarray([filekey] * len(names)),
        audio_path=np.asarray([""] * len(names)),
    )
    print(f"[cache] {npz_path(filekey).relative_to(PROJECT_ROOT)} ({len(embs)} embeddings)", flush=True)

    if not keep_zip:
        zpath.unlink(missing_ok=True)
        print(f"[cleanup] deleted {zpath}", flush=True)


def load_selected(selected):
    mats, rows = [], []
    for filekey, _, archive_name in selected:
        p = npz_path(filekey)
        if not p.exists():
            raise RuntimeError(f"missing embedding cache: {archive_name} ({filekey})")
        d = np.load(p)
        X = np.asarray(d["embeddings"], dtype=np.float32)
        X /= np.linalg.norm(X, axis=1, keepdims=True)
        mats.append(X)
        for i in range(len(X)):
            rows.append({
                "wav": str(d["wav"][i]),
                "archive": str(d["archive"][i]),
                "filekey": str(d["filekey"][i]),
            })
    return np.concatenate(mats, axis=0), rows


def cluster_and_write(X, rows, refs, threshold):
    labels = AgglomerativeClustering(
        n_clusters=None,
        metric="cosine",
        linkage="average",
        distance_threshold=1.0-threshold,
        compute_full_tree=True,
    ).fit_predict(X)

    groups = {}
    for i, lab in enumerate(labels):
        groups.setdefault(int(lab), []).append(i)

    details = []
    for lab, idxs in groups.items():
        block = X[idxs]
        centroid = normalize(block.mean(axis=0))
        sims = block @ centroid
        details.append({
            "lab": lab,
            "idxs": idxs,
            "centroid": centroid,
            "size": len(idxs),
            "mean": float(sims.mean()),
            "min": float(sims.min()),
            "q": float(centroid @ refs["questioner"]),
            "c": float(centroid @ refs["coach"]),
            "archives": Counter(rows[i]["archive"] for i in idxs),
        })

    ordered = sorted(details, key=lambda r: (-r["size"], -r["mean"], r["lab"]))
    cid = {r["lab"]: f"C{n:03d}" for n, r in enumerate(ordered, 1)}

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with SUMMARY_CSV.open("w", newline="", encoding="utf-8") as f:
        fields = [
            "cluster", "size", "mean_to_centroid", "min_to_centroid",
            "questioner_score", "coach_score", "margin_q_minus_coach",
            "closest_known_role", "closest_known_score",
            "archive_count", "archives",
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in ordered:
            q, c = r["q"], r["c"]
            w.writerow({
                "cluster": cid[r["lab"]],
                "size": r["size"],
                "mean_to_centroid": r["mean"],
                "min_to_centroid": r["min"],
                "questioner_score": q,
                "coach_score": c,
                "margin_q_minus_coach": q-c,
                "closest_known_role": "questioner" if q >= c else "coach",
                "closest_known_score": max(q, c),
                "archive_count": len(r["archives"]),
                "archives": " | ".join(f"{k}:{v}" for k, v in r["archives"].most_common()),
            })

    with MEMBERS_CSV.open("w", newline="", encoding="utf-8") as f:
        fields = [
            "cluster", "wav", "archive", "filekey",
            "similarity_to_cluster_centroid", "questioner_score", "coach_score",
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in ordered:
            cluster = cid[r["lab"]]
            for i in r["idxs"]:
                w.writerow({
                    "cluster": cluster,
                    **rows[i],
                    "similarity_to_cluster_centroid": float(X[i] @ r["centroid"]),
                    "questioner_score": float(X[i] @ refs["questioner"]),
                    "coach_score": float(X[i] @ refs["coach"]),
                })

    print(f"\n[result] embeddings={len(X)} clusters={len(ordered)} threshold={threshold:.3f}")
    for role, key in (("questioner", "q"), ("coach", "c")):
        best = max(ordered, key=lambda r: r[key])
        other = best["c"] if key == "q" else best["q"]
        print(
            f"[{role}] {cid[best['lab']]} size={best['size']} "
            f"score={best[key]:.6f} other={other:.6f} "
            f"cohesion={best['mean']:.6f} min={best['min']:.6f} "
            f"archives={len(best['archives'])}"
        )
        ranked = sorted(
            best["idxs"],
            key=lambda i: float(X[i] @ refs[role]),
            reverse=True,
        )[:12]
        print("  top:", ", ".join(rows[i]["wav"] for i in ranked))

    print(f"[summary] {SUMMARY_CSV.relative_to(PROJECT_ROOT)}")
    print(f"[members] {MEMBERS_CSV.relative_to(PROJECT_ROOT)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["experienced", "full"], default="experienced")
    ap.add_argument("--threshold", type=float, default=0.982)
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--keep-zips", action="store_true")
    args = ap.parse_args()

    selected = (
        [x for x in ARCHIVES if x[0] in EXPERIENCED_KEYS]
        if args.stage == "experienced"
        else ARCHIVES
    )
    missing = [x for x in selected if not npz_path(x[0]).exists()]

    print(f"[plan] stage={args.stage} selected={len(selected)} cached={len(selected)-len(missing)} missing={len(missing)}")
    for key, size, name in missing:
        print(f"  NEED {key} {size:>7} {name}")
    print(f"[cluster] threshold={args.threshold:.3f}")
    print("[storage] new archives keep embeddings only; ZIPs deleted after successful embedding")

    if not args.run:
        print("[safe] no --run: nothing downloaded")
        return

    if not 0.90 < args.threshold < 1.0:
        raise SystemExit("--threshold must be between 0.90 and 1.0")

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    EMBED_DIR.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str((PROJECT_ROOT / "backend" / "scripts").resolve()))

    helper = load_helper()
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"[device] {device}", flush=True)
    encoder = helper.load_encoder(device)
    refs = load_refs(helper, encoder, device)
    print(f"[reference] q-vs-coach={float(refs['questioner'] @ refs['coach']):.6f}", flush=True)

    for filekey, _, archive_name in missing:
        embed_archive(helper, encoder, device, filekey, archive_name, args.keep_zips)

    X, rows = load_selected(selected)
    cluster_and_write(X, rows, refs, args.threshold)


if __name__ == "__main__":
    main()
