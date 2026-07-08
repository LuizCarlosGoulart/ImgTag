"""Registro de motores disponiveis.

E aqui que a "troca de motor" acontece de fato. O app pede um motor pelo
nome (vindo da config ou de um seletor na UI) e o registry devolve a
instancia certa. Adicionar um motor novo = registrar uma linha aqui.
"""

from __future__ import annotations

from typing import Callable

from .base import TaggerEngine
from .clip_engine import CLIPEngine
from .fake_engine import FakeEngine

# Fabricas: nome -> funcao que constroi o motor (sem carregar ainda).
_ENGINES: dict[str, Callable[[], TaggerEngine]] = {
    "clip": CLIPEngine,
    "fake": FakeEngine,
}


def available_engines() -> list[str]:
    """Nomes de todos os motores registrados (para o seletor da UI)."""
    return list(_ENGINES.keys())


def get_engine(name: str) -> TaggerEngine:
    """Constroi (sem carregar) o motor pedido pelo nome.

    O chamador deve invocar `.load()` depois. Levanta KeyError com uma
    mensagem util se o nome nao existir.
    """
    if name not in _ENGINES:
        disponiveis = ", ".join(available_engines())
        raise KeyError(f"Motor '{name}' desconhecido. Disponiveis: {disponiveis}")
    return _ENGINES[name]()
