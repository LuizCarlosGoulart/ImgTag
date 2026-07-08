"""Motor falso para testes e desenvolvimento.

Nao carrega modelo nenhum: devolve scores deterministicos derivados do
nome do arquivo + tag. Serve para exercitar toda a logica de metadados e
organizacao de pastas sem depender do CLIP (que e pesado de carregar).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from .base import TaggerEngine


class FakeEngine(TaggerEngine):
    name = "fake"

    def load(self) -> None:
        # Nada a carregar.
        pass

    def classify(self, image_path: Path, tags: list[str]) -> dict[str, float]:
        scores: dict[str, float] = {}
        for tag in tags:
            seed = f"{image_path.name}:{tag}".encode("utf-8")
            digest = hashlib.sha256(seed).digest()
            # Primeiro byte -> score estavel em 0.0-1.0.
            scores[tag] = digest[0] / 255.0
        return scores

    @property
    def info(self) -> str:
        return "FakeEngine (scores deterministicos, sem modelo)"
