from __future__ import annotations

import orjson
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from trustai_api.deps import get_db
from trustai_api.schemas import JobStatusResponse
from trustai_api.services.job_store import JobStore
from trustai_api.services.proof_store import ProofStore

router = APIRouter()


@router.get("/v1/jobs/{job_id}", response_model=JobStatusResponse, response_model_exclude_none=True)
def get_job(job_id: str, db: Session = Depends(get_db)) -> dict:
    job_store = JobStore()
    proof_store = ProofStore()
    job = job_store.get(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    payload = {
        "job_id": job.job_id,
        "status": job.status,
        "proof_id": job.proof_id,
        "error": job.error,
    }
    if job.proof_id:
        proof = proof_store.get(db, job.proof_id)
        if proof:
            payload["result"] = orjson.loads(proof.payload_json)
    return payload
