from __future__ import annotations

import argparse
import csv
import gc
import json
import math
import re
import shutil
import zipfile
from pathlib import Path

import librosa
import numpy as np
import torch
import torch.nn.functional as F
from qwen_tts import Qwen3TTSModel

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROOT = PROJECT_ROOT / ".cache" / "aihub71592"
WORK = ROOT / "membership_pilot"
PREPARED = WORK / "prepared"
STATE_PATH = WORK / "state.json"
MANIFEST_PATH = WORK / "manifest.csv"
RESULTS_PATH = WORK / "membership_scores.csv"

EXT_MEMBERS = ROOT / "interviewer_clustering_extended" / "cluster_members.csv"
TARGET_META = ROOT / "target_metadata_analysis" / "target_metadata.csv"
NEW_MATCHES = ROOT / "seeded_new_matches" / "matches.csv"
OLD_AUDIO = ROOT / "interviewer_clustering_pilot" / "question_wavs"
NEW_AUDIO = ROOT / "seeded_new_matches" / "high_confidence_audio"
VAL_AUDIO = PROJECT_ROOT / ".cache" / "tts-provenance" / "listening_validation_top"
VAL_LABELS = ROOT / "labels_vl"

MODEL_PATHS = {
    "questioner": PROJECT_ROOT / "models/tts/questioner_candidate04/model_or_adapter",
    "coach": PROJECT_ROOT / "models/tts/coach_candidate01/model_or_adapter",
}
TARGET_CLUSTERS = {"questioner": "C008", "coach": "C027"}

TRAIN_PER_ROLE = 20
NEW_PER_ROLE = 6
VAL_CONTROLS_PER_ROLE = 4
STATE_VERSION = 1


def find_base_snapshot() -> Path:
    hub = Path.home() / ".cache/huggingface/hub/models--Qwen--Qwen3-TTS-12Hz-0.6B-Base/snapshots"
    if not hub.exists():
        raise RuntimeError(f"base model cache missing: {hub}")
    candidates = [
        p for p in hub.iterdir()
        if (p / "config.json").exists() and (p / "model.safetensors").exists()
    ]
    if not candidates:
        raise RuntimeError("no complete local 0.6B Base snapshot found")
    candidates.sort(key=lambda p: p.name)
    return candidates[-1]


def read_csv(path):
    return list(csv.DictReader(path.open(encoding="utf-8-sig")))


def numeric_id(wav):
    m = re.search(r"_(\d+)\.wav$", wav)
    return int(m.group(1)) if m else -1


def extract_original_wav_name(path: Path) -> str:
    m = re.search(r"(ckmk_q_[^/\\]+\.wav)", path.name)
    if not m:
        raise RuntimeError(f"cannot recover original wav name from {path}")
    return m.group(1)


def build_validation_label_lookup(wanted_wavs):
    wanted = set(wanted_wavs)
    found = {}
    for zpath in sorted(VAL_LABELS.rglob("*.zip")):
        if len(found) == len(wanted):
            break
        with zipfile.ZipFile(zpath) as zf:
            for name in zf.namelist():
                if not name.lower().endswith(".json"):
                    continue
                base = Path(name).name
                wav = re.sub(r"^ckmk_d_", "ckmk_q_", base[:-5] + ".wav")
                if wav not in wanted or wav in found:
                    continue
                obj = json.loads(zf.read(name).decode("utf-8-sig"))
                found[wav] = obj["dataSet"]["question"]["raw"]["text"]
    missing = sorted(wanted - set(found))
    if missing:
        raise RuntimeError(f"validation labels missing for: {missing}")
    return found


