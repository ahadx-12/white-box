from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import orjson
from sqlalchemy.orm import Session
from trustai_core.schemas.proof import VerificationResult

from trustai_api.db.models import Proof


@dataclass
class ProofCreateResult:
    proof: Proof
    payload: dict[str, Any]


class ProofStore:
    def create(
        self,
        session: Session,
        result: VerificationResult,
        request_hash: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ProofCreateResult:
        payload = result.model_dump()
        existing = session.get(Proof, result.proof_id)
        if existing:
            return ProofCreateResult(proof=existing, payload=orjson.loads(existing.payload_json))
        proof = Proof(
            proof_id=result.proof_id,
            pack=result.pack,
            pack_fingerprint=result.pack_fingerprint,
            status=result.status,
            score=float(result.explain.get("score", 0.0)),
            payload_json=orjson.dumps(payload, option=orjson.OPT_SORT_KEYS).decode(),
            request_hash=request_hash,
            metadata=metadata,
        )
        session.add(proof)
        session.commit()
        session.refresh(proof)
        return ProofCreateResult(proof=proof, payload=payload)

    def get(self, session: Session, proof_id: str) -> Proof | None:
        return session.get(Proof, proof_id)
