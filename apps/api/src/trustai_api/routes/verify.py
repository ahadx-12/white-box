from __future__ import annotations

from typing import Any
from uuid import uuid4

import orjson
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session
from trustai_core.utils.hashing import sha256_canonical_json

from trustai_api.deps import get_db, get_queue, get_settings_dep, get_verifier_service
from trustai_api.queue.rq import enqueue_verify
from trustai_api.routes.utils import resolve_pack
from trustai_api.schemas import VerificationResultResponse, VerifyAsyncResponse, VerifyRequest
from trustai_api.services.idempotency import IdempotencyStore
from trustai_api.services.job_store import JobStore
from trustai_api.services.proof_store import ProofStore
from trustai_api.services.verifier_service import VerifierService, VerifyOptions
from trustai_api.settings import Settings

router = APIRouter()


@router.post(
    "/v1/verify",
    response_model=VerificationResultResponse | VerifyAsyncResponse,
    response_model_exclude_none=True,
)
async def verify(
    body: VerifyRequest,
    mode: str | None = Query(default=None),
    x_request_id: str | None = Header(default=None, alias="X-Request-Id"),
    x_pack: str | None = Header(default=None, alias="X-TrustAI-Pack"),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    queue: Any = Depends(get_queue),
    verifier: VerifierService = Depends(get_verifier_service),
) -> dict[str, Any]:
    if mode and body.mode and mode != body.mode:
        raise HTTPException(status_code=400, detail="Mode mismatch between query and body")
    resolved_mode = body.mode or mode or "sync"
    if resolved_mode not in {"sync", "async"}:
        raise HTTPException(status_code=400, detail="Invalid mode")

    pack = resolve_pack(settings, x_pack)

    idempotency_store = IdempotencyStore()
    job_store = JobStore()
    proof_store = ProofStore()

    if x_request_id:
        record = idempotency_store.get(db, x_request_id)
        if record:
            if record.mode != resolved_mode or record.pack != pack:
                raise HTTPException(status_code=409, detail="Idempotency key reuse mismatch")
            if record.response_json:
                return orjson.loads(record.response_json)
            if record.proof_id:
                proof = proof_store.get(db, record.proof_id)
                if proof:
                    return orjson.loads(proof.payload_json)
            if record.job_id:
                job = job_store.get(db, record.job_id)
                if job:
                    return {"job_id": job.job_id, "status": job.status}

    request_hash = sha256_canonical_json(
        {
            "input": body.input,
            "pack": pack,
            "mode": resolved_mode,
            "options": body.options.model_dump() if body.options else None,
        }
    )

    if resolved_mode == "async":
        job_id = str(uuid4())
        payload = {
            "input": body.input,
            "pack": pack,
            "options": body.options.model_dump() if body.options else None,
        }
        job_store.create(
            db,
            job_id=job_id,
            pack=pack,
            input_text=body.input,
            request_id=x_request_id,
            payload_json=orjson.dumps(payload).decode(),
        )
        if x_request_id:
            idempotency_store.create(
                db,
                request_id=x_request_id,
                mode=resolved_mode,
                pack=pack,
                job_id=job_id,
            )
        enqueue_verify(queue, job_id=job_id, payload=payload)
        return {"job_id": job_id, "status": "queued"}

    options = None
    if body.options:
        options = VerifyOptions(
            max_iters=body.options.max_iters,
            threshold=body.options.threshold,
        )
    result = await verifier.verify_sync(body.input, pack, options)
    create_result = proof_store.create(
        db,
        result=result,
        request_hash=request_hash,
        metadata={"options": body.options.model_dump() if body.options else None},
    )
    payload = create_result.payload
    payload_json = orjson.dumps(payload, option=orjson.OPT_SORT_KEYS).decode()
    if x_request_id:
        idempotency_store.create(
            db,
            request_id=x_request_id,
            mode=resolved_mode,
            pack=pack,
            proof_id=result.proof_id,
            response_json=payload_json,
        )
    return payload
