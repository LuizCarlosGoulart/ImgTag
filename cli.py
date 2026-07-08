"""CLI minima -- fase 1: validar que o motor classifica bem as suas fotos.

Uso:
    python cli.py <pasta_de_imagens>            # so mostra as sugestoes
    python cli.py <pasta> --apply <saida>       # grava tags + organiza
    python cli.py <pasta> --engine fake         # usa o motor de teste

Comece SEM --apply: veja se as tags fazem sentido antes de tocar nos
arquivos. Quando confiar, rode com --apply apontando para uma pasta de
saida (de preferencia numa copia do acervo, na primeira vez).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from core.config import load_config
from core.pipeline import (
    apply_suggestion,
    build_engine,
    classify_images,
    list_images,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="ImgTag - classificador de fotos")
    parser.add_argument("folder", type=Path, help="Pasta com as imagens")
    parser.add_argument("--apply", type=Path, metavar="SAIDA",
                        help="Aplica (grava tags + organiza) nesta pasta de saida")
    parser.add_argument("--engine", help="Motor a usar (sobrescreve a config)")
    parser.add_argument("--threshold", type=float,
                        help="Limiar de score 0.0-1.0 (sobrescreve a config)")
    args = parser.parse_args()

    config = load_config()
    if args.engine:
        config.engine = args.engine
    if args.threshold is not None:
        config.threshold = args.threshold

    if not config.tag_labels:
        parser.error("Nenhuma tag definida em tags.json.")

    images = list_images(args.folder)
    if not images:
        parser.error(f"Nenhuma imagem suportada em {args.folder}")

    print(f"Motor: {config.engine} | limiar: {config.threshold} | "
          f"{len(images)} imagem(ns)\n")

    engine = build_engine(config)
    print(f"-> {engine.info}\n")

    suggestions = classify_images(engine, images, config)

    for s in suggestions:
        flag = " [ja taggeada]" if s.already_tagged else ""
        aceitas = ", ".join(sorted(config.label_for(t) for t in s.accepted)) or "-"
        print(f"{s.image_path.name}{flag}")
        print(f"   aceitas: {aceitas}")
        ranked = sorted(s.scores.items(), key=lambda kv: kv[1], reverse=True)
        detalhe = "  ".join(f"{config.label_for(t)}={v:.2f}" for t, v in ranked)
        print(f"   scores : {detalhe}\n")

    if args.apply:
        print(f"Aplicando em {args.apply} (modo {config.organize_mode})...")
        for s in suggestions:
            apply_suggestion(s, config, args.apply)
        print("Concluido.")
    else:
        print("Modo previa (sem --apply): nenhum arquivo foi alterado.")


if __name__ == "__main__":
    main()
