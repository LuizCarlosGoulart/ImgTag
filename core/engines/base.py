"""Contrato dos motores de classificacao.

Todo motor (CLIP, API de visao, modelos futuros) deve implementar esta
interface. O resto do app so conversa com `TaggerEngine`, nunca com uma
implementacao concreta -- e por isso que o motor e trocavel.

Regra de ouro do contrato: `classify` sempre devolve scores normalizados
em 0.0-1.0. Assim o "limiar" calibrado pelo usuario vale para qualquer
motor.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class TaggerEngine(ABC):
    """Interface comum a todos os motores de classificacao."""

    #: Nome curto do motor, usado na config, na UI e nos logs.
    name: str = "base"

    @abstractmethod
    def load(self) -> None:
        """Carrega o modelo / prepara a conexao. Chamado uma vez, no inicio.

        Implementacoes pesadas (carregar pesos na memoria, abrir sessao de
        API) devem ficar aqui e nao no __init__, para o app poder listar os
        motores disponiveis sem pagar o custo de carregar todos.
        """
        raise NotImplementedError

    @abstractmethod
    def classify(self, image_path: Path, tags: list[str]) -> dict[str, float]:
        """Devolve o score (0.0-1.0) de cada tag para a imagem dada.

        Args:
            image_path: caminho da imagem a classificar.
            tags: tags candidatas, em ingles (ver mapa de rotulos na UI).

        Returns:
            Dict {tag: score}, com uma entrada para cada tag de entrada.
            Score alto = a imagem combina com a tag.
        """
        raise NotImplementedError

    @property
    def info(self) -> str:
        """Descricao legivel do motor, para exibir na interface."""
        return self.name
