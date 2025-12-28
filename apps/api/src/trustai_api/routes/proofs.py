from __future__ import annotations

import orjson
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from trustai_api.deps import get_db
from trustai_api.schemas import ProofResponse
from trustai_api.services.proof_store import ProofStore

router = APIRouter()


@router.get(
    "/v1/proofs/{proof_id}",
    response_model=ProofResponse,
    response_model_exclude_none=True,
)
def get_proof(proof_id: str, db: Session = Depends(get_db)) -> dict:
    proof_store = ProofStore()
    proof = proof_store.get(db, proof_id)
    if not proof:
        raise HTTPException(status_code=404, detail="Proof not found")
    return {"proof_id": proof.proof_id, "payload": orjson.loads(proof.payload_json)}
