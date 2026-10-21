"""Checkpoint-compatible Wav2Vec2 speech emotion classifier."""

from pathlib import Path

import torch
import torch.nn as nn
from transformers import AutoProcessor, Wav2Vec2Model, Wav2Vec2PreTrainedModel


MODEL_NAME = "jungjongho/wav2vec2-xlsr-korean-speech-emotion-recognition"
LABELS = ["기쁨", "당황", "분노", "불안", "슬픔"]


class Wav2Vec2ClassificationHead(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.dense = nn.Linear(config.hidden_size, config.hidden_size)
        self.dropout = nn.Dropout(config.final_dropout)
        self.out_proj = nn.Linear(config.hidden_size, config.num_labels)

    def forward(self, features):
        features = self.dropout(features)
        features = torch.tanh(self.dense(features))
        return self.out_proj(self.dropout(features))


class Wav2Vec2ForSpeechClassification(Wav2Vec2PreTrainedModel):
    """Architecture matching the classifier keys in the selected checkpoint."""

    def __init__(self, config):
        super().__init__(config)
        self.num_labels = config.num_labels
        self.wav2vec2 = Wav2Vec2Model(config)
        self.classifier = Wav2Vec2ClassificationHead(config)
        self.post_init()

    def forward(self, input_values, attention_mask=None, labels=None, **kwargs):
        outputs = self.wav2vec2(
            input_values=input_values,
            attention_mask=attention_mask,
            **kwargs,
        )
        hidden_states = outputs.last_hidden_state
        if attention_mask is None:
            pooled = hidden_states.mean(dim=1)
        else:
            feature_mask = self._get_feature_vector_attention_mask(
                hidden_states.shape[1], attention_mask
            )
            masked = hidden_states.masked_fill(~feature_mask[:, :, None].bool(), 0.0)
            pooled = masked.sum(dim=1) / feature_mask.sum(dim=1)[:, None].clamp(min=1)

        logits = self.classifier(pooled)
        loss = None
        if labels is not None:
            loss = nn.CrossEntropyLoss()(logits, labels)
        return {"loss": loss, "logits": logits}


def load_model(model_name_or_path: str | Path = MODEL_NAME):
    processor = AutoProcessor.from_pretrained(model_name_or_path)
    model = Wav2Vec2ForSpeechClassification.from_pretrained(model_name_or_path)
    actual_labels = set(model.config.id2label.values())
    if actual_labels != set(LABELS):
        raise ValueError(f"예상 라벨과 다릅니다: {model.config.id2label}")
    return processor, model
