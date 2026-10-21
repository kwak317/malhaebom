from __future__ import annotations

import csv
import io
import json
import math
import struct
import sys
import zipfile
from pathlib import Path

import numpy as np
import requests
import soundfile as sf
import torch
import torchaudio.functional as AF
from safetensors.torch import load_file, save_file

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "scripts"))
from aihub_download_common import download  # noqa: E402

from qwen_tts.core.models.configuration_qwen3_tts import Qwen3TTSSpeakerEncoderConfig  # noqa: E402
from qwen_tts.core.models.modeling_qwen3_tts import Qwen3TTSSpeakerEncoder, mel_spectrogram  # noqa: E402

DATASET_KEY = "71592"
WORK = PROJECT_ROOT / ".cache" / "aihub71592" / "speaker_recheck_top_archives"
DOWNLOAD_DIR = WORK / "downloads"
RESULT_CSV = WORK / "multi_sample_rank.csv"
SUMMARY_JSON = WORK / "summary.json"
LABEL_ROOT = PROJECT_ROOT / ".cache" / "aihub71592" / "labels_vl"
SAMPLE_ROOT = PROJECT_ROOT / ".cache" / "tts-provenance" / "multi_samples"
ENCODER_PATH = PROJECT_ROOT / ".cache" / "tts-provenance" / "qwen_base_speaker_encoder.safetensors"
HF_URL = "https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-Base/resolve/main/model.safetensors"

ARCHIVES = [
    ("495182", "VS_07.ProductionManufacturing_Female_Experienced.zip"),
    ("495178", "VS_06.Design_Female_Experienced.zip"),
    ("495158", "VS_01.Management_Female_Experienced.zip"),
    ("495166", "VS_03.PublicService_Female_Experienced.zip"),
    ("495160", "VS_01.Management_Male_Experienced.zip"),
    ("495184", "VS_07.ProductionManufacturing_Male_Experienced.zip"),
    ("495162", "VS_02.SalesMarketing_Female_Experienced.zip"),
]

def normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    if not math.isfinite(n) or n <= 0:
        raise RuntimeError("invalid embedding norm")
    return v.astype(np.float32) / n

def get_range(start: int, end: int) -> bytes:
    r = requests.get(HF_URL, headers={"Range": f"bytes={start}-{end}"}, allow_redirects=True, timeout=60)
    r.raise_for_status()
    if r.status_code == 206:
        return r.content
    if r.status_code == 200:
        return r.content[start:end + 1]
    raise RuntimeError(f"unexpected HTTP status {r.status_code}")

def ensure_encoder_weights() -> None:
    if ENCODER_PATH.is_file():
        return
    ENCODER_PATH.parent.mkdir(parents=True, exist_ok=True)
    h8 = get_range(0, 7)
    hlen = struct.unpack("<Q", h8)[0]
    header = json.loads(get_range(8, 8 + hlen - 1).decode("utf-8"))
    items = {k: v for k, v in header.items() if k != "__metadata__" and k.startswith("speaker_encoder.")}
    start_off = min(v["data_offsets"][0] for v in items.values())
    end_off = max(v["data_offsets"][1] for v in items.values())
    blob = get_range(8 + hlen + start_off, 8 + hlen + end_off - 1)
    state = {}
    for full_name, meta in items.items():
        a, b = meta["data_offsets"]
        raw = memoryview(blob)[a - start_off:b - start_off]
        if meta["dtype"] != "BF16":
            raise RuntimeError(f"unexpected dtype {meta['dtype']}: {full_name}")
        u = np.frombuffer(raw, dtype="<u2").astype(np.uint32)
        arr = (u << 16).view("<f4").copy().reshape(meta["shape"])
        state[full_name.removeprefix("speaker_encoder.")] = torch.from_numpy(arr).to(torch.bfloat16)
    save_file(state, str(ENCODER_PATH))

def load_encoder(device: torch.device) -> Qwen3TTSSpeakerEncoder:
    ensure_encoder_weights()
    cfg = Qwen3TTSSpeakerEncoderConfig(enc_dim=1024, sample_rate=24000)
    model = Qwen3TTSSpeakerEncoder(cfg)
    state = load_file(str(ENCODER_PATH))
    missing, unexpected = model.load_state_dict(state, strict=False)
    if missing or unexpected:
        raise RuntimeError(f"encoder state mismatch missing={missing} unexpected={unexpected}")
    return model.to(device=device, dtype=torch.float32).eval()

def trim_and_cap(wav: np.ndarray, sr: int, max_seconds: float = 8.0) -> np.ndarray:
    wav = np.asarray(wav, dtype=np.float32)
    if wav.ndim == 2:
        wav = wav.mean(axis=1)
    if not wav.size:
        return wav
    frame = max(1, int(sr * 0.05))
    rms = []
    for i in range(0, len(wav), frame):
        seg = wav[i:i + frame]
        rms.append(float(np.sqrt(np.mean(seg * seg))) if len(seg) else 0.0)
    rms = np.asarray(rms)
    threshold = max(0.0015, float(rms.max()) * 0.03)
    active = np.flatnonzero(rms > threshold)
    if active.size:
        start = max(0, int(active[0] * frame - 0.1 * sr))
        end = min(len(wav), int((active[-1] + 1) * frame + 0.1 * sr))
        wav = wav[start:end]
    cap = int(max_seconds * sr)
    if len(wav) > cap:
        wav = wav[:cap]
    return wav

