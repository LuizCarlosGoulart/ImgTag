"""Motor baseado em CLIP (open_clip), rodando localmente.

Implementacao da fase 1. As dependencias pesadas (torch, open_clip) sao
importadas dentro de `load()` para que o app possa iniciar e listar
motores mesmo sem elas instaladas -- so quebra se voce realmente escolher
usar o CLIP.

Score: softmax (com temperatura) sobre a similaridade de cosseno entre a
imagem e cada tag. Ver ADR-09 em DECISIONS.md.
"""

from __future__ import annotations

from pathlib import Path

from .base import TaggerEngine

# Ensemble de prompts (tecnica da OpenAI): em vez de uma unica frase,
# descrevemos a tag de varias formas e tiramos a media dos embeddings de
# texto. Isso reduz o vies de uma frase so e melhora a acuracia -- em
# especial para tags cujo termo isolado e ambiguo (ex.: "people" casa mal
# com um retrato individual, mas "a portrait of a person" casa bem).
_PROMPT_TEMPLATES = [
    "a photo of {tag}",
    "a close-up photo of {tag}",
    "a photo containing {tag}",
    "an image of {tag}",
    "a picture of {tag}",
]


class CLIPEngine(TaggerEngine):
    name = "clip"

    # Usamos a variante -quickgelu porque os pesos "openai" foram treinados
    # com a ativacao QuickGELU. Casar os dois evita o aviso de mismatch e a
    # pequena perda de acuracia que ele indica.
    #
    # `temperature`: controla o quanto o softmax "espalha" os scores entre
    # as tags. Menor = mais decisivo (tende a uma tag dominante); maior =
    # mais suave (favorece multi-tag). ~0.05 e um bom ponto de partida para
    # 8 tags. Ver ADR-09 em DECISIONS.md.
    def __init__(
        self,
        model_name: str = "ViT-B-32-quickgelu",
        pretrained: str = "openai",
        temperature: float = 0.05,
    ):
        self.model_name = model_name
        self.pretrained = pretrained
        self.temperature = temperature
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
        for tag in missing:
            # Um embedding por template; media -> renormaliza. E o ensemble
            # de prompts que estabiliza a representacao da tag.
            prompts = [tpl.format(tag=tag) for tpl in _PROMPT_TEMPLATES]
            tokens = self._tokenizer(prompts).to(self._device)
            with torch.no_grad():
                feats = self._model.encode_text(tokens)
                feats /= feats.norm(dim=-1, keepdim=True)
                mean = feats.mean(dim=0)
                mean /= mean.norm()
            self._text_cache[tag] = mean
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
            # Similaridade de cosseno crua vive numa faixa estreita (~0.15-0.30)
            # e nao serve para thresholding direto. O softmax sobre as tags,
            # com temperatura, ESPALHA os scores e separa sinal de ruido -- e
            # a forma canonica de usar CLIP para classificacao zero-shot.
            sims = (img_feat @ text_feats.T).squeeze(0)
            probs = (sims / self.temperature).softmax(dim=-1)
            scores = probs.cpu().tolist()

        return {tag: float(score) for tag, score in zip(tags, scores)}

    @property
    def info(self) -> str:
        return f"CLIP ({self.model_name}/{self.pretrained}) em {self._device}"
