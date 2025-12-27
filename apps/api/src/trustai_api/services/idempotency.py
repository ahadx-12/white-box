from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from trustai_api.db.models import IdempotencyKey


@dataclass
class IdempotencyRecord:
    request_id: str
    mode: str
    pack: str
    job_id: str | None
    proof_id: str | None
    response_json: str | None


class IdempotencyStore:
    def get(self, session: Session, request_id: str) -> IdempotencyKey | None:
        return session.get(IdempotencyKey, request_id)

    def create(
        self,
        session: Session,
        request_id: str,
        mode: str,
        pack: str,
        job_id: str | None = None,
        proof_id: str | None = None,
        response_json: str | None = None,
    ) -> IdempotencyKey:
        record = IdempotencyKey(
            request_id=request_id,
            mode=mode,
            pack=pack,
            job_id=job_id,
            proof_id=proof_id,
            response_json=response_json,
            created_at=datetime.utcnow(),
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record

    def set_response(
        self,
        session: Session,
        record: IdempotencyKey,
        response_json: str,
    ) -> IdempotencyKey:
        record.response_json = response_json
        session.add(record)
        session.commit()
        session.refresh(record)
        return record
