import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from app.api.dependencies import get_current_active_user, get_db
from app.core.rate_limiter import get_user_id_or_ip, limiter
from app.domain.models.models import AnalysisJob
from app.domain.schemas.product import JobCreate, JobList, JobResponse
from app.services.jobs import job_payload, submit

router = APIRouter(prefix="/analysis/jobs", tags=["Analysis jobs"])


@router.post("", status_code=202, response_model=JobResponse)
@limiter.limit("10/hour", key_func=get_user_id_or_ip)
async def create_job(
    request: Request, data: JobCreate, db=Depends(get_db), user=Depends(get_current_active_user)
):
    return job_payload(await submit(db, user, data))


@router.get("", response_model=JobList)
async def my_jobs(
    ticker: str | None = None,
    active: bool = False,
    db=Depends(get_db),
    user=Depends(get_current_active_user),
):
    query = select(AnalysisJob).where(AnalysisJob.user_id == user.id)
    if ticker:
        query = query.where(AnalysisJob.ticker == ticker.upper())
    if active:
        query = query.where(AnalysisJob.status.notin_(("succeeded", "failed")))
    rows = (await db.scalars(query.order_by(AnalysisJob.created_at.desc()).limit(50))).all()
    return {"data": [job_payload(j) for j in rows]}


@router.get("/{job_id}", response_model=JobResponse)
async def read_job(job_id: uuid.UUID, db=Depends(get_db), user=Depends(get_current_active_user)):
    job = await db.get(AnalysisJob, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(404, "Job tidak ditemukan.")
    return job_payload(job)
