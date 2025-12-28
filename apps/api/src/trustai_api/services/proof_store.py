from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import orjson
from sqlalchemy.orm import Session

from trustai_api.db.models import Proof


@dataclass
class ProofCreateResult:
    proof: Proof
    payload: dict[str, Any]


class ProofStore:
    def create(
        self,
        session: Session,
        payload: dict[str, Any],
        request_hash: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ProofCreateResult:
        proof_id = payload.get("proof_id")
        if not proof_id:
            raise ValueError("Payload missing proof_id")
        existing = session.get(Proof, proof_id)
        if existing:
            return ProofCreateResult(proof=existing, payload=orjson.loads(existing.payload_json))
        iterations = payload.get("iterations") or []
        score = 0.0
        if iterations:
            last_score = iterations[-1].get("score")
            if isinstance(last_score, (int, float)):
                score = float(last_score)
        proof = Proof(
            proof_id=proof_id,
            pack=payload.get("pack") or "",
            pack_fingerprint=payload.get("pack_fingerprint") or "",
            status=payload.get("status") or "unknown",
            score=score,
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
