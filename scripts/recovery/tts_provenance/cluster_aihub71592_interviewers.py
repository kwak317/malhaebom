from __future__ import annotations

import argparse
import csv
import importlib.util
import io
import json
import math
import shutil
import sys
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORK = PROJECT_ROOT / ".cache" / "aihub71592" / "interviewer_clustering_pilot"
DOWNLOAD_DIR = WORK / "downloads"
EMBED_DIR = WORK / "embeddings"
AUDIO_DIR = WORK / "question_wavs"
REP_DIR = WORK / "representatives"
STATE_PATH = WORK / "state.json"
SUMMARY_CSV = WORK / "cluster_summary.csv"
MEMBERS_CSV = WORK / "cluster_members.csv"

SOURCE_ROOT = PROJECT_ROOT / ".cache" / "tts-provenance" / "listening_validation_top"
HELPER_PATH = PROJECT_ROOT / ".cache" / "recheck_aihub71592_top_archives_multi_sample.py"
DATASET_KEY = "71592"

# Same size-ordered Training source list used by the previous centroid scan.
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


def normalize(v: np.ndarray) -> np.ndarray:
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


def load_reference_centroids(helper, encoder, device):
    out = {}
    for role in ("questioner", "coach"):
        paths = sorted((SOURCE_ROOT / role).glob("rank*.wav"))
        if len(paths) != 5:
            raise RuntimeError(f"expected 5 {role} validation reference WAVs, found {len(paths)}")
        vecs = []
        for path in paths:
            wav, sr = sf.read(path, dtype="float32", always_2d=False)
            emb = helper.embed_audio(encoder, device, wav, sr)
            if emb is None:
                raise RuntimeError(f"failed to embed reference: {path}")
            vecs.append(normalize(emb))
        out[role] = normalize(np.mean(np.stack(vecs), axis=0))
    print(
        f"[reference] q-vs-coach cosine={float(np.dot(out['questioner'], out['coach'])):.6f}",
        flush=True,
    )
    return out


def load_state():
    if not STATE_PATH.exists():
        return {"processed": [], "archive_stats": {}}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE_PATH)


def locate_archive(name: str) -> Path:
    matches = list(DOWNLOAD_DIR.rglob(name))
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one downloaded {name}, found {len(matches)}")
    return matches[0]


def archive_npz_path(filekey: str) -> Path:
    return EMBED_DIR / f"{filekey}.npz"


def process_archive(helper, encoder, device, filekey: str, archive_name: str, keep_zip: bool):
    from aihub_download_common import download

    print(f"\n[download] {archive_name} filekey={filekey}", flush=True)
    download(DATASET_KEY, DOWNLOAD_DIR, filekeys=[filekey])
    zpath = locate_archive(archive_name)

    names: list[str] = []
    paths: list[str] = []
    embs: list[np.ndarray] = []
    archive_audio_dir = AUDIO_DIR / filekey
    archive_audio_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zpath) as zf:
        members = sorted(
            n for n in zf.namelist()
            if n.lower().endswith(".wav") and Path(n).name.startswith("ckmk_q_")
        )
        print(f"[archive] q_wavs={len(members)}", flush=True)

        for idx, member in enumerate(members, 1):
            base = Path(member).name
            out = archive_audio_dir / base
            try:
                raw = zf.read(member)
                if not out.exists():
                    out.write_bytes(raw)
                wav, sr = sf.read(io.BytesIO(raw), dtype="float32", always_2d=False)
                emb = helper.embed_audio(encoder, device, wav, sr)
                if emb is None:
                    continue
                names.append(base)
                paths.append(str(out.relative_to(PROJECT_ROOT)))
                embs.append(normalize(emb))
            except Exception as exc:
                print(f"[warn] {base}: {type(exc).__name__}: {exc}", flush=True)

            if idx % 100 == 0 or idx == len(members):
                print(f"[progress] {idx}/{len(members)} embedded={len(embs)}", flush=True)

    if not embs:
        raise RuntimeError(f"no embeddings produced for {archive_name}")

    EMBED_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        archive_npz_path(filekey),
        embeddings=np.stack(embs).astype(np.float32),
        wav=np.asarray(names),
        audio_path=np.asarray(paths),
        archive=np.asarray([archive_name] * len(names)),
        filekey=np.asarray([filekey] * len(names)),
    )

    if not keep_zip:
        zpath.unlink(missing_ok=True)
        print(f"[cleanup] deleted {zpath}", flush=True)

    return len(members), len(embs)