@torch.inference_mode()
def embed_audio(encoder: Qwen3TTSSpeakerEncoder, device: torch.device, wav: np.ndarray, sr: int) -> np.ndarray | None:
    wav = trim_and_cap(wav, sr)
    if len(wav) < int(sr * 0.8):
        return None
    x = torch.from_numpy(wav).float()
    if sr != 24000:
        x = AF.resample(x, sr, 24000)
    x = x.unsqueeze(0)
    mel = mel_spectrogram(
        x, n_fft=1024, num_mels=128, sampling_rate=24000,
        hop_size=256, win_size=1024, fmin=0, fmax=12000,
    ).transpose(1, 2).to(device)
    emb = encoder(mel)[0].float().cpu().numpy()
    return normalize(emb)

def build_label_index() -> dict[str, dict]:
    index = {}
    for zpath in sorted(LABEL_ROOT.rglob("VL_*.zip")):
        with zipfile.ZipFile(zpath) as zf:
            for name in zf.namelist():
                if not name.lower().endswith(".json"):
                    continue
                try:
                    obj = json.loads(zf.read(name).decode("utf-8"))
                    ds = obj.get("dataSet", {})
                    info = ds.get("info", {})
                    raw_info = obj.get("rawDataInfo", {})
                    for role in ("question", "answer"):
                        ad = raw_info.get(role, {})
                        ap = ad.get("audioPath")
                        if not ap:
                            continue
                        key = Path(ap).name
                        raw_text = ds.get(role, {}).get("raw", {}).get("text", "")
                        index[key] = {
                            "role": role,
                            "text": raw_text,
                            "occupation": info.get("occupation"),
                            "gender": info.get("gender"),
                            "ageRange": info.get("ageRange"),
                            "experience": info.get("experience"),
                            "audioPath": ap,
                            "labelZip": zpath.name,
                        }
                except Exception:
                    continue
    return index

def load_candidate_embeddings(encoder, device) -> dict[str, list[np.ndarray]]:
    out = {}
    for candidate in ("questioner", "coach"):
        vecs = []
        for p in sorted(SAMPLE_ROOT.glob(f"{candidate}_[0-9][0-9].wav")):
            wav, sr = sf.read(p, dtype="float32", always_2d=False)
            emb = embed_audio(encoder, device, wav, sr)
            if emb is None:
                raise RuntimeError(f"failed to embed candidate sample: {p}")
            vecs.append(emb)
            print(f"[candidate] {candidate}: {p.name}", flush=True)
        if len(vecs) != 5:
            raise RuntimeError(f"expected 5 samples for {candidate}, found {len(vecs)}")
        out[candidate] = vecs
    return out

def summarize_scores(scores: list[float]) -> tuple[float, float, float, float]:
    a = np.asarray(scores, dtype=np.float32)
    return float(a.mean()), float(a.min()), float(a.std()), float(a.max())

def main() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"[device] {device}", flush=True)
    encoder = load_encoder(device)
    candidates = load_candidate_embeddings(encoder, device)
    labels = build_label_index()
    print(f"[labels] indexed {len(labels)} WAV paths", flush=True)

    rows = []
    for filekey, archive_name in ARCHIVES:
        print(f"\n[download] {archive_name} filekey={filekey}", flush=True)
        download(DATASET_KEY, DOWNLOAD_DIR, filekeys=[filekey])
        matches = list(DOWNLOAD_DIR.rglob(archive_name))
        if len(matches) != 1:
            raise RuntimeError(f"expected one {archive_name}, found {len(matches)}")
        zpath = matches[0]

        with zipfile.ZipFile(zpath) as zf:
            wav_names = [n for n in zf.namelist() if n.lower().endswith(".wav")]
            for idx, member in enumerate(wav_names, 1):
                try:
                    wav, sr = sf.read(io.BytesIO(zf.read(member)), dtype="float32", always_2d=False)
                    source_emb = embed_audio(encoder, device, wav, sr)
                    if source_emb is None:
                        continue
                    meta = labels.get(Path(member).name, {})
                    for candidate, vecs in candidates.items():
                        scores = [float(np.dot(v, source_emb)) for v in vecs]
                        mean, minimum, std, maximum = summarize_scores(scores)
                        rows.append({
                            "candidate": candidate,
                            "wav": Path(member).name,
                            "archive": archive_name,
                            "mean": mean,
                            "min": minimum,
                            "std": std,
                            "max": maximum,
                            "scores": ";".join(f"{x:.6f}" for x in scores),
                            **meta,
                        })
                except Exception as exc:
                    print(f"[warn] {Path(member).name}: {type(exc).__name__}: {exc}", flush=True)
                if idx % 100 == 0 or idx == len(wav_names):
                    print(f"[progress] {archive_name}: {idx}/{len(wav_names)}", flush=True)

        zpath.unlink(missing_ok=True)
        print(f"[done] {archive_name}; source ZIP deleted", flush=True)

    rows.sort(key=lambda r: (r["candidate"], -r["mean"], -r["min"], r["std"]))
    fields = [
        "candidate", "wav", "archive", "mean", "min", "std", "max", "scores",
        "role", "occupation", "gender", "ageRange", "experience", "audioPath", "text", "labelZip"
    ]
    with RESULT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k) for k in fields})

    summary = {}
    for candidate in ("questioner", "coach"):
        subset = [r for r in rows if r["candidate"] == candidate]
        subset.sort(key=lambda r: (-r["mean"], -r["min"], r["std"]))
        summary[candidate] = subset[:30]
        print(f"\nTOP 15 {candidate}", flush=True)
        for r in subset[:15]:
            print(
                f"mean={r['mean']:.6f} min={r['min']:.6f} std={r['std']:.6f} "
                f"max={r['max']:.6f}\t{r['wav']}\t{r.get('role','')}\t{r['archive']}",
                flush=True,
            )

    SUMMARY_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[complete] {RESULT_CSV}", flush=True)
    print(f"[complete] {SUMMARY_JSON}", flush=True)

if __name__ == "__main__":
    main()
