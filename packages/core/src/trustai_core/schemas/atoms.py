from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SourceSpanModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    start: int = Field(ge=0)
    end: int = Field(ge=0)


class AtomModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    subject: str
    predicate: str
    obj: str
    is_true: bool = True
    confidence: float = Field(ge=0.0, le=1.0)
    source_span: SourceSpanModel | None = None
    type: Literal["fact", "norm", "assumption"] | None = None

    def sort_key(self) -> tuple[str, str, str, bool]:
        return (self.subject, self.predicate, self.obj, self.is_true)


class ManifestModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    atoms: list[AtomModel]