def load_all_embeddings(selected):
    matrices = []
    rows = []
    for filekey, _, archive_name in selected:
        npz_path = archive_npz_path(filekey)
        if not npz_path.exists():
            raise RuntimeError(f"missing embedding cache for {archive_name}: {npz_path}")
        data = np.load(npz_path)
        emb = np.asarray(data["embeddings"], dtype=np.float32)
        matrices.append(emb)
        for i in range(len(emb)):
            rows.append({
                "wav": str(data["wav"][i]),
                "audio_path": str(data["audio_path"][i]),
                "archive": str(data["archive"][i]),
                "filekey": str(data["filekey"][i]),
            })
    X = np.concatenate(matrices, axis=0)
    X = X / np.linalg.norm(X, axis=1, keepdims=True)
    return X.astype(np.float32), rows


def cluster_embeddings(X: np.ndarray, similarity_threshold: float):
    from sklearn.cluster import AgglomerativeClustering

    distance_threshold = 1.0 - similarity_threshold
    model = AgglomerativeClustering(
        n_clusters=None,
        metric="cosine",
        linkage="average",
        distance_threshold=distance_threshold,
        compute_full_tree=True,
    )
    return model.fit_predict(X)


def make_outputs(X, rows, labels, refs, representative_count: int):
    raw_groups: dict[int, list[int]] = {}
    for idx, label in enumerate(labels):
        raw_groups.setdefault(int(label), []).append(idx)

    details = {}
    for label, idxs in raw_groups.items():
        block = X[idxs]
        centroid = normalize(block.mean(axis=0))
        sims = block @ centroid
        order = np.argsort(-sims)
        rep_idxs = [idxs[int(j)] for j in order[:representative_count]]
        archives = Counter(rows[i]["archive"] for i in idxs)
        q_score = float(np.dot(centroid, refs["questioner"]))
        c_score = float(np.dot(centroid, refs["coach"]))
        details[label] = {
            "idxs": idxs,
            "centroid": centroid,
            "mean_to_centroid": float(np.mean(sims)),
            "min_to_centroid": float(np.min(sims)),
            "q_score": q_score,
            "c_score": c_score,
            "rep_idxs": rep_idxs,
            "archives": archives,
        }

    # Stable human-facing cluster IDs: biggest clusters first, then stronger cohesion.
    ordered = sorted(
        details,
        key=lambda lab: (
            -len(details[lab]["idxs"]),
            -details[lab]["mean_to_centroid"],
            lab,
        ),
    )
    cluster_id = {lab: f"C{rank:03d}" for rank, lab in enumerate(ordered, 1)}

    if REP_DIR.exists():
        shutil.rmtree(REP_DIR)
    REP_DIR.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    member_rows = []
    for lab in ordered:
        d = details[lab]
        cid = cluster_id[lab]
        idxs = d["idxs"]
        reps = []
        for rank, idx in enumerate(d["rep_idxs"], 1):
            src = PROJECT_ROOT / rows[idx]["audio_path"]
            dst = REP_DIR / cid / f"rep{rank:02d}_{src.name}"
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            reps.append(str(dst.relative_to(PROJECT_ROOT)))

        best_role = "questioner" if d["q_score"] >= d["c_score"] else "coach"
        best_score = max(d["q_score"], d["c_score"])
        summary_rows.append({
            "cluster": cid,
            "size": len(idxs),
            "mean_to_centroid": d["mean_to_centroid"],
            "min_to_centroid": d["min_to_centroid"],
            "questioner_score": d["q_score"],
            "coach_score": d["c_score"],
            "margin_q_minus_coach": d["q_score"] - d["c_score"],
            "closest_known_role": best_role,
            "closest_known_score": best_score,
            "archive_count": len(d["archives"]),
            "archives": " | ".join(f"{k}:{v}" for k, v in d["archives"].most_common()),
            "representatives": " | ".join(reps),
        })

        centroid = d["centroid"]
        for idx in idxs:
            member_rows.append({
                "cluster": cid,
                **rows[idx],
                "similarity_to_cluster_centroid": float(np.dot(X[idx], centroid)),
                "questioner_score": float(np.dot(X[idx], refs["questioner"])),
                "coach_score": float(np.dot(X[idx], refs["coach"])),
            })

    with SUMMARY_CSV.open("w", newline="", encoding="utf-8") as f:
        fields = [
            "cluster", "size", "mean_to_centroid", "min_to_centroid",
            "questioner_score", "coach_score", "margin_q_minus_coach",
            "closest_known_role", "closest_known_score",
            "archive_count", "archives", "representatives",
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(summary_rows)

    with MEMBERS_CSV.open("w", newline="", encoding="utf-8") as f:
        fields = [
            "cluster", "wav", "audio_path", "archive", "filekey",
            "similarity_to_cluster_centroid", "questioner_score", "coach_score",
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(member_rows)

    return summary_rows


def main():
    parser = argparse.ArgumentParser(
        description="Cluster AI Hub 71592 question WAVs into anonymous interviewer voice groups."
    )
    parser.add_argument("--max-archives", type=int, default=8)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--run", action="store_true", help="Actually download/embed/cluster. Without --run, only print the plan.")
    parser.add_argument("--keep-zips", action="store_true")
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.988,
        help="Average-link cosine similarity cut. Default 0.988; known A/B gap suggests 0.985-0.990 is worth comparing.",
    )
    parser.add_argument("--representatives", type=int, default=3)
    args = parser.parse_args()

    if not 0.90 < args.similarity_threshold < 1.0:
        raise SystemExit("--similarity-threshold must be between 0.90 and 1.0")
    if args.representatives < 1:
        raise SystemExit("--representatives must be >= 1")

    selected = ARCHIVES if args.all else ARCHIVES[: max(0, args.max_archives)]
    print(f"[plan] selected={len(selected)}/{len(ARCHIVES)} archive(s)")
    for i, (key, size, name) in enumerate(selected, 1):
        print(f"  {i:02d}. {key} {size:>7} {name}")
    print(f"[cluster] average-link cosine threshold >= {args.similarity_threshold:.3f}")
    print(f"[work] {WORK.relative_to(PROJECT_ROOT)}")
    if args.plan_only or not args.run:
        if not args.run:
            print("[safe] no --run: plan only; no download or model load performed")
        return

    WORK.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    EMBED_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str((PROJECT_ROOT / "backend" / "scripts").resolve()))
    helper = load_helper()
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"[device] {device}", flush=True)
    encoder = helper.load_encoder(device)
    refs = load_reference_centroids(helper, encoder, device)

    state = load_state()
    processed = set(state.get("processed", []))

    for filekey, size, archive_name in selected:
        cached = archive_npz_path(filekey).exists()
        if archive_name in processed and cached:
            print(f"[skip] cached: {archive_name}", flush=True)
            continue

        q_count, emb_count = process_archive(
            helper, encoder, device, filekey, archive_name, args.keep_zips
        )
        state.setdefault("processed", []).append(archive_name)
        state.setdefault("archive_stats", {})[archive_name] = {
            "filekey": filekey,
            "size": size,
            "q_wavs": q_count,
            "embeddings": emb_count,
        }
        save_state(state)

    X, rows = load_all_embeddings(selected)
    print(f"\n[cluster] total embeddings={len(X)}", flush=True)
    labels = cluster_embeddings(X, args.similarity_threshold)
    summaries = make_outputs(X, rows, labels, refs, args.representatives)

    sizes = sorted((int(r["size"]) for r in summaries), reverse=True)
    print(f"[cluster] clusters={len(summaries)}")
    print(f"[cluster] largest sizes={sizes[:15]}")
    print(f"[summary] {SUMMARY_CSV.relative_to(PROJECT_ROOT)}")
    print(f"[members] {MEMBERS_CSV.relative_to(PROJECT_ROOT)}")
    print(f"[reps]    {REP_DIR.relative_to(PROJECT_ROOT)}")

    print("\n[top known-role matches]")
    for role in ("questioner", "coach"):
        key = f"{role}_score"
        top = sorted(summaries, key=lambda r: float(r[key]), reverse=True)[:8]
        print(f"[{role}]")
        for r in top:
            print(
                f"  {r['cluster']} size={r['size']:>4} "
                f"{key}={float(r[key]):.6f} "
                f"other={float(r['coach_score' if role == 'questioner' else 'questioner_score']):.6f} "
                f"cohesion={float(r['mean_to_centroid']):.6f}"
            )


if __name__ == "__main__":
    main()
