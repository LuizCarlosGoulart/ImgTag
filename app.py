"""Interface desktop (Gradio) -- fase 4.

Este arquivo e um esqueleto funcional do fluxo de 4 passos descrito no
plano: selecionar pasta + tags -> classificar -> revisar -> aplicar.
A logica de verdade vive em core/pipeline.py; aqui so montamos a tela.

Rode com:  python app.py
"""

from __future__ import annotations

from pathlib import Path

import gradio as gr

from core.config import load_config
from core.engines.registry import available_engines
from core.pipeline import (
    apply_suggestion,
    build_engine,
    classify_images,
    list_images,
)

# Estado carregado sob demanda (o motor e pesado).
_state: dict[str, object] = {}


def _do_classify(folder: str, engine_name: str, threshold: float):
    config = load_config()
    config.engine = engine_name
    config.threshold = threshold

    images = list_images(Path(folder))
    if not images:
        return "Nenhuma imagem suportada nessa pasta.", None

    engine = build_engine(config)
    suggestions = classify_images(engine, images, config)

    _state["config"] = config
    _state["suggestions"] = suggestions

    linhas = []
    for s in suggestions:
        aceitas = ", ".join(sorted(config.label_for(t) for t in s.accepted)) or "-"
        flag = " (ja taggeada)" if s.already_tagged else ""
        linhas.append([s.image_path.name + flag, aceitas])
    resumo = f"{len(images)} imagem(ns) classificada(s) com {engine.info}."
    return resumo, linhas


def _do_apply(output_root: str):
    if "suggestions" not in _state:
        return "Classifique as imagens primeiro."
    config = _state["config"]
    for s in _state["suggestions"]:
        apply_suggestion(s, config, Path(output_root))
    return f"Aplicado em {output_root} (modo {config.organize_mode})."


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="ImgTag") as demo:
        gr.Markdown("# ImgTag\nClassificacao de fotos por tags (motor trocavel).")

        with gr.Row():
            folder = gr.Textbox(label="Pasta de imagens")
            engine = gr.Dropdown(
                choices=available_engines(),
                value=available_engines()[0],
                label="Motor",
            )
            threshold = gr.Slider(0.0, 1.0, value=0.60, step=0.01, label="Limiar")

        classify_btn = gr.Button("Classificar", variant="primary")
        resumo = gr.Textbox(label="Resumo", interactive=False)
        tabela = gr.Dataframe(
            headers=["Imagem", "Tags aceitas"],
            label="Sugestoes (revise antes de aplicar)",
            interactive=False,
        )

        with gr.Row():
            output_root = gr.Textbox(label="Pasta de saida")
            apply_btn = gr.Button("Aplicar (copiar + gravar tags)")
        status = gr.Textbox(label="Status", interactive=False)

        classify_btn.click(
            _do_classify,
            inputs=[folder, engine, threshold],
            outputs=[resumo, tabela],
        )
        apply_btn.click(_do_apply, inputs=[output_root], outputs=[status])

    return demo


if __name__ == "__main__":
    build_ui().launch()
