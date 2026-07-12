"""Configuracao central do app.

Aqui ficam as preferencias globais: qual motor usar, o limiar de
confianca, o modo de organizacao e o mapa de rotulos PT-BR -> tag interna
(em ingles, que o CLIP entende melhor).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# Troque aqui o motor ativo: "clip" (real) ou "fake" (testes).
DEFAULT_ENGINE = "clip"

# Score minimo (0.0-1.0) para uma tag ser aplicada a uma foto.
# Com o softmax do CLIP (ADR-09) os scores sao probabilidades que somam 1
# entre as tags. Numa foto com uma tag dominante, ela fica bem acima de
# 0.20; fotos genuinamente multi-tag dividem a probabilidade, entao 0.20
# ainda captura duas tags fortes. Ajuste conforme seus resultados.
DEFAULT_THRESHOLD = 0.20

# "copy" (duplica os bytes) ou "hardlink" (compartilha, economiza disco).
DEFAULT_ORGANIZE_MODE = "copy"

# Se True, fotos que ja tem keywords sao puladas (nao recebem tags novas).
SKIP_ALREADY_TAGGED = False

_TAGS_FILE = Path(__file__).resolve().parent.parent / "tags.json"


@dataclass
class Config:
    engine: str = DEFAULT_ENGINE
    threshold: float = DEFAULT_THRESHOLD
    organize_mode: str = DEFAULT_ORGANIZE_MODE
    skip_already_tagged: bool = SKIP_ALREADY_TAGGED
    # rotulo exibido (PT-BR) -> tag interna (ingles, para o motor).
    tag_labels: dict[str, str] = field(default_factory=dict)

    @property
    def engine_tags(self) -> list[str]:
        """Tags internas (em ingles) enviadas ao motor."""
        return list(self.tag_labels.values())

    def label_for(self, engine_tag: str) -> str:
        """Rotulo PT-BR de uma tag interna (para exibir / nomear pastas)."""
        for label, internal in self.tag_labels.items():
            if internal == engine_tag:
                return label
        return engine_tag


def load_config() -> Config:
    """Carrega a config, lendo as tags de tags.json."""
    labels: dict[str, str] = {}
    if _TAGS_FILE.exists():
        labels = json.loads(_TAGS_FILE.read_text(encoding="utf-8"))
    return Config(tag_labels=labels)
