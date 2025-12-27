from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AtomModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    subject: str
    predicate: str
    obj: str
    is_true: bool = True

    def sort_key(self) -> tuple[str, str, str, bool]:
        return (self.subject, self.predicate, self.obj, self.is_true)


class ManifestModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    atoms: list[AtomModel]
