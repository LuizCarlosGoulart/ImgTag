"""Motor baseado em CLIP (open_clip), rodando localmente.

Implementacao da fase 1. As dependencias pesadas (torch, open_clip) sao
importadas dentro de `load()` para que o app possa iniciar e listar
motores mesmo sem elas instaladas -- so quebra se voce realmente escolher
usar o CLIP.

Score: usa similaridade de cosseno entre o embedding da imagem e o de
cada tag, mapeada para 0.0-1.0. Nao usa softmax entre as tags de proposito
-- queremos multi-tag, entao cada tag e avaliada de forma independente.
"""

from __future__ import annotations

from pathlib import Path

from .base import TaggerEngine

# Prompt-engineering simples: o CLIP compara melhor frases do que palavras
# soltas. "a photo of {tag}" e o template classico da literatura.
_PROMPT_TEMPLATE = "a photo of {tag}"


class CLIPEngine(TaggerEngine):
    name = "clip"

    def __init__(self, model_name: str = "ViT-B-32", pretrained: str = "openai"):
        self.model_name = model_name
        self.pretrained = pretrained
        self._model = None
        self._preprocess = None
        self._tokenizer = None
        self._device = "cpu"
        # Cache dos embeddings de texto: as tags mudam pouco entre imagens.
        self._text_cache: dict[str, "object"] = {}

    def load(self) -> None:
        import open_clip
        import torch

        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        model, _, preprocess = open_clip.create_model_and_transforms(
            self.model_name, pretrained=self.pretrained
        )
        model.eval().to(self._device)
        self._model = model
        self._preprocess = preprocess
        self._tokenizer = open_clip.get_tokenizer(self.model_name)

    def _encode_tags(self, tags: list[str]):
        import torch

        missing = [t for t in tags if t not in self._text_cache]
        if missing:
            prompts = [_PROMPT_TEMPLATE.format(tag=t) for t in missing]
            tokens = self._tokenizer(prompts).to(self._device)
            with torch.no_grad():
                feats = self._model.encode_text(tokens)
                feats /= feats.norm(dim=-1, keepdim=True)
            for tag, feat in zip(missing, feats):
                self._text_cache[tag] = feat
        return torch.stack([self._text_cache[t] for t in tags])

    def classify(self, image_path: Path, tags: list[str]) -> dict[str, float]:
        import torch
        from PIL import Image

        if self._model is None:
            raise RuntimeError("Motor CLIP nao carregado. Chame load() antes.")

        image = Image.open(image_path).convert("RGB")
        image_input = self._preprocess(image).unsqueeze(0).to(self._device)

        with torch.no_grad():
            img_feat = self._model.encode_image(image_input)
            img_feat /= img_feat.norm(dim=-1, keepdim=True)
            text_feats = self._encode_tags(tags)
            # Cosseno em -1..1 -> mapeia para 0..1.
            sims = (img_feat @ text_feats.T).squeeze(0)
            scores = ((sims + 1.0) / 2.0).cpu().tolist()

        return {tag: float(score) for tag, score in zip(tags, scores)}

    @property
    def info(self) -> str:
        return f"CLIP ({self.model_name}/{self.pretrained}) em {self._device}"
