"""Orquestracao: junta motor + metadados + organizacao.

Este e o miolo reutilizavel, independente de interface. Tanto a CLI
quanto o app Gradio chamam estas funcoes. Ele nao sabe qual motor esta
rodando -- so conversa com o contrato TaggerEngine.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .base_types import IMAGE_EXTENSIONS
from .config import Config
from .engines.base import TaggerEngine
from .engines.registry import get_engine
from . import metadata, organizer


@dataclass
class Suggestion:
    """Resultado da classificacao de uma foto (antes de aplicar)."""

    image_path: Path
    scores: dict[str, float]              # tag interna -> score
    accepted: set[str]                    # tags acima do limiar
    already_tagged: bool                  # ja tinha keywords?


def build_engine(config: Config) -> TaggerEngine:
    """Cria e carrega o motor definido na config."""
    engine = get_engine(config.engine)
    engine.load()
    return engine


def list_images(folder: Path) -> list[Path]:
    """Lista as imagens suportadas numa pasta (nao-recursivo)."""
    return sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )


def classify_images(
    engine: TaggerEngine,
    images: list[Path],
    config: Config,
) -> list[Suggestion]:
    """Classifica cada imagem e monta as sugestoes (sem tocar nos arquivos)."""
    tags = config.engine_tags
    suggestions: list[Suggestion] = []
    for image in images:
        already = metadata.has_keywords(image)
        scores = engine.classify(image, tags)
        accepted = {t for t, s in scores.items() if s >= config.threshold}
        suggestions.append(
            Suggestion(
                image_path=image,
                scores=scores,
                accepted=accepted,
                already_tagged=already,
            )
        )
    return suggestions


def apply_suggestion(
    suggestion: Suggestion,
    config: Config,
    output_root: Path,
) -> None:
    """Aplica uma sugestao: grava keywords (merge) + organiza em pastas.

    Respeita `skip_already_tagged` e usa os rotulos PT-BR como nome de
    pasta / keyword. Nunca sobrescreve metadados existentes.
    """
    if config.skip_already_tagged and suggestion.already_tagged:
        return
    if not suggestion.accepted:
        return

    labels = {config.label_for(t) for t in suggestion.accepted}
    metadata.write_keywords(suggestion.image_path, labels)
    organizer.organize(
        suggestion.image_path,
        labels,
        output_root,
        mode=config.organize_mode,
    )
