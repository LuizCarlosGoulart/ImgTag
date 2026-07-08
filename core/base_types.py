"""Tipos e constantes compartilhados, sem dependencias pesadas."""

from __future__ import annotations

# Extensoes de imagem suportadas. RAW/HEIC ficam fora do MVP -- precisam
# de tratamento especial de metadados (ver README, pontos em aberto).
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
