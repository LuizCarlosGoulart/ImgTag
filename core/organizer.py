"""Organizacao fisica das fotos em pastas por tag.

Como o projeto e multi-tag, uma foto pode pertencer a varias pastas ao
mesmo tempo. Por isso o padrao e COPIAR (nunca mover): o original fica no
lugar e aparece em cada pasta de tag que se aplica.

Modo `hardlink` economiza disco: a mesma foto aparece em N pastas sem
duplicar os bytes (so funciona dentro do mesmo volume/disco).
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def organize(
    image_path: Path,
    tags: set[str],
    output_root: Path,
    mode: str = "copy",
) -> list[Path]:
    """Coloca a imagem na pasta de cada tag sob `output_root`.

    Args:
        image_path: arquivo original (nunca e movido/apagado).
        tags: tags aplicadas -> uma subpasta por tag.
        output_root: raiz onde as pastas de tag sao criadas.
        mode: "copy" (duplica) ou "hardlink" (compartilha os bytes).

    Returns:
        Lista dos caminhos de destino criados.
    """
    destinos: list[Path] = []
    for tag in sorted(tags):
        tag_dir = output_root / tag
        tag_dir.mkdir(parents=True, exist_ok=True)
        destino = tag_dir / image_path.name

        if destino.exists():
            destinos.append(destino)  # Ja organizado antes -- idempotente.
            continue

        if mode == "hardlink":
            try:
                os.link(image_path, destino)
            except OSError:
                # Volumes diferentes nao permitem hardlink -> cai para copia.
                shutil.copy2(image_path, destino)
        else:
            shutil.copy2(image_path, destino)

        destinos.append(destino)
    return destinos