def build_manifest():
    meta = {r["wav"]: r for r in read_csv(TARGET_META)}
    ext = read_csv(EXT_MEMBERS)
    new = read_csv(NEW_MATCHES)

    rows = []
    ref_paths = {}

    for role in ("questioner", "coach"):
        # Experienced candidates whose WAVs survived from the original 8-archive pilot.
        exp = []
        for r in ext:
            if r["cluster"] != TARGET_CLUSTERS[role]:
                continue
            wav = r["wav"]
            audio = OLD_AUDIO / r["filekey"] / wav
            if not audio.exists() or wav not in meta:
                continue
            exp.append((
                float(r["similarity_to_cluster_centroid"]),
                numeric_id(wav),
                wav,
                audio,
                meta[wav]["question"],
            ))
        exp.sort(key=lambda x: (-x[0], x[1]))

        # High-confidence New candidates with retained WAVs.
        nr = []
        for r in new:
            if r["best_role"] != role or r["confidence"] != "high":
                continue
            wav = r["wav"]
            audio = NEW_AUDIO / role / f"{r['filekey']}_{wav}"
            if not audio.exists() or wav not in meta:
                continue
            nr.append((
                float(r["best_score"]),
                numeric_id(wav),
                wav,
                audio,
                meta[wav]["question"],
            ))
        nr.sort(key=lambda x: (-x[0], x[1]))

        n_new = min(NEW_PER_ROLE, len(nr))
        n_exp = TRAIN_PER_ROLE - n_new
        selected = [("train_exp", x) for x in exp[:n_exp]] + [("train_new", x) for x in nr[:n_new]]
        if len(selected) < TRAIN_PER_ROLE:
            raise RuntimeError(f"not enough retained training candidates for {role}: {len(selected)}")

        for source, (score, _, wav, audio, text) in selected:
            rows.append({
                "role": role,
                "split": "train_candidate",
                "source": source,
                "wav": wav,
                "audio_path": str(audio.relative_to(PROJECT_ROOT)),
                "text": text,
                "speaker_match_score": score,
            })

        # Validation rank01 is used only as canonical ref_audio; rank02..05 are controls.
        val_paths = sorted((VAL_AUDIO / role).glob("rank*.wav"))
        if len(val_paths) < 5:
            raise RuntimeError(f"expected >=5 validation WAVs for {role}, got {len(val_paths)}")
        ref_paths[role] = val_paths[0]
        controls = val_paths[1:1 + VAL_CONTROLS_PER_ROLE]
        label_lookup = build_validation_label_lookup([extract_original_wav_name(p) for p in controls])
        for p in controls:
            wav = extract_original_wav_name(p)
            rows.append({
                "role": role,
                "split": "validation_control",
                "source": "validation",
                "wav": wav,
                "audio_path": str(p.relative_to(PROJECT_ROOT)),
                "text": label_lookup[wav],
                "speaker_match_score": "",
            })

    WORK.mkdir(parents=True, exist_ok=True)
    fields = ["role","split","source","wav","audio_path","text","speaker_match_score"]
    with MANIFEST_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return rows, ref_paths


def load_state():
    if not STATE_PATH.exists():
        return {"version": STATE_VERSION, "scores": {}}
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    if state.get("version") != STATE_VERSION:
        raise RuntimeError("membership pilot state version mismatch; use --reset")
    return state


def save_state(state):
    WORK.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE_PATH)


def sample_key(row):
    return f"{row['role']}|{row['split']}|{row['wav']}"


def prepared_path(row):
    safe = sample_key(row).replace("|", "__")
    return PREPARED / f"{safe}.pt"


def load_tts(path, device):
    dtype = torch.bfloat16 if device.startswith("cuda") else torch.float32
    return Qwen3TTSModel.from_pretrained(
        str(path),
        device_map=device,
        dtype=dtype,
        attn_implementation="sdpa",
        local_files_only=True,
    )


def canonical_speaker_embedding(base_tts, ref_path: Path):
    wav, _ = librosa.load(str(ref_path), sr=24000, mono=True)
    emb = base_tts.model.extract_speaker_embedding(wav.astype(np.float32), 24000)
    return emb.detach().float().cpu()


def prepare_sample(base_tts, row):
    path = PROJECT_ROOT / row["audio_path"]
    text = f"<|im_start|>assistant\n{row['text']}<|im_end|>\n<|im_start|>assistant\n"
    proc = base_tts.processor(text=text, return_tensors="pt", padding=True)
    text_ids = proc["input_ids"]
    text_ids = text_ids.unsqueeze(0) if text_ids.dim() == 1 else text_ids
    text_ids = text_ids[:, :-5].cpu().long()

    enc = base_tts.model.speech_tokenizer.encode([str(path)])
    audio_codes = enc.audio_codes[0].detach().cpu().long()
    if audio_codes.ndim != 2 or audio_codes.shape[1] != 16:
        raise RuntimeError(f"unexpected audio code shape for {row['wav']}: {tuple(audio_codes.shape)}")

    return {"text_ids": text_ids, "audio_codes": audio_codes}


