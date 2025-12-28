from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from trustai_api.db.models import Job


@dataclass
class JobCreateResult:
    job: Job


class JobStore:
    def create(
        self,
        session: Session,
        job_id: str,
        pack: str,
        input_text: str,
        request_id: str | None = None,
        payload_json: str | None = None,
    ) -> JobCreateResult:
        job = Job(
            job_id=job_id,
            status="queued",
            pack=pack,
            request_id=request_id,
            input_text=input_text,
            payload_json=payload_json,
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        return JobCreateResult(job=job)

    def set_running(self, session: Session, job: Job) -> Job:
        job.status = "running"
        job.updated_at = datetime.utcnow()
        session.add(job)
        session.commit()
        session.refresh(job)
        return job

    def set_done(self, session: Session, job: Job, proof_id: str) -> Job:
        job.status = "done"
        job.proof_id = proof_id
        job.updated_at = datetime.utcnow()
        session.add(job)
        session.commit()
        session.refresh(job)
        return job

    def set_failed(self, session: Session, job: Job, error: str) -> Job:
        job.status = "failed"
        job.error = error
        job.updated_at = datetime.utcnow()
        session.add(job)
        session.commit()
        session.refresh(job)
        return job

    def get(self, session: Session, job_id: str) -> Job | None:
        return session.get(Job, job_id)
