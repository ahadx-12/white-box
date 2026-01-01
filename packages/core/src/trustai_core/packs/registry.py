from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from typing import Protocol

from trustai_core.llm.base import LLMClient


@dataclass(frozen=True)
class PackContext:
    llm_mode: str
    openai_model: str
    claude_model: str
    openai_client_factory: Callable[[], LLMClient]
    anthropic_client_factory: Callable[[], LLMClient]


class PackRunner(Protocol):
    name: str
    fingerprint: str

    async def run(
        self,
        input_text: str,
        options: dict[str, object] | None,
    ) -> object:
        ...


PackFactory = Callable[[PackContext], PackRunner]

_PACK_REGISTRY: dict[str, PackFactory] = {}


def register_pack(name: str, factory: PackFactory) -> None:
    _PACK_REGISTRY[name] = factory


def _ensure_pack_loaded(name: str) -> None:
    if name in _PACK_REGISTRY:
        return
    try:
        import_module(f"trustai_core.packs.{name}.pack")
    except ModuleNotFoundError:
        return


def get_pack_runner(name: str, context: PackContext) -> PackRunner | None:
    _ensure_pack_loaded(name)
    factory = _PACK_REGISTRY.get(name)
    if not factory:
        return None
    return factory(context)


def list_registered_packs() -> list[str]:
    return sorted(_PACK_REGISTRY.keys())
