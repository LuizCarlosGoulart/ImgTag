"""Leitura e escrita de keywords nos metadados da imagem.

REGRA CENTRAL DO PROJETO: nunca sobrescrever tags que ja existem.
Sempre lemos as keywords atuais, fazemos a uniao com as novas e
regravamos. Fotos que voce ja organizou no passado permanecem intactas
(so ganham tags, nunca perdem).

Usa ExifTool por baixo (via pyexiftool), que preserva o resto do arquivo.
Grava tanto em XMP-dc:Subject quanto em IPTC:Keywords, os dois campos que
apps como Lightroom, digiKam e o Explorer do Windows reconhecem.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

# Candidatos de instalacao do ExifTool no Windows quando ele nao esta no
# PATH do processo atual (ex.: terminal aberto antes da instalacao).
_WINDOWS_FALLBACKS = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "ExifTool" / "ExifTool.exe",
    Path(os.environ.get("ProgramFiles", "")) / "ExifTool" / "exiftool.exe",
]


def _find_exiftool() -> str:
    """Localiza o executavel do ExifTool.

    Ordem: variavel EXIFTOOL_EXECUTABLE -> PATH -> locais conhecidos de
    instalacao no Windows. Assim o app funciona mesmo que o PATH do
    terminal atual nao tenha sido atualizado apos a instalacao.
    """
    env = os.environ.get("EXIFTOOL_EXECUTABLE")
    if env and Path(env).exists():
        return env

    found = shutil.which("exiftool") or shutil.which("ExifTool")
    if found:
        return found

    for candidate in _WINDOWS_FALLBACKS:
        if candidate.exists():
            return str(candidate)

    raise FileNotFoundError(
        "ExifTool nao encontrado. Instale de https://exiftool.org e garanta "
        "que esteja no PATH, ou defina a variavel EXIFTOOL_EXECUTABLE com o "
        "caminho do executavel."
    )


def _helper():
    """Cria um ExifToolHelper apontando para o executavel localizado."""
    import exiftool

    return exiftool.ExifToolHelper(executable=_find_exiftool())


def read_keywords(image_path: Path) -> set[str]:
    """Le as keywords ja presentes no arquivo (XMP + IPTC), sem duplicatas."""
    with _helper() as et:
        meta = et.get_tags(
            [str(image_path)],
            tags=["XMP-dc:Subject", "IPTC:Keywords"],
        )[0]

    existing: set[str] = set()
    for field in ("XMP:Subject", "IPTC:Keywords"):
        value = meta.get(field)
        if value is None:
            continue
        if isinstance(value, list):
            existing.update(str(v) for v in value)
        else:
            existing.add(str(value))
    return existing


def has_keywords(image_path: Path) -> bool:
    """True se a foto ja tem alguma keyword (para o modo 'pular ja-taggeadas')."""
    return len(read_keywords(image_path)) > 0


def write_keywords(image_path: Path, new_tags: set[str]) -> set[str]:
    """Faz merge das novas tags com as existentes e regrava.

    Nunca remove nada. Devolve o conjunto final de keywords do arquivo.
    Se a uniao nao acrescenta nada novo, nao toca no arquivo.
    """
    existing = read_keywords(image_path)
    merged = existing | {t for t in new_tags}

    if merged == existing:
        return existing  # Nada a fazer -- evita reescrever o arquivo a toa.

    ordered = sorted(merged)
    with _helper() as et:
        et.set_tags(
            [str(image_path)],
            tags={
                "XMP-dc:Subject": ordered,
                "IPTC:Keywords": ordered,
            },
            params=["-overwrite_original"],
        )
    return merged