def pack_sample(prepared, config):
    text_ids = prepared["text_ids"]
    audio_codes = prepared["audio_codes"]

    text_len = text_ids.shape[1]
    codec_len = audio_codes.shape[0]
    t = text_len + codec_len + 8

    input_ids = torch.zeros((1, t, 2), dtype=torch.long)
    codec_ids = torch.zeros((1, t, 16), dtype=torch.long)
    text_embedding_mask = torch.zeros((1, t), dtype=torch.bool)
    codec_embedding_mask = torch.zeros((1, t), dtype=torch.bool)
    codec_mask = torch.zeros((1, t), dtype=torch.bool)
    attention_mask = torch.zeros((1, t), dtype=torch.long)
    codec_0_labels = torch.full((1, t), -100, dtype=torch.long)

    audio_codec_0 = audio_codes[:, 0]

    input_ids[0, :3, 0] = text_ids[0, :3]
    input_ids[0, 3:7, 0] = config.tts_pad_token_id
    input_ids[0, 7, 0] = config.tts_bos_token_id
    input_ids[0, 8:8 + text_len - 3, 0] = text_ids[0, 3:]
    input_ids[0, 8 + text_len - 3, 0] = config.tts_eos_token_id
    input_ids[0, 8 + text_len - 2:8 + text_len + codec_len, 0] = config.tts_pad_token_id
    text_embedding_mask[0, :8 + text_len + codec_len] = True

    input_ids[0, 3:8, 1] = torch.tensor([
        config.talker_config.codec_nothink_id,
        config.talker_config.codec_think_bos_id,
        config.talker_config.codec_think_eos_id,
        0,
        config.talker_config.codec_pad_id,
    ])
    input_ids[0, 8:8 + text_len - 3, 1] = config.talker_config.codec_pad_id
    input_ids[0, 8 + text_len - 3, 1] = config.talker_config.codec_pad_id
    input_ids[0, 8 + text_len - 2, 1] = config.talker_config.codec_bos_id
    start = 8 + text_len - 1
    input_ids[0, start:start + codec_len, 1] = audio_codec_0
    input_ids[0, start + codec_len, 1] = config.talker_config.codec_eos_token_id

    codec_0_labels[0, start:start + codec_len] = audio_codec_0
    codec_0_labels[0, start + codec_len] = config.talker_config.codec_eos_token_id
    codec_ids[0, start:start + codec_len, :] = audio_codes

    codec_embedding_mask[0, 3:8 + text_len + codec_len] = True
    codec_embedding_mask[0, 6] = False
    codec_mask[0, start:start + codec_len] = True
    attention_mask[0, :8 + text_len + codec_len] = True

    return {
        "input_ids": input_ids,
        "codec_ids": codec_ids,
        "text_embedding_mask": text_embedding_mask.unsqueeze(-1),
        "codec_embedding_mask": codec_embedding_mask.unsqueeze(-1),
        "attention_mask": attention_mask,
        "codec_0_labels": codec_0_labels,
        "codec_mask": codec_mask,
    }


