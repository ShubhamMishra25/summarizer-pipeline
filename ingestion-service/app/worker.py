import os
import time
import json
import logging
import redis
from extractor import DocumentExtractor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
INPUT_QUEUE = os.getenv("REDIS_INPUT_QUEUE", "doc_processing_queue")
OUTPUT_QUEUE = os.getenv("REDIS_OUTPUT_QUEUE", "summarization_queue")
CLEANED_DIR = os.getenv("CLEANED_DIR", "/shared/cleaned")

os.makedirs(CLEANED_DIR, exist_ok=True)

def get_redis_connection():
    while True:
        try:
            client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
            client.ping()
            logging.info("Connected to Redis successfully.")
            return client
        except redis.ConnectionError:
            logging.warning("Redis not ready. Retrying in 2 seconds...")
            time.sleep(2)

def update_job_metadata(r: redis.Redis, job_id: str, updates: dict):
    data_str = r.get(f"job:{job_id}")
    if data_str:
        job_data = json.loads(data_str)
        job_data.update(updates)
        r.set(f"job:{job_id}", json.dumps(job_data))

def main():
    r = get_redis_connection()
    logging.info(f"Ingestion Worker started. Listening on queue '{INPUT_QUEUE}'...")

    while True:
        try:
            item = r.blpop(INPUT_QUEUE, timeout=5)
            if not item:
                continue

            _, message_json = item
            payload = json.loads(message_json)
            job_id = payload["job_id"]
            file_path = payload["file_path"]
            extension = payload["extension"]

            logging.info(f"Processing Job [{job_id}] - Extracting text...")
            update_job_metadata(r, job_id, {"status": "preprocessing"})

            extracted_text = DocumentExtractor.extract(file_path, extension)
            if not extracted_text:
                raise ValueError("Document appears empty or text could not be extracted.")

            cleaned_file_path = os.path.join(CLEANED_DIR, f"{job_id}.txt")
            with open(cleaned_file_path, "w", encoding="utf-8") as f:
                f.write(extracted_text)

            update_job_metadata(r, job_id, {
                "status": "queued_for_summarization",
                "cleaned_text_path": cleaned_file_path,
                "character_count": len(extracted_text)
            })

            next_payload = {"job_id": job_id, "cleaned_text_path": cleaned_file_path}
            r.rpush(OUTPUT_QUEUE, json.dumps(next_payload))
            logging.info(f"Job [{job_id}] preprocessed successfully.")

        except Exception as e:
            logging.error(f"Error processing job: {str(e)}")
            if 'job_id' in locals():
                update_job_metadata(r, job_id, {
                    "status": "failed",
                    "error": f"Preprocessing error: {str(e)}"
                })

if __name__ == "__main__":
    main()
