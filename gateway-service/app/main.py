import os
import uuid
import json
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import redis

from app.schemas import JobSubmissionResponse, JobStatusResponse

app = FastAPI(
    title="Document Summarization Gateway",
    description="API Gateway for uploading documents and tracking summarization jobs.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/shared/uploads")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_QUEUE_NAME = os.getenv("REDIS_QUEUE_NAME", "doc_processing_queue")

os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_redis_client():
    try:
        return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis connection error: {str(e)}")

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/upload", response_model=JobSubmissionResponse, status_code=status.HTTP_202_ACCEPTED, tags=["Jobs"])
async def upload_document(file: UploadFile = File(...)):
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{file_ext}'. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    job_id = str(uuid.uuid4())
    stored_filename = f"{job_id}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, stored_filename)

    try:
        with open(file_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                buffer.write(chunk)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store file: {str(e)}")

    job_payload = {
        "job_id": job_id,
        "original_filename": file.filename,
        "stored_filename": stored_filename,
        "file_path": file_path,
        "extension": file_ext,
        "status": "queued",
        "summary": "",
        "error": "",
        "created_at": datetime.utcnow().isoformat()
    }

    r = get_redis_client()
    try:
        r.set(f"job:{job_id}", json.dumps(job_payload))
        r.rpush(REDIS_QUEUE_NAME, json.dumps({"job_id": job_id, "file_path": file_path, "extension": file_ext}))
    except redis.RedisError as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue job: {str(e)}")

    return JobSubmissionResponse(
        job_id=job_id,
        filename=file.filename,
        status="queued",
        message="Document uploaded and job queued successfully.",
        created_at=datetime.utcnow()
    )

@app.get("/status/{job_id}", response_model=JobStatusResponse, tags=["Jobs"])
def get_job_status(job_id: str):
    r = get_redis_client()
    job_data_str = r.get(f"job:{job_id}")

    if not job_data_str:
        raise HTTPException(status_code=404, detail=f"Job ID '{job_id}' not found.")

    job_data = json.loads(job_data_str)
    return JobStatusResponse(
        job_id=job_data.get("job_id"),
        status=job_data.get("status"),
        error=job_data.get("error") or None,
        summary=job_data.get("summary") or None,
        created_at=job_data.get("created_at")
    )