@torch.inference_mode()
def score_sample(tts, prepared, speaker_embedding):
    model = tts.model
    device = next(model.parameters()).device
    dtype = next(model.parameters()).dtype

    batch = pack_sample(prepared, model.config)
    input_ids = batch["input_ids"].to(device)
    codec_ids = batch["codec_ids"].to(device)
    text_mask = batch["text_embedding_mask"].to(device)
    codec_emb_mask = batch["codec_embedding_mask"].to(device)
    attention_mask = batch["attention_mask"].to(device)
    labels = batch["codec_0_labels"].to(device)
    codec_mask = batch["codec_mask"].to(device)

    input_text_ids = input_ids[:, :, 0]
    input_codec_ids = input_ids[:, :, 1]

    # Local model dimensions are 2048 text -> 1024 talker; surviving fine-tuned
    # checkpoints show changed text_projection weights, so projection was trainable.
    text_emb = model.talker.text_projection(
        model.talker.model.text_embedding(input_text_ids)
    )
    text_emb = text_emb * text_mask

    codec_emb = model.talker.model.codec_embedding(input_codec_ids) * codec_emb_mask
    codec_emb[:, 6, :] = speaker_embedding.to(device=device, dtype=dtype).view(1, -1)

    input_emb = text_emb + codec_emb
    for i in range(1, 16):
        emb_i = model.talker.code_predictor.get_input_embeddings()[i - 1](codec_ids[:, :, i])
        input_emb = input_emb + emb_i * codec_mask.unsqueeze(-1)

    outputs = model.talker(
        inputs_embeds=input_emb[:, :-1, :],
        attention_mask=attention_mask[:, :-1],
        labels=labels[:, 1:],
        output_hidden_states=True,
        use_cache=False,
    )

    recipe_codec0 = float(outputs.loss.detach().float().cpu())

    logits = outputs.logits.float()
    explicit_targets = labels[:, 1:]
    explicit_mask = explicit_targets != -100
    if not torch.any(explicit_mask):
        raise RuntimeError("no codec targets")
    explicit_codec0 = float(
        F.cross_entropy(logits[explicit_mask], explicit_targets[explicit_mask]).detach().cpu()
    )

    hidden_states = outputs.hidden_states[0][-1]
    talker_hidden = hidden_states[codec_mask[:, :-1]]
    talker_codec_ids = codec_ids[codec_mask]
    _, sub_loss = model.talker.forward_sub_talker_finetune(talker_codec_ids, talker_hidden)
    sub = float(sub_loss.detach().float().cpu())

    return {
        "recipe_codec0_loss": recipe_codec0,
        "explicit_codec0_loss": explicit_codec0,
        "subtalker_loss": sub,
        "recipe_total_loss": recipe_codec0 + 0.3 * sub,
        "explicit_total_loss": explicit_codec0 + 0.3 * sub,
        "codec_frames": int(talker_codec_ids.shape[0]),
    }


def write_results(rows, state):
    fields = [
        "role","split","source","wav","audio_path","speaker_match_score",
        "base_recipe_total","ft_recipe_total","delta_recipe",
        "base_explicit_total","ft_explicit_total","delta_explicit",
        "base_codec0","ft_codec0","base_subtalker","ft_subtalker","codec_frames",
    ]
    out = []
    for row in rows:
        key = sample_key(row)
        score = state["scores"].get(key, {})
        b = score.get("base")
        f = score.get("finetuned")
        rec = {k: row.get(k, "") for k in ["role","split","source","wav","audio_path","speaker_match_score"]}
        if b:
            rec.update({
                "base_recipe_total": b["recipe_total_loss"],
                "base_explicit_total": b["explicit_total_loss"],
                "base_codec0": b["recipe_codec0_loss"],
                "base_subtalker": b["subtalker_loss"],
                "codec_frames": b["codec_frames"],
            })
        if f:
            rec.update({
                "ft_recipe_total": f["recipe_total_loss"],
                "ft_explicit_total": f["explicit_total_loss"],
                "ft_codec0": f["recipe_codec0_loss"],
                "ft_subtalker": f["subtalker_loss"],
            })
        if b and f:
            rec["delta_recipe"] = b["recipe_total_loss"] - f["recipe_total_loss"]
            rec["delta_explicit"] = b["explicit_total_loss"] - f["explicit_total_loss"]
        out.append(rec)

    with RESULTS_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)


