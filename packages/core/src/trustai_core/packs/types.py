from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from trustai_core.schemas.atoms import AtomModel


class OntologyModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    opposites: list[list[str]] = []
    mutex_sets: list[list[str]] = []
    aliases: dict[str, str] = {}


class PackModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    ontology: OntologyModel
    axioms: list[AtomModel]
    fingerprint: str