def summarize(rows, state):
    print("\n=== PILOT SUMMARY ===")
    for role in ("questioner", "coach"):
        print(f"\n[{role}]")
        for metric in ("delta_recipe", "delta_explicit"):
            vals = {"train_candidate": [], "validation_control": []}
            for row in rows:
                if row["role"] != role:
                    continue
                s = state["scores"].get(sample_key(row), {})
                if "base" not in s or "finetuned" not in s:
                    continue
                b, f = s["base"], s["finetuned"]
                if metric == "delta_recipe":
                    d = b["recipe_total_loss"] - f["recipe_total_loss"]
                else:
                    d = b["explicit_total_loss"] - f["explicit_total_loss"]
                vals[row["split"]].append(d)
            print(metric)
            for split, arr in vals.items():
                if arr:
                    a = np.asarray(arr, dtype=float)
                    print(
                        f"  {split}: n={len(a)} mean={a.mean():.6f} "
                        f"median={np.median(a):.6f} min={a.min():.6f} max={a.max():.6f}"
                    )

        ranked = []
        for row in rows:
            if row["role"] != role or row["split"] != "train_candidate":
                continue
            s = state["scores"].get(sample_key(row), {})
            if "base" in s and "finetuned" in s:
                ranked.append((
                    s["base"]["explicit_total_loss"] - s["finetuned"]["explicit_total_loss"],
                    row["wav"],
                ))
        ranked.sort(reverse=True)
        print("  top train candidates by delta_explicit:")
        for d, wav in ranked[:10]:
            print(f"    {d:+.6f}  {wav}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--reset", action="store_true")
    args = ap.parse_args()

    if args.reset and WORK.exists():
        shutil.rmtree(WORK)

    rows, ref_paths = build_manifest()
    print(f"[plan] samples={len(rows)}")
    for role in ("questioner","coach"):
        tr=sum(r["role"]==role and r["split"]=="train_candidate" for r in rows)
        va=sum(r["role"]==role and r["split"]=="validation_control" for r in rows)
        print(f"  {role}: train_candidates={tr}, validation_controls={va}, ref={ref_paths[role].name}")
    print(f"[manifest] {MANIFEST_PATH.relative_to(PROJECT_ROOT)}")

    if not args.run:
        print("[safe] no --run: no model scoring performed")
        return

    WORK.mkdir(parents=True, exist_ok=True)
    PREPARED.mkdir(parents=True, exist_ok=True)
    state = load_state()

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    base_path = find_base_snapshot()
    print(f"[device] {device}")
    print(f"[base] {base_path}")

    # Phase 1: Base model, canonical speaker embeddings, audio-code preparation, base scoring.
    print("\n[phase 1] loading base model", flush=True)
    base = load_tts(base_path, device)
    speaker_embs = {}
    for role in ("questioner","coach"):
        emb_path = WORK / f"{role}_speaker_embedding.pt"
        if emb_path.exists():
            speaker_embs[role] = torch.load(emb_path, map_location="cpu")
        else:
            speaker_embs[role] = canonical_speaker_embedding(base, ref_paths[role])
            torch.save(speaker_embs[role], emb_path)
        print(f"[speaker] {role} embedding ready", flush=True)

    for i, row in enumerate(rows, 1):
        key = sample_key(row)
        pp = prepared_path(row)
        if pp.exists():
            prepared = torch.load(pp, map_location="cpu")
        else:
            prepared = prepare_sample(base, row)
            torch.save(prepared, pp)

        state["scores"].setdefault(key, {})
        if "base" not in state["scores"][key]:
            state["scores"][key]["base"] = score_sample(base, prepared, speaker_embs[row["role"]])
            save_state(state)
            write_results(rows, state)
        print(f"[base {i:02d}/{len(rows)}] {row['role']} {row['split']} {row['wav']}", flush=True)

    del base
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # Phase 2: score each role with its fine-tuned model.
    for role in ("questioner","coach"):
        print(f"\n[phase 2] loading fine-tuned {role}", flush=True)
        ft = load_tts(MODEL_PATHS[role], device)
        role_rows = [r for r in rows if r["role"] == role]
        for i, row in enumerate(role_rows, 1):
            key = sample_key(row)
            state["scores"].setdefault(key, {})
            if "finetuned" not in state["scores"][key]:
                prepared = torch.load(prepared_path(row), map_location="cpu")
                state["scores"][key]["finetuned"] = score_sample(
                    ft, prepared, speaker_embs[role]
                )
                save_state(state)
                write_results(rows, state)
            print(f"[{role} {i:02d}/{len(role_rows)}] {row['split']} {row['wav']}", flush=True)

        del ft
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    write_results(rows, state)
    summarize(rows, state)
    print(f"\n[result] {RESULTS_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
